import { describe, expect, it, vi } from 'vitest';
import { generateFeaturesForDay } from '../src/modules/scoring/feature-engineering';
const day = new Date('2026-03-01');
function row(date: string, value: number | null) { return {driveId:'d1',day:new Date(date),smart5:value,smart187:null,smart188:null,smart197:null,smart198:null,smart199:null,temperature:null,isFailedToday:false}; }
describe('feature parity with training SQL', () => {
  it('uses lifetime firstSeen, last observations, and zero-imputed missing-current delta', async () => {
    const rows=[row('2026-01-01',8),row('2026-02-28',10),row('2026-03-01',null)];
    const upsert=vi.fn();
    const prisma={telemetryDaily:{findMany:vi.fn().mockResolvedValue(rows)},drive:{findMany:vi.fn().mockResolvedValue([{driveId:'d1',capacityBytes:1000n,firstSeen:new Date('2025-01-01'),telemetryDaily:[...rows].reverse()}])},featuresDaily:{upsert}};
    await generateFeaturesForDay(prisma as never,day);
    const vector=upsert.mock.calls[0][0].create.featureVector;
    expect(vector.age_days).toBe(424);
    expect(vector.smart_5_raw_delta_vs_7d).toBe(0);
    expect(vector.smart_5_raw_mean_30d).toBe(9);
    const query=prisma.drive.findMany.mock.calls[0][0];
    expect(query.select.telemetryDaily.take).toBe(30);
    expect(query.where.telemetryDaily.some.day).toEqual(day);
  });
});
