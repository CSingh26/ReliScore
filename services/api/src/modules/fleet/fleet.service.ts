import { Injectable } from '@nestjs/common';
import { Prisma } from '@prisma/client';
import { PrismaService } from '../prisma.service';

@Injectable()
export class FleetService {
  constructor(private readonly prisma: PrismaService) {}

  async getSummary(day?: string) {
    const summaryDay = day ? new Date(day) : await this.resolveLatestPredictionDay();
    const totalDrives = await this.prisma.drive.count();

    const predictionsWhere: Prisma.PredictionWhereInput = summaryDay
      ? { day: summaryDay }
      : {};

    const [drivesScoredToday, predictedFailures14d, buckets] = await Promise.all([
      this.prisma.prediction.count({ where: predictionsWhere }),
      this.prisma.prediction.count({
        where: {
          ...predictionsWhere,
          riskBucket: 'HIGH',
        },
      }),
      this.prisma.prediction.groupBy({
        by: ['riskBucket'],
        where: predictionsWhere,
        _count: {
          riskBucket: true,
        },
      }),
    ]);

    const riskDistribution = {
      LOW: 0,
      MED: 0,
      HIGH: 0,
    };

    for (const bucket of buckets) {
      riskDistribution[bucket.riskBucket] = bucket._count.riskBucket;
    }

    return {
      day: summaryDay ? summaryDay.toISOString().slice(0, 10) : null,
      totalDrives,
      drivesScoredToday,
      predictedFailures14d,
      riskDistribution,
    };
  }

  private async resolveLatestPredictionDay(): Promise<Date | null> {
    const latest = await this.prisma.prediction.findFirst({
      select: { day: true },
      orderBy: {
        day: 'desc',
      },
    });

    return latest?.day ?? null;
  }
}
