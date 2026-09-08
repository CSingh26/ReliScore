import { Injectable, ServiceUnavailableException } from '@nestjs/common';
import axios, { AxiosInstance } from 'axios';
import { scoreResponseSchema, type ScoreResponse } from '@reliscore/shared';
import { z } from 'zod';
import { FeatureVector } from './feature-engineering';

interface ScoreBatchItem {
  drive_id: string;
  day: string;
  features: FeatureVector;
}

const modelInfoSchema = z.object({
  features: z.array(z.string().min(1)).min(1).max(256).refine(names => new Set(names).size === names.length),
  model_version: z.string(),
  horizon_days: z.literal(30),
});

const scoreBatchResponseSchema = z.array(scoreResponseSchema);

@Injectable()
export class ModelClientService {
  private readonly client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.MODEL_SERVICE_URL ?? 'http://localhost:8000',
      timeout: 15000,
      headers: process.env.MODEL_SERVICE_TOKEN
        ? {
            Authorization: `Bearer ${process.env.MODEL_SERVICE_TOKEN}`,
          }
        : {},
    });
  }

  async scoreBatch(items: ScoreBatchItem[]) {
    try {
      const infoResponse = await this.client.get('/model/info');
      const modelInfo = modelInfoSchema.parse(infoResponse.data);

      const normalizedItems = items.map((item) => ({
        drive_id: item.drive_id,
        day: item.day,
        features: this.normalizeFeatures(item.features, modelInfo.features),
      }));

      const scores: ScoreResponse[] = [];
      for (let start = 0; start < normalizedItems.length; start += 1000) {
        const batch = normalizedItems.slice(start, start + 1000);
        const response = await this.client.post('/score_batch', { items: batch });
        const parsed = scoreBatchResponseSchema.parse(response.data);
        if (parsed.length !== batch.length || parsed.some((score, index) =>
          score.drive_id !== batch[index].drive_id || score.day !== batch[index].day || score.model_version !== modelInfo.model_version
        )) throw new Error('Model response does not match requested drive/day/version');
        scores.push(...parsed);
      }
      return scores;
    } catch (error) {
      throw new ServiceUnavailableException({
        message: 'Model service scoring call failed',
        detail: error instanceof Error ? error.message : String(error),
      });
    }
  }

  private normalizeFeatures(
    features: Record<string, number>,
    expectedFeatureNames: string[],
  ): Record<string, number | null> {
    const normalized: Record<string, number | null> = {};
    for (const name of expectedFeatureNames) {
      const value = features[name];
      normalized[name] = typeof value === 'number' && Number.isFinite(value) ? value : null;
    }
    return normalized;
  }
}
