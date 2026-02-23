import Link from 'next/link';
import { getDrives, getFleetSummary } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { RiskDistributionChart } from '@/components/charts/risk-distribution-chart';

function formatPercent(value: number | undefined) {
  if (typeof value !== 'number') {
    return '0%';
  }

  return `${(value * 100).toFixed(1)}%`;
}

export default async function HomePage() {
  const [summary, highRiskDrives] = await Promise.all([
    getFleetSummary(),
    getDrives({ risk: 'high', page: 1, pageSize: 10 }),
  ]);

  if (!summary) {
    return (
      <EmptyState
        title="API unavailable"
        description="Start the platform API and refresh to view live fleet risk data."
      />
    );
  }

  const distribution = [
    { bucket: 'LOW', count: summary.riskDistribution.LOW },
    { bucket: 'MED', count: summary.riskDistribution.MED },
    { bucket: 'HIGH', count: summary.riskDistribution.HIGH },
  ];

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <p className="text-sm font-medium text-muted-foreground">Fleet snapshot</p>
        <h2 className="text-2xl font-semibold tracking-tight">Overview</h2>
        <p className="text-sm text-muted-foreground">Latest scoring day: {summary.day ?? 'n/a'}</p>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <Card>
          <p className="text-sm text-muted-foreground">Total drives</p>
          <p className="mt-2 text-2xl font-semibold">{summary.totalDrives.toLocaleString()}</p>
        </Card>
        <Card>
          <p className="text-sm text-muted-foreground">Scored today</p>
          <p className="mt-2 text-2xl font-semibold">{summary.drivesScoredToday.toLocaleString()}</p>
        </Card>
        <Card>
          <p className="text-sm text-muted-foreground">Predicted failures (14d)</p>
          <p className="mt-2 text-2xl font-semibold">{summary.predictedFailures14d.toLocaleString()}</p>
        </Card>
        <Card>
          <p className="text-sm text-muted-foreground">High risk rate</p>
          <p className="mt-2 text-2xl font-semibold">
            {formatPercent(
              summary.drivesScoredToday
                ? summary.riskDistribution.HIGH / summary.drivesScoredToday
                : 0,
            )}
          </p>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1.1fr_1.3fr]">
        <Card>
          <h3 className="text-base font-semibold">Risk Distribution</h3>
          <p className="mt-1 text-sm text-muted-foreground">Fleet bucket counts by latest scored day</p>
          <RiskDistributionChart data={distribution} />
        </Card>

        <Card>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold">Highest Risk Drives</h3>
              <p className="mt-1 text-sm text-muted-foreground">Immediate triage queue</p>
            </div>
            <Link href="/drives" className="text-sm font-medium text-primary hover:underline">
              View all drives
            </Link>
          </div>

          {!highRiskDrives?.items?.length ? (
            <div className="mt-4 text-sm text-muted-foreground">No high-risk drives found.</div>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Drive</TableHead>
                    <TableHead>Model</TableHead>
                    <TableHead>Risk</TableHead>
                    <TableHead>Bucket</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {highRiskDrives.items.map((drive) => (
                    <TableRow key={drive.driveId}>
                      <TableCell>
                        <Link href={`/drives/${drive.driveId}`} className="font-medium hover:text-primary">
                          {drive.driveId}
                        </Link>
                      </TableCell>
                      <TableCell>{drive.model}</TableCell>
                      <TableCell>{formatPercent(drive.latestPrediction?.riskScore)}</TableCell>
                      <TableCell>
                        <Badge className="border-red-200 bg-red-50 text-red-700">
                          {drive.latestPrediction?.riskBucket ?? 'N/A'}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </Card>
      </section>
    </div>
  );
}
