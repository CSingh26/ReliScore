import { FeaturesDaily, Prisma, PrismaClient, TelemetryDaily } from '@prisma/client';

export type FeatureVector = Record<string, number> & {
  age_days: number;
  smart_5_mean_7d: number;
  smart_5_slope_14d: number;
  smart_197_max_30d: number;
  smart_197_mean_7d: number;
  smart_198_delta_7d: number;
  smart_199_volatility_30d: number;
  temperature_mean_7d: number;
  read_latency_mean_7d: number;
  write_latency_mean_7d: number;
  missing_smart_197_30d: number;
};

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

function toDateOnly(date: Date): Date {
  return new Date(date.toISOString().slice(0, 10));
}

function rollingSeries(values: Array<number | null | undefined>, window: number): number[] {
  return values.slice(-window).filter((value): value is number => typeof value === 'number');
}

function mean(values: number[]): number {
  if (!values.length) {
    return 0;
  }

  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function max(values: number[]): number {
  if (!values.length) {
    return 0;
  }

  return Math.max(...values);
}

function std(values: number[]): number {
  if (values.length < 2) {
    return 0;
  }

  const m = mean(values);
  const variance = values.reduce((sum, value) => sum + (value - m) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function slope(values: Array<number | null | undefined>, window: number): number {
  const relevant = values.slice(-window).filter((value): value is number => typeof value === 'number');
  if (relevant.length < 2) {
    return 0;
  }

  return (relevant[relevant.length - 1] - relevant[0]) / Math.max(relevant.length - 1, 1);
}

function computeFeatureVector(rows: TelemetryDaily[], day: Date): FeatureVector {
  const sorted = [...rows].sort((a, b) => a.day.getTime() - b.day.getTime());
  const smart5 = sorted.map((row) => row.smart5);
  const smart197 = sorted.map((row) => row.smart197);
  const smart198 = sorted.map((row) => row.smart198);
  const smart199 = sorted.map((row) => row.smart199);
  const temp = sorted.map((row) => row.temperature);
  const readLatency = sorted.map((row) => row.ioReadLatencyMs);
  const writeLatency = sorted.map((row) => row.ioWriteLatencyMs);

  const firstSeen = sorted[0]?.day ?? day;
  const ageDays = Math.max(0, Math.floor((day.getTime() - firstSeen.getTime()) / (24 * 60 * 60 * 1000)));

  const smart198Latest = smart198[smart198.length - 1] ?? 0;
  const smart198SevenAgo = smart198[Math.max(0, smart198.length - 7)] ?? 0;

  const smart197Recent = rollingSeries(smart197, 30);

  return {
    age_days: ageDays,
    smart_5_mean_7d: mean(rollingSeries(smart5, 7)),
    smart_5_slope_14d: slope(smart5, 14),
    smart_197_max_30d: max(smart197Recent),
    smart_197_mean_7d: mean(rollingSeries(smart197, 7)),
    smart_198_delta_7d: Number(smart198Latest) - Number(smart198SevenAgo),
    smart_199_volatility_30d: std(rollingSeries(smart199, 30)),
    temperature_mean_7d: mean(rollingSeries(temp, 7)),
    read_latency_mean_7d: mean(rollingSeries(readLatency, 7)),
    write_latency_mean_7d: mean(rollingSeries(writeLatency, 7)),
    missing_smart_197_30d: smart197Recent.length ? 0 : 1,
  };
}

function toFeaturesDailyCreateInput(
  driveId: string,
  day: Date,
  vector: FeatureVector,
): Prisma.FeaturesDailyUncheckedCreateInput {
  return {
    driveId,
    day,
    labelFailWithin14d: false,
    ageDays: vector.age_days,
    smart5Mean7d: vector.smart_5_mean_7d,
    smart5Slope14d: vector.smart_5_slope_14d,
    smart197Max30d: vector.smart_197_max_30d,
    smart197Mean7d: vector.smart_197_mean_7d,
    smart198Delta7d: vector.smart_198_delta_7d,
    smart199Volatility30d: vector.smart_199_volatility_30d,
    temperatureMean7d: vector.temperature_mean_7d,
    readLatencyMean7d: vector.read_latency_mean_7d,
    writeLatencyMean7d: vector.write_latency_mean_7d,
    missingSmart19730d: vector.missing_smart_197_30d > 0,
    featureVector: toJsonValue(vector),
  };
}

function toFeaturesDailyUpdateInput(vector: FeatureVector): Prisma.FeaturesDailyUncheckedUpdateInput {
  return {
    labelFailWithin14d: false,
    ageDays: vector.age_days,
    smart5Mean7d: vector.smart_5_mean_7d,
    smart5Slope14d: vector.smart_5_slope_14d,
    smart197Max30d: vector.smart_197_max_30d,
    smart197Mean7d: vector.smart_197_mean_7d,
    smart198Delta7d: vector.smart_198_delta_7d,
    smart199Volatility30d: vector.smart_199_volatility_30d,
    temperatureMean7d: vector.temperature_mean_7d,
    readLatencyMean7d: vector.read_latency_mean_7d,
    writeLatencyMean7d: vector.write_latency_mean_7d,
    missingSmart19730d: vector.missing_smart_197_30d > 0,
    featureVector: toJsonValue(vector),
  };
}

function toJsonValue(vector: FeatureVector): Prisma.InputJsonValue {
  return JSON.parse(JSON.stringify(vector)) as Prisma.InputJsonValue;
}

export function featureVectorFromRow(row: FeaturesDaily): FeatureVector {
  const featureVector = (row.featureVector ?? {}) as Partial<FeatureVector>;

  return {
    age_days: Number(featureVector.age_days ?? row.ageDays ?? 0),
    smart_5_mean_7d: Number(featureVector.smart_5_mean_7d ?? row.smart5Mean7d ?? 0),
    smart_5_slope_14d: Number(featureVector.smart_5_slope_14d ?? row.smart5Slope14d ?? 0),
    smart_197_max_30d: Number(featureVector.smart_197_max_30d ?? row.smart197Max30d ?? 0),
    smart_197_mean_7d: Number(featureVector.smart_197_mean_7d ?? row.smart197Mean7d ?? 0),
    smart_198_delta_7d: Number(featureVector.smart_198_delta_7d ?? row.smart198Delta7d ?? 0),
    smart_199_volatility_30d: Number(
      featureVector.smart_199_volatility_30d ?? row.smart199Volatility30d ?? 0,
    ),
    temperature_mean_7d: Number(featureVector.temperature_mean_7d ?? row.temperatureMean7d ?? 0),
    read_latency_mean_7d: Number(featureVector.read_latency_mean_7d ?? row.readLatencyMean7d ?? 0),
    write_latency_mean_7d: Number(
      featureVector.write_latency_mean_7d ?? row.writeLatencyMean7d ?? 0,
    ),
    missing_smart_197_30d: Number(
      featureVector.missing_smart_197_30d ?? (row.missingSmart19730d ? 1 : 0),
    ),
  };
}

export async function generateFeaturesForDay(prisma: PrismaClient, day: Date): Promise<number> {
  const dayStart = toDateOnly(day);
  const lowerBound = new Date(dayStart.getTime() - THIRTY_DAYS_MS);

  const telemetryRows = await prisma.telemetryDaily.findMany({
    where: {
      day: {
        gte: lowerBound,
        lte: dayStart,
      },
    },
    orderBy: [{ driveId: 'asc' }, { day: 'asc' }],
  });

  const grouped = new Map<string, TelemetryDaily[]>();
  for (const row of telemetryRows) {
    if (!grouped.has(row.driveId)) {
      grouped.set(row.driveId, []);
    }

    grouped.get(row.driveId)?.push(row);
  }

  let generated = 0;
  for (const [driveId, rows] of grouped.entries()) {
    if (!rows.length) {
      continue;
    }

    const vector = computeFeatureVector(rows, dayStart);
    const createInput = toFeaturesDailyCreateInput(driveId, dayStart, vector);
    const updateInput = toFeaturesDailyUpdateInput(vector);

    await prisma.featuresDaily.upsert({
      where: {
        driveId_day: {
          driveId,
          day: dayStart,
        },
      },
      create: createInput,
      update: updateInput,
    });

    generated += 1;
  }

  return generated;
}
