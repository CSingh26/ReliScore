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
    const { scored, bucketMode } = this.applyOperationalBuckets(scores);

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

  private applyOperationalBuckets<T extends { drive_id: string; risk_score: number; risk_bucket: string }>(
    scores: T[],
  ): { scored: T[]; bucketMode: 'model' | 'rank_fallback' } {
    if (scores.length === 0) {
      return { scored: [], bucketMode: 'model' };
    }

    const hasMediumOrHigh = scores.some((item) => item.risk_bucket === 'MED' || item.risk_bucket === 'HIGH');
    if (hasMediumOrHigh) {
      return { scored: scores, bucketMode: 'model' };
    }

    const ordered = [...scores].sort((a, b) => {
      if (b.risk_score !== a.risk_score) {
        return b.risk_score - a.risk_score;
      }
      return a.drive_id.localeCompare(b.drive_id);
    });

    const total = ordered.length;
    const highCount = total >= 20 ? Math.ceil(total * 0.05) : Math.min(1, total);
    const medCount =
      total >= 10 ? Math.ceil(total * 0.15) : Math.min(1, Math.max(0, total - highCount));

    const nextScores = ordered.map((item, index) => {
      let riskBucket: RiskBucket = 'LOW';
      let bucketPosition = 0;
      let bucketSize = Math.max(1, total - highCount - medCount);
      if (index < highCount) {
        riskBucket = 'HIGH';
        bucketPosition = index;
        bucketSize = highCount;
      } else if (index < highCount + medCount) {
        riskBucket = 'MED';
        bucketPosition = index - highCount;
        bucketSize = medCount;
      }

      return {
        ...item,
        risk_score: this.operationalScoreForBucket(riskBucket, bucketPosition, bucketSize),
        risk_bucket: riskBucket,
      };
    });

    return { scored: nextScores, bucketMode: 'rank_fallback' };
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

  private operationalScoreForBucket(
    bucket: RiskBucket,
    bucketPosition: number,
    bucketSize: number,
  ): number {
    const clampedSize = Math.max(1, bucketSize);
    const t = clampedSize === 1 ? 0.5 : bucketPosition / (clampedSize - 1);

    let max = 0.39;
    let min = 0.02;
    if (bucket === 'HIGH') {
      max = 0.95;
      min = 0.75;
    } else if (bucket === 'MED') {
      max = 0.74;
      min = 0.4;
    }

    return Number((max - (max - min) * t).toFixed(6));
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
