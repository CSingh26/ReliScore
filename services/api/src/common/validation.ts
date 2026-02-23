import { BadRequestException } from '@nestjs/common';
import { ZodSchema } from 'zod';

export function parseWithSchema<T>(schema: ZodSchema<T>, value: unknown): T {
  const parsed = schema.safeParse(value);
  if (!parsed.success) {
    throw new BadRequestException({
      message: 'Request validation failed',
      issues: parsed.error.issues,
    });
  }

  return parsed.data;
}
