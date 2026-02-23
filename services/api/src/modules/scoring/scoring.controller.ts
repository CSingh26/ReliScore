import { Body, Controller, Post } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';
import { z } from 'zod';
import { parseWithSchema } from '../../common/validation';
import { ScoringService } from './scoring.service';

const scoreRunSchema = z.object({
  day: z.string().date().optional(),
});

@ApiTags('scoring')
@Controller('score')
export class ScoringController {
  constructor(private readonly scoringService: ScoringService) {}

  @Post('run')
  async run(@Body() body: unknown) {
    const parsed = parseWithSchema(scoreRunSchema, body ?? {});
    return this.scoringService.runScoringJob(parsed.day);
  }
}
