import { notFound } from 'next/navigation';
import { RiskHistoryChart } from '@/components/charts/risk-history-chart';
import { TelemetryChart } from '@/components/charts/telemetry-chart';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { getDriveDetail } from '@/lib/api';

function riskBadgeClass(bucket: string) {
  if (bucket === 'HIGH') return 'border-red-200 bg-red-50 text-red-700';
  if (bucket === 'MED') return 'border-amber-200 bg-amber-50 text-amber-700';
  return 'border-emerald-200 bg-emerald-50 text-emerald-700';
}

export default async function DriveDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await getDriveDetail(id);

  if (!response) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">Drive profile</p>
          <h2 className="text-2xl font-semibold tracking-tight">{response.drive.driveId}</h2>
          <p className="text-sm text-muted-foreground">
            {response.drive.model} • {response.drive.datacenter ?? 'n/a'}
          </p>
        </div>

        <Badge className={riskBadgeClass(response.riskHistory.at(-1)?.riskBucket ?? 'LOW')}>
          {response.riskHistory.at(-1)?.riskBucket ?? 'LOW'} Risk
        </Badge>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <Card>
          <p className="text-sm text-muted-foreground">Last Seen</p>
          <p className="mt-2 text-lg font-semibold">{response.drive.lastSeen?.slice(0, 10)}</p>
        </Card>
        <Card>
          <p className="text-sm text-muted-foreground">Capacity (TB)</p>
          <p className="mt-2 text-lg font-semibold">
            {(response.drive.capacityBytes / 1_000_000_000_000).toFixed(1)}
          </p>
        </Card>
        <Card>
          <p className="text-sm text-muted-foreground">Model Version</p>
          <p className="mt-2 text-lg font-semibold">{response.riskHistory.at(-1)?.modelVersion ?? 'n/a'}</p>
        </Card>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.1fr_1.4fr]">
        <Card>
          <h3 className="text-base font-semibold">Risk Trend</h3>
          <p className="mt-1 text-sm text-muted-foreground">Recent prediction history</p>
          {!response.riskHistory.length ? (
            <EmptyState title="No risk history" description="Run scoring to populate trend data." />
          ) : (
            <RiskHistoryChart
              data={response.riskHistory.map((point) => ({
                day: point.day.slice(5, 10),
                riskScore: point.riskScore,
              }))}
            />
          )}
        </Card>

        <Card>
          <h3 className="text-base font-semibold">Telemetry Trends</h3>
          <p className="mt-1 text-sm text-muted-foreground">SMART and temperature over time</p>
          {!response.telemetryTrend.length ? (
            <EmptyState title="No telemetry" description="Seed telemetry to render this chart." />
          ) : (
            <TelemetryChart
              data={response.telemetryTrend.map((point) => ({
                day: point.day.slice(5, 10),
                smart197: point.smart197,
                smart5: point.smart5,
                temperature: point.temperature,
              }))}
            />
          )}
        </Card>
      </section>

      <Card>
        <h3 className="text-base font-semibold">Top Reason Codes</h3>
        <p className="mt-1 text-sm text-muted-foreground">Feature contributions from latest score</p>

        {!response.topReasons.length ? (
          <p className="mt-4 text-sm text-muted-foreground">No explanation payload available.</p>
        ) : (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {response.topReasons.map((reason) => (
              <div
                key={`${reason.code}-${reason.direction}`}
                className="rounded-md border border-border/80 bg-muted/30 p-3"
              >
                <div className="flex items-center justify-between">
                  <p className="font-medium">{reason.code}</p>
                  <Badge
                    className={
                      reason.direction === 'UP'
                        ? 'border-red-200 bg-red-50 text-red-700'
                        : 'border-emerald-200 bg-emerald-50 text-emerald-700'
                    }
                  >
                    {reason.direction}
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  Contribution: {Number(reason.contribution).toFixed(4)}
                </p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
