import { describe, expect, it, vi } from 'vitest';
vi.mock('../src/modules/scoring/feature-engineering', () => ({
  generateFeaturesForDay: vi.fn().mockResolvedValue(1),
  featureVectorFromRow: () => ({ temperature: 12 }),
}));
import { ScoringService } from '../src/modules/scoring/scoring.service';

describe('ScoringService score provenance', () => {
  it('persists a low model probability unchanged even when every drive is low', async () => {
    const upsert = vi.fn().mockResolvedValue({});
    const prisma = {
      featuresDaily: { findMany: vi.fn().mockResolvedValue([{driveId: 'd1', day: new Date('2026-01-01')}]) },
      prediction: {upsert}, $transaction: vi.fn().mockResolvedValue([]),
      auditLog: {create: vi.fn().mockResolvedValue({})},
    };
    const model = {scoreBatch: vi.fn().mockResolvedValue([{ drive_id: 'd1', day: '2026-01-01', risk_score: .012, risk_bucket: 'LOW', top_reasons: [], model_version: 'test', scored_at: '2026-01-01T00:00:00Z'}])};
    const result = await new ScoringService(prisma as never, {info: vi.fn()} as never, model as never).runScoringJob('2026-01-01');
    expect(upsert.mock.calls[0][0].create.riskScore).toBe(.012);
    expect(upsert.mock.calls[0][0].create.riskBucket).toBe('LOW');
    expect(result.bucketMode).toBe('model');
  });
});
