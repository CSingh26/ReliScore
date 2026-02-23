import { BadRequestException } from '@nestjs/common';
import { z } from 'zod';

export function parseWithSchema<TSchema extends z.ZodTypeAny>(
  schema: TSchema,
  value: unknown,
): z.infer<TSchema> {
  const parsed = schema.safeParse(value);
  if (!parsed.success) {
    throw new BadRequestException({
      message: 'Request validation failed',
      issues: parsed.error.issues,
    });
  }

  return parsed.data;
}
