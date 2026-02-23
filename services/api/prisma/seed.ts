import axios from 'axios';
import { PrismaClient, RiskBucket } from '@prisma/client';
import { scoreResponseSchema } from '@reliscore/shared';
import { z } from 'zod';
import { featureVectorFromRow, generateFeaturesForDay } from '../src/modules/scoring/feature-engineering';

const prisma = new PrismaClient();
const scoreBatchResponseSchema = z.array(scoreResponseSchema);

const MODELS = ['ST12000NM0008', 'WDC_WUH721414ALE6L4', 'TOSHIBA_MG07ACA14TA'];
const DATACENTERS = ['us-east-1', 'us-west-2', 'eu-central-1'];

function toDateOnly(date: Date): Date {
  return new Date(date.toISOString().slice(0, 10));
}

function toIsoDay(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function bucketFromScore(score: number): RiskBucket {
  if (score >= 0.75) {
    return 'HIGH';
  }

  if (score >= 0.4) {
    return 'MED';
  }

  return 'LOW';
}

function sigmoid(value: number): number {
  return 1 / (1 + Math.exp(-value));
}

function fallbackScores(items: Array<{ drive_id: string; day: string; features: Record<string, number> }>) {
  return items.map((item) => {
    const features = item.features;
    const linear =
      0.015 * (features.age_days ?? 0) +
      0.09 * (features.smart_5_mean_7d ?? 0) +
      0.16 * (features.smart_197_mean_7d ?? 0) +
      0.22 * (features.smart_197_max_30d ?? 0) +
      0.11 * (features.smart_198_delta_7d ?? 0) +
      0.07 * (features.write_latency_mean_7d ?? 0) +
      0.3 * (features.missing_smart_197_30d ?? 0) -
      3.2;

    const riskScore = clamp(sigmoid(linear), 0, 1);
    const topReasons = [
      { code: 'smart_197_max_30d', contribution: Number((0.22 * (features.smart_197_max_30d ?? 0)).toFixed(6)), direction: 'UP' },
      { code: 'smart_197_mean_7d', contribution: Number((0.16 * (features.smart_197_mean_7d ?? 0)).toFixed(6)), direction: 'UP' },
      { code: 'smart_5_mean_7d', contribution: Number((0.09 * (features.smart_5_mean_7d ?? 0)).toFixed(6)), direction: 'UP' },
      { code: 'age_days', contribution: Number((0.015 * (features.age_days ?? 0)).toFixed(6)), direction: 'UP' },
      {
        code: 'missing_smart_197_30d',
        contribution: Number((0.3 * (features.missing_smart_197_30d ?? 0)).toFixed(6)),
        direction: 'UP',
      },
    ];

    return {
      drive_id: item.drive_id,
      day: item.day,
      risk_score: riskScore,
      risk_bucket: bucketFromScore(riskScore),
      top_reasons: topReasons,
      model_version: 'heuristic-seed-v1',
      scored_at: new Date().toISOString(),
    };
  });
}

async function callModelScoreBatchWithRetry(
  items: Array<{ drive_id: string; day: string; features: Record<string, number> }>,
) {
  const client = axios.create({
    baseURL: process.env.MODEL_SERVICE_URL ?? 'http://model:8000',
    timeout: 20000,
  });

  const headers = process.env.MODEL_SERVICE_TOKEN
    ? { Authorization: `Bearer ${process.env.MODEL_SERVICE_TOKEN}` }
    : undefined;

  for (let attempt = 1; attempt <= 8; attempt += 1) {
    try {
      const response = await client.post('/score_batch', { items }, { headers });
      return scoreBatchResponseSchema.parse(response.data);
    } catch (error) {
      if (attempt === 8) {
        console.warn(`Model service unavailable after retries, using fallback heuristic scoring: ${String(error)}`);
        return fallbackScores(items);
      }

      await new Promise((resolve) => {
        setTimeout(resolve, 1500 * attempt);
      });
    }
  }

  return fallbackScores(items);
}

async function seedDrivesAndTelemetry(latestDay: Date) {
  const startDay = new Date(latestDay);
  startDay.setDate(startDay.getDate() - 120);

  const telemetryRows: Array<{
    driveId: string;
    day: Date;
    smart5: number;
    smart187: number;
    smart188: number;
    smart197: number;
    smart198: number;
    smart199: number;
    temperature: number;
    ioReadLatencyMs: number;
    ioWriteLatencyMs: number;
    isFailedToday: boolean;
  }> = [];

  for (let index = 0; index < 48; index += 1) {
    const driveId = `DRV-${String(index + 1).padStart(4, '0')}`;
    const model = MODELS[index % MODELS.length];
    const datacenter = DATACENTERS[index % DATACENTERS.length];
    const highRisk = index % 8 === 0;

    await prisma.drive.upsert({
      where: { driveId },
      create: {
        driveId,
        model,
        datacenter,
        capacityBytes: BigInt(12_000_000_000_000),
        firstSeen: toDateOnly(startDay),
        lastSeen: toDateOnly(latestDay),
      },
      update: {
        model,
        datacenter,
        lastSeen: toDateOnly(latestDay),
      },
    });

    for (let dayOffset = 0; dayOffset <= 120; dayOffset += 1) {
      const day = new Date(startDay);
      day.setDate(startDay.getDate() + dayOffset);

      const progress = dayOffset / 120;
      const riskTrend = highRisk ? 1 + progress * 3.2 : 1 + progress * 0.8;

      const smart5 = Math.max(0, Math.round(1 + riskTrend * 2 + Math.random() * 3));
      const smart197 = Math.max(0, Math.round(2 + riskTrend * 4 + Math.random() * 5));
      const smart198 = Math.max(0, Math.round(1 + riskTrend * 2 + Math.random() * 4));
      const smart199 = Math.max(0, Math.round(1 + riskTrend * 1.8 + Math.random() * 4));
      const smart187 = Math.max(0, Math.round(riskTrend + Math.random() * 2));
      const smart188 = Math.max(0, Math.round(riskTrend + Math.random() * 2));
      const temperature = clamp(30 + riskTrend * 2.5 + Math.random() * 2.5, 28, 48);

      const ioReadLatencyMs = clamp(2.2 + riskTrend * 1.2 + Math.random() * 1.5, 1.0, 18);
      const ioWriteLatencyMs = clamp(2.5 + riskTrend * 1.5 + Math.random() * 2, 1.2, 24);

      const isFailedToday = highRisk && dayOffset === 118;

      telemetryRows.push({
        driveId,
        day: toDateOnly(day),
        smart5,
        smart187,
        smart188,
        smart197,
        smart198,
        smart199,
        temperature,
        ioReadLatencyMs,
        ioWriteLatencyMs,
        isFailedToday,
      });
    }
  }

  await prisma.telemetryDaily.createMany({
    data: telemetryRows,
    skipDuplicates: true,
  });

  await prisma.auditLog.create({
    data: {
      action: 'INGESTION',
      payload: {
        source: 'synthetic-seed',
        day: toIsoDay(latestDay),
        rowsInserted: telemetryRows.length,
      },
    },
  });
}

async function seedFeaturesAndPredictions(day: Date) {
  const generatedFeatures = await generateFeaturesForDay(prisma, day);

  const featureRows = await prisma.featuresDaily.findMany({
    where: { day },
    orderBy: { driveId: 'asc' },
  });

  const items = featureRows.map((row) => ({
    drive_id: row.driveId,
    day: toIsoDay(day),
    features: featureVectorFromRow(row),
  }));

  const scored = await callModelScoreBatchWithRetry(items);

  await prisma.$transaction(
    scored.map((score) =>
      prisma.prediction.upsert({
        where: {
          driveId_day_modelVersion: {
            driveId: score.drive_id,
            day,
            modelVersion: score.model_version,
          },
        },
        create: {
          driveId: score.drive_id,
          day,
          modelVersion: score.model_version,
          riskScore: score.risk_score,
          riskBucket: score.risk_bucket as RiskBucket,
          reasonCodes: score.top_reasons,
          scoredAt: new Date(score.scored_at),
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

  await prisma.auditLog.create({
    data: {
      action: 'FEATURE_RUN',
      payload: {
        day: toIsoDay(day),
        generatedFeatures,
      },
    },
  });

  await prisma.auditLog.create({
    data: {
      action: 'SCORE_RUN',
      payload: {
        day: toIsoDay(day),
        storedPredictions: scored.length,
        modelVersion: scored[0]?.model_version,
      },
    },
  });

  return {
    generatedFeatures,
    storedPredictions: scored.length,
    modelVersion: scored[0]?.model_version ?? 'none',
  };
}

async function main() {
  const latestDay = toDateOnly(new Date());

  console.log('Seeding drives and telemetry...');
  await seedDrivesAndTelemetry(latestDay);

  console.log('Generating features and predictions...');
  const stats = await seedFeaturesAndPredictions(latestDay);

  console.log('Seed complete', {
    day: toIsoDay(latestDay),
    ...stats,
  });
}

main()
  .catch((error) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
