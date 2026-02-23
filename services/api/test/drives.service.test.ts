import { NotFoundException } from '@nestjs/common';
import { describe, expect, it, vi } from 'vitest';
import { DrivesService } from '../src/modules/drives/drives.service';

describe('DrivesService', () => {
  it('throws when drive does not exist', async () => {
    const prisma = {
      drive: {
        findUnique: vi.fn().mockResolvedValue(null),
      },
      telemetryDaily: {
        findMany: vi.fn(),
      },
      prediction: {
        findMany: vi.fn(),
      },
    };

    const service = new DrivesService(prisma as never);

    await expect(service.getDriveDetails('missing-drive')).rejects.toBeInstanceOf(NotFoundException);
  });
});
