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
        count: vi
          .fn()
          .mockResolvedValueOnce(110)
          .mockResolvedValueOnce(17),
        groupBy: vi.fn().mockResolvedValue([
          { riskBucket: 'LOW', _count: { riskBucket: 71 } },
          { riskBucket: 'MED', _count: { riskBucket: 22 } },
          { riskBucket: 'HIGH', _count: { riskBucket: 17 } },
        ]),
      },
    };

    const service = new FleetService(prisma as never);
    const summary = await service.getSummary();

    expect(summary.totalDrives).toBe(120);
    expect(summary.drivesScoredToday).toBe(110);
    expect(summary.predictedFailures14d).toBe(17);
    expect(summary.riskDistribution.HIGH).toBe(17);
  });
});
