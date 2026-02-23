import { describe, expect, it } from 'vitest';
import { featurePayloadSchema, riskBucketSchema } from '../src/schemas';

describe('shared schemas', () => {
  it('validates risk bucket', () => {
    expect(riskBucketSchema.parse('HIGH')).toBe('HIGH');
  });

  it('validates feature payload shape', () => {
    const parsed = featurePayloadSchema.parse({
      drive_id: 'drive-1',
      day: '2026-02-20',
      features: {
        smart_5_mean_7d: 2,
      },
    });

    expect(parsed.drive_id).toBe('drive-1');
  });
});
