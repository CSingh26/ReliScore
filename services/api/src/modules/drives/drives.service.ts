import { Injectable, NotFoundException } from '@nestjs/common';
import { Prediction, Prisma, RiskBucket } from '@prisma/client';
import { PrismaService } from '../prisma.service';

@Injectable()
export class DrivesService {
  constructor(private readonly prisma: PrismaService) {}

  async listDrives(params: { risk?: RiskBucket; page: number; pageSize: number }) {
    const where: Prisma.DriveWhereInput = params.risk
      ? {
          predictions: {
            some: {
              riskBucket: params.risk,
            },
          },
        }
      : {};

    const [total, rows] = await Promise.all([
      this.prisma.drive.count({ where }),
      this.prisma.drive.findMany({
        where,
        skip: (params.page - 1) * params.pageSize,
        take: params.pageSize,
        orderBy: {
          driveId: 'asc',
        },
        include: {
          predictions: {
            orderBy: {
              day: 'desc',
            },
            take: 1,
          },
        },
      }),
    ]);

    return {
      page: params.page,
      pageSize: params.pageSize,
      total,
      items: rows.map((row) => ({
        driveId: row.driveId,
        model: row.model,
        datacenter: row.datacenter,
        capacityBytes: Number(row.capacityBytes ?? 0),
        firstSeen: row.firstSeen,
        lastSeen: row.lastSeen,
        latestPrediction: this.toPredictionSummary(row.predictions[0]),
      })),
    };
  }

  async getDriveDetails(driveId: string) {
    const drive = await this.prisma.drive.findUnique({ where: { driveId } });
    if (!drive) {
      throw new NotFoundException(`Drive ${driveId} not found`);
    }

    const [telemetry, predictions] = await Promise.all([
      this.prisma.telemetryDaily.findMany({
        where: { driveId },
        orderBy: { day: 'asc' },
        take: 60,
      }),
      this.prisma.prediction.findMany({
        where: { driveId },
        orderBy: { day: 'asc' },
        take: 60,
      }),
    ]);

    const latestPrediction = predictions[predictions.length - 1];

    return {
      drive: {
        driveId: drive.driveId,
        model: drive.model,
        datacenter: drive.datacenter,
        capacityBytes: Number(drive.capacityBytes ?? 0),
        firstSeen: drive.firstSeen,
        lastSeen: drive.lastSeen,
      },
      telemetryTrend: telemetry.map((point) => ({
        day: point.day,
        smart5: point.smart5,
        smart197: point.smart197,
        smart198: point.smart198,
        smart199: point.smart199,
        temperature: point.temperature,
      })),
      riskHistory: predictions.map((point) => ({
        day: point.day,
        riskScore: point.riskScore,
        riskBucket: point.riskBucket,
        modelVersion: point.modelVersion,
      })),
      topReasons: Array.isArray(latestPrediction?.reasonCodes)
        ? latestPrediction.reasonCodes
        : latestPrediction?.reasonCodes ?? [],
    };
  }

  private toPredictionSummary(prediction?: Prediction) {
    if (!prediction) {
      return null;
    }

    return {
      day: prediction.day,
      riskScore: prediction.riskScore,
      riskBucket: prediction.riskBucket,
      modelVersion: prediction.modelVersion,
      reasons: prediction.reasonCodes,
    };
  }
}
