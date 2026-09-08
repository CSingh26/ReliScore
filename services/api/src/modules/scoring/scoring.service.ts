import { Injectable } from '@nestjs/common';
import { RiskBucket } from '@prisma/client';
import { LoggerService } from '../../common/logger.service';
import { PrismaService } from '../prisma.service';
import { featureVectorFromRow, generateFeaturesForDay } from './feature-engineering';
import { ModelClientService } from './model-client.service';

function toDateOnlyString(day: Date): string {
  return day.toISOString().slice(0, 10);
}

@Injectable()
export class ScoringService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly logger: LoggerService,
    private readonly modelClient: ModelClientService,
  ) {}

  async runScoringJob(day?: string) {
    const targetDay = day ? new Date(day) : await this.resolveLatestTelemetryDay();
    if (!targetDay) {
      return {
        status: 'skipped',
        reason: 'No telemetry available',
        generatedFeatures: 0,
        storedPredictions: 0,
      };
    }

    const dateOnly = new Date(targetDay.toISOString().slice(0, 10));

    const generatedFeatures = await generateFeaturesForDay(this.prisma, dateOnly);
    if (generatedFeatures === 0) {
      return {
        status: 'skipped',
        day: toDateOnlyString(dateOnly),
        reason: 'No feature rows generated',
        generatedFeatures,
        storedPredictions: 0,
      };
    }

    const featureRows = await this.prisma.featuresDaily.findMany({
      where: {
        day: dateOnly,
        drive: { telemetryDaily: { some: { day: dateOnly }, none: { day: { lte: dateOnly }, isFailedToday: true } } },
      },
      orderBy: {
        driveId: 'asc',
      },
    });

    const batchItems = featureRows.map((row) => ({
      drive_id: row.driveId,
      day: toDateOnlyString(row.day),
      features: featureVectorFromRow(row),
    }));

    const scores = await this.modelClient.scoreBatch(batchItems);
    const scored = scores;
    const bucketMode = 'model' as const;

    await this.prisma.$transaction(
      scored.map((score) =>
        this.prisma.prediction.upsert({
          where: {
            driveId_day_modelVersion: {
              driveId: score.drive_id,
              day: dateOnly,
              modelVersion: score.model_version,
            },
          },
          create: {
            driveId: score.drive_id,
            day: dateOnly,
            modelVersion: score.model_version,
            riskScore: score.risk_score,
            riskBucket: score.risk_bucket as RiskBucket,
            reasonCodes: score.top_reasons,
          },
          update: {
            riskScore: score.risk_score,
            riskBucket: score.risk_bucket as RiskBucket,
            reasonCodes: score.top_reasons,
            scoredAt: new Date(score.scored_at),
          },
        }),
      ),
    );

    await this.prisma.auditLog.create({
      data: {
        action: 'SCORE_RUN',
        payload: {
          day: toDateOnlyString(dateOnly),
          generatedFeatures,
          storedPredictions: scored.length,
          modelVersion: scored[0]?.model_version ?? 'unknown',
          bucketMode,
          riskDistribution: this.bucketDistribution(scored.map((item) => item.risk_bucket as RiskBucket)),
        },
      },
    });

    this.logger.info('Scoring run completed', {
      day: toDateOnlyString(dateOnly),
      generatedFeatures,
      storedPredictions: scored.length,
      modelVersion: scored[0]?.model_version,
      bucketMode,
    });

    return {
      status: 'completed',
      day: toDateOnlyString(dateOnly),
      generatedFeatures,
      storedPredictions: scored.length,
      modelVersion: scored[0]?.model_version ?? null,
      bucketMode,
    };
  }

  private bucketDistribution(buckets: RiskBucket[]) {
    const distribution: Record<RiskBucket, number> = {
      LOW: 0,
      MED: 0,
      HIGH: 0,
    };

    for (const bucket of buckets) {
      distribution[bucket] += 1;
    }

    return distribution;
  }

  private async resolveLatestTelemetryDay(): Promise<Date | null> {
    const latest = await this.prisma.telemetryDaily.findFirst({
      select: {
        day: true,
      },
      orderBy: {
        day: 'desc',
      },
    });

    return latest?.day ?? null;
  }
}
