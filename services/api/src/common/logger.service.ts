import { Injectable } from '@nestjs/common';
import pino from 'pino';

@Injectable()
export class LoggerService {
  private readonly logger = pino({
    level: process.env.LOG_LEVEL ?? 'info',
    base: {
      service: 'reliscore-api',
      env: process.env.NODE_ENV ?? 'development',
    },
    timestamp: pino.stdTimeFunctions.isoTime,
  });

  info(message: string, context?: Record<string, unknown>) {
    this.logger.info(context ?? {}, message);
  }

  error(message: string, context?: Record<string, unknown>) {
    this.logger.error(context ?? {}, message);
  }

  warn(message: string, context?: Record<string, unknown>) {
    this.logger.warn(context ?? {}, message);
  }
}
