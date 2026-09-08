import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma.service';

@Injectable()
export class FleetService {
  constructor(private readonly prisma: PrismaService) {}

  async getSummary(day?: string) {
    const summaryDay = day ? new Date(day) : await this.resolveLatestPredictionDay();
    const totalDrives = await this.prisma.drive.count();

    // Multiple model versions may coexist; a fleet count is per drive, never
    // the number of prediction records. Prefer the most recently scored version.
    const predictions = summaryDay ? await this.prisma.prediction.findMany({
      where: { day: summaryDay }, distinct: ['driveId'],
      orderBy: [{ scoredAt: 'desc' }, { modelVersion: 'asc' }],
      select: { riskBucket: true },
    }) : [];
    const riskDistribution = { LOW: 0, MED: 0, HIGH: 0 };
    for (const prediction of predictions) riskDistribution[prediction.riskBucket] += 1;
    const drivesScoredToday = predictions.length;
    // Historical API field name retained; this is a threshold count, not an
    // expected-failure estimate. The UI calls it High-risk drives.
    const predictedFailures30d = riskDistribution.HIGH;

    return {
      day: summaryDay ? summaryDay.toISOString().slice(0, 10) : null,
      totalDrives,
      drivesScoredToday,
      predictedFailures30d,
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
