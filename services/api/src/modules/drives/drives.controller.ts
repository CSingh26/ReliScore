import { BadRequestException, Controller, Get, Param, Query } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { RiskBucket } from '@prisma/client';
import { z } from 'zod';
import { parseWithSchema } from '../../common/validation';
import { DrivesService } from './drives.service';

const listDrivesQuerySchema = z.object({
  risk: z
    .union([z.literal('low'), z.literal('med'), z.literal('high')])
    .optional()
    .transform((value) => value?.toUpperCase() as RiskBucket | undefined),
  page: z.coerce.number().int().positive().default(1),
  pageSize: z.coerce.number().int().min(1).max(200).default(25),
});

const driveParamSchema = z.object({
  id: z.string().min(1),
});

@ApiTags('drives')
@Controller('drives')
export class DrivesController {
  constructor(private readonly drivesService: DrivesService) {}

  @Get()
  async list(@Query() query: Record<string, unknown>) {
    const parsedQuery = listDrivesQuerySchema.safeParse(query);
    if (!parsedQuery.success) {
      throw new BadRequestException({
        message: 'Request validation failed',
        issues: parsedQuery.error.issues,
      });
    }

    const parsed = parsedQuery.data;
    return this.drivesService.listDrives({
      risk: parsed.risk,
      page: parsed.page,
      pageSize: parsed.pageSize,
    });
  }

  @Get(':id')
  async detail(@Param() params: Record<string, unknown>) {
    const parsed = parseWithSchema(driveParamSchema, params);
    return this.drivesService.getDriveDetails(parsed.id);
  }
}
