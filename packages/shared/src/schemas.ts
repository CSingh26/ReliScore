import { z } from 'zod';

export const riskBucketSchema = z.enum(['LOW', 'MED', 'HIGH']);

export const driveSchema = z.object({
  driveId: z.string(),
  model: z.string(),
  datacenter: z.string(),
  capacityBytes: z.number().int().nonnegative(),
  firstSeen: z.string(),
  lastSeen: z.string(),
});

export const featurePayloadSchema = z.object({
  drive_id: z.string(),
  day: z.string(),
  features: z.record(z.number().nullable()),
});

export const scoreResponseSchema = z.object({
  drive_id: z.string(),
  day: z.string(),
  risk_score: z.number().min(0).max(1),
  risk_bucket: riskBucketSchema,
  top_reasons: z.array(z.object({
    code: z.string(),
    contribution: z.number(),
    direction: z.enum(['UP', 'DOWN']),
  })),
  model_version: z.string(),
  scored_at: z.string(),
});

export type RiskBucket = z.infer<typeof riskBucketSchema>;
export type Drive = z.infer<typeof driveSchema>;
export type FeaturePayload = z.infer<typeof featurePayloadSchema>;
export type ScoreResponse = z.infer<typeof scoreResponseSchema>;
