import { Injectable } from '@nestjs/common';
import { LoggerService } from '../../common/logger.service';

@Injectable()
export class ScoringService {
  constructor(private readonly logger: LoggerService) {}

  async runScoringJob(day?: string) {
    this.logger.info('Scoring run requested', { day: day ?? 'latest' });

    return {
      status: 'accepted',
      day: day ?? new Date().toISOString().slice(0, 10),
      generatedFeatures: 0,
      storedPredictions: 0,
      note: 'Feature generation and score batch integration are added in the next stage.',
    };
  }
}
