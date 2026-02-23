import { Controller, Get, Query } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { z } from 'zod';
import { parseWithSchema } from '../../common/validation';
import { FleetService } from './fleet.service';

const summaryQuerySchema = z.object({
  day: z.string().date().optional(),
});

@ApiTags('fleet')
@Controller('fleet')
export class FleetController {
  constructor(private readonly fleetService: FleetService) {}

  @Get('summary')
  async summary(@Query() query: Record<string, unknown>) {
    const parsed = parseWithSchema(summaryQuerySchema, query);
    return this.fleetService.getSummary(parsed.day);
  }
}
