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
      const response = await this.client.post('/score_batch', { items });
      return scoreBatchResponseSchema.parse(response.data);
    } catch (error) {
      throw new ServiceUnavailableException({
        message: 'Model service scoring call failed',
        detail: error instanceof Error ? error.message : String(error),
      });
    }
  }
}
