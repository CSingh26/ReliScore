import { describe, expect, it, vi } from 'vitest';
import { FleetService } from '../src/modules/fleet/fleet.service';

describe('FleetService', () => {
  it('returns summary with distribution counts', async () => {
    const prisma = {
      drive: {
        count: vi.fn().mockResolvedValue(120),
      },
      prediction: {
        findFirst: vi.fn().mockResolvedValue({ day: new Date('2026-02-22') }),
        findMany: vi.fn().mockResolvedValue([
          ...Array.from({length:71}, () => ({riskBucket:'LOW'})),
          ...Array.from({length:22}, () => ({riskBucket:'MED'})),
          ...Array.from({length:17}, () => ({riskBucket:'HIGH'})),
        ]),
      },
    };

    const service = new FleetService(prisma as never);
    const summary = await service.getSummary();

    expect(summary.totalDrives).toBe(120);
    expect(summary.drivesScoredToday).toBe(110);
    expect(summary.predictedFailures30d).toBe(17);
    expect(summary.riskDistribution.HIGH).toBe(17);
  });
});
