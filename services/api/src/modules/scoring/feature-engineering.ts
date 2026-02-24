import { FeaturesDaily, Prisma, PrismaClient, TelemetryDaily } from '@prisma/client';

const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;

const RAW_METRICS = [
  'smart_5_raw',
  'smart_187_raw',
  'smart_188_raw',
  'smart_197_raw',
  'smart_198_raw',
  'smart_199_raw',
  'smart_241_raw',
  'smart_242_raw',
  'temperature',
] as const;

type RawMetric = (typeof RAW_METRICS)[number];

const METRIC_FEATURE_COLUMNS = RAW_METRICS.flatMap((metric) => [
  `${metric}_mean_7d`,
  `${metric}_mean_30d`,
  `${metric}_std_30d`,
  `${metric}_delta_vs_7d`,
  `${metric}_is_increasing`,
]);

export const MODEL_FEATURE_COLUMNS = ['capacity_bytes', 'age_days', ...METRIC_FEATURE_COLUMNS] as const;

export type FeatureVector = Record<string, number>;

function toDateOnly(date: Date): Date {
  return new Date(date.toISOString().slice(0, 10));
}

function mean(values: number[]): number {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function stdDev(values: number[]): number {
  if (values.length < 2) return 0;
  const m = mean(values);
  const variance = values.reduce((sum, value) => sum + (value - m) ** 2, 0) / values.length;
  return Math.sqrt(variance);
}

function recentNumeric(values: Array<number | null | undefined>, window: number): number[] {
  return values.slice(-window).filter((value): value is number => typeof value === 'number');
}

function toJsonValue(vector: FeatureVector): Prisma.InputJsonValue {
  return JSON.parse(JSON.stringify(vector)) as Prisma.InputJsonValue;
}

function metricFromRow(row: TelemetryDaily, metric: RawMetric): number | null {
  switch (metric) {
    case 'smart_5_raw':
      return row.smart5;
    case 'smart_187_raw':
      return row.smart187;
    case 'smart_188_raw':
      return row.smart188;
    case 'smart_197_raw':
      return row.smart197;
    case 'smart_198_raw':
      return row.smart198;
    case 'smart_199_raw':
      return row.smart199;
    case 'temperature':
      return row.temperature;
    case 'smart_241_raw':
    case 'smart_242_raw':
      return null;
    default:
      return null;
  }
}

function metricFeatureSet(sortedRows: TelemetryDaily[], metric: RawMetric): Record<string, number> {
  const values = sortedRows.map((row) => metricFromRow(row, metric));
  const values7 = recentNumeric(values, 7);
  const values30 = recentNumeric(values, 30);

  const current = values[values.length - 1];
  const previous = values.length > 1 ? values[values.length - 2] : null;
  const mean7 = mean(values7);

  return {
    [`${metric}_mean_7d`]: mean7,
    [`${metric}_mean_30d`]: mean(values30),
    [`${metric}_std_30d`]: stdDev(values30),
    [`${metric}_delta_vs_7d`]: (typeof current === 'number' ? current : 0) - mean7,
    [`${metric}_is_increasing`]:
      typeof current === 'number' && typeof previous === 'number' && current > previous ? 1 : 0,
  };
}

function computeFeatureVector(
  rows: TelemetryDaily[],
  day: Date,
  capacityBytes: bigint | null,
): FeatureVector {
  const sortedRows = [...rows].sort((a, b) => a.day.getTime() - b.day.getTime());
  const firstSeen = sortedRows[0]?.day ?? day;
  const ageDays = Math.max(0, Math.floor((day.getTime() - firstSeen.getTime()) / (24 * 60 * 60 * 1000)));

  const vector: FeatureVector = {
    capacity_bytes: Number(capacityBytes ?? 0),
    age_days: ageDays,
  };

  for (const metric of RAW_METRICS) {
    Object.assign(vector, metricFeatureSet(sortedRows, metric));
  }

  return vector;
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
    smart5Mean7d: vector.smart_5_raw_mean_7d,
    smart5Slope14d: vector.smart_5_raw_delta_vs_7d,
    smart197Max30d: vector.smart_197_raw_mean_30d,
    smart197Mean7d: vector.smart_197_raw_mean_7d,
    smart198Delta7d: vector.smart_198_raw_delta_vs_7d,
    smart199Volatility30d: vector.smart_199_raw_std_30d,
    temperatureMean7d: vector.temperature_mean_7d,
    readLatencyMean7d: null,
    writeLatencyMean7d: null,
    missingSmart19730d: vector.smart_197_raw_mean_30d === 0,
    featureVector: toJsonValue(vector),
  };
}

function toFeaturesDailyUpdateInput(vector: FeatureVector): Prisma.FeaturesDailyUncheckedUpdateInput {
  return {
    labelFailWithin14d: false,
    ageDays: vector.age_days,
    smart5Mean7d: vector.smart_5_raw_mean_7d,
    smart5Slope14d: vector.smart_5_raw_delta_vs_7d,
    smart197Max30d: vector.smart_197_raw_mean_30d,
    smart197Mean7d: vector.smart_197_raw_mean_7d,
    smart198Delta7d: vector.smart_198_raw_delta_vs_7d,
    smart199Volatility30d: vector.smart_199_raw_std_30d,
    temperatureMean7d: vector.temperature_mean_7d,
    readLatencyMean7d: null,
    writeLatencyMean7d: null,
    missingSmart19730d: vector.smart_197_raw_mean_30d === 0,
    featureVector: toJsonValue(vector),
  };
}

export function featureVectorFromRow(row: FeaturesDaily): FeatureVector {
  const source = (row.featureVector ?? {}) as Record<string, unknown>;

  const vector: FeatureVector = {};
  for (const column of MODEL_FEATURE_COLUMNS) {
    const value = source[column];
    vector[column] = typeof value === 'number' && Number.isFinite(value) ? value : 0;
  }

  if (source['age_days'] === undefined && typeof row.ageDays === 'number') {
    vector.age_days = row.ageDays;
  }
  if (source['smart_5_raw_mean_7d'] === undefined && typeof row.smart5Mean7d === 'number') {
    vector.smart_5_raw_mean_7d = row.smart5Mean7d;
  }
  if (source['smart_197_raw_mean_7d'] === undefined && typeof row.smart197Mean7d === 'number') {
    vector.smart_197_raw_mean_7d = row.smart197Mean7d;
  }

  return vector;
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

  const driveIds = Array.from(grouped.keys());
  const drives = await prisma.drive.findMany({
    where: { driveId: { in: driveIds } },
    select: {
      driveId: true,
      capacityBytes: true,
    },
  });
  const capacityByDrive = new Map(drives.map((drive) => [drive.driveId, drive.capacityBytes]));

  let generated = 0;
  for (const [driveId, rows] of grouped.entries()) {
    if (!rows.length) {
      continue;
    }

    const vector = computeFeatureVector(rows, dayStart, capacityByDrive.get(driveId) ?? null);
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
