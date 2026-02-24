import { Injectable, ServiceUnavailableException } from '@nestjs/common';
import axios, { AxiosInstance } from 'axios';
import { scoreResponseSchema } from '@reliscore/shared';
import { z } from 'zod';
import { FeatureVector } from './feature-engineering';

interface ScoreBatchItem {
  drive_id: string;
  day: string;
  features: FeatureVector;
}

const modelInfoSchema = z.object({
  features: z.array(z.string()),
  model_version: z.string(),
  horizon_days: z.number().int(),
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

      const response = await this.client.post('/score_batch', { items: normalizedItems });
      return scoreBatchResponseSchema.parse(response.data);
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
