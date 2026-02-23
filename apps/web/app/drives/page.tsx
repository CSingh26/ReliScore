import Link from 'next/link';
import { getDrives } from '@/lib/api';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { EmptyState } from '@/components/ui/empty-state';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

function riskBadgeClass(bucket: string | undefined) {
  if (bucket === 'HIGH') return 'border-red-200 bg-red-50 text-red-700';
  if (bucket === 'MED') return 'border-amber-200 bg-amber-50 text-amber-700';
  return 'border-emerald-200 bg-emerald-50 text-emerald-700';
}

function scorePercent(score: number | undefined) {
  if (typeof score !== 'number') return 'n/a';
  return `${(score * 100).toFixed(1)}%`;
}

export default async function DrivesPage({
  searchParams,
}: {
  searchParams: Promise<{ risk?: string; page?: string }>;
}) {
  const params = await searchParams;
  const risk = (params.risk ?? '').toLowerCase();
  const page = Number(params.page ?? 1);

  const response = await getDrives({
    risk: risk || undefined,
    page,
    pageSize: 25,
  });

  if (!response) {
    return (
      <EmptyState
        title="Drive list unavailable"
        description="The API did not return drive inventory data."
      />
    );
  }

  return (
    <div className="space-y-6">
      <section className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">Drives</h2>
          <p className="text-sm text-muted-foreground">Server-side filtered drive risk inventory</p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/drives">
            <Button variant={risk ? 'outline' : 'default'} size="sm">
              All
            </Button>
          </Link>
          <Link href="/drives?risk=high">
            <Button variant={risk === 'high' ? 'default' : 'outline'} size="sm">
              High
            </Button>
          </Link>
          <Link href="/drives?risk=med">
            <Button variant={risk === 'med' ? 'default' : 'outline'} size="sm">
              Medium
            </Button>
          </Link>
          <Link href="/drives?risk=low">
            <Button variant={risk === 'low' ? 'default' : 'outline'} size="sm">
              Low
            </Button>
          </Link>
        </div>
      </section>

      <Card>
        {response.items.length === 0 ? (
          <p className="text-sm text-muted-foreground">No drives found for this filter.</p>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Drive ID</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Datacenter</TableHead>
                  <TableHead>Risk Score</TableHead>
                  <TableHead>Risk Bucket</TableHead>
                  <TableHead>Model Version</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {response.items.map((drive) => (
                  <TableRow key={drive.driveId}>
                    <TableCell>
                      <Link href={`/drives/${drive.driveId}`} className="font-medium hover:text-primary">
                        {drive.driveId}
                      </Link>
                    </TableCell>
                    <TableCell>{drive.model}</TableCell>
                    <TableCell>{drive.datacenter ?? 'n/a'}</TableCell>
                    <TableCell>{scorePercent(drive.latestPrediction?.riskScore)}</TableCell>
                    <TableCell>
                      <Badge className={riskBadgeClass(drive.latestPrediction?.riskBucket)}>
                        {drive.latestPrediction?.riskBucket ?? 'N/A'}
                      </Badge>
                    </TableCell>
                    <TableCell>{drive.latestPrediction?.modelVersion ?? 'n/a'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        <div className="mt-4 flex items-center justify-between border-t border-border/70 pt-4 text-sm text-muted-foreground">
          <span>
            Showing {(response.page - 1) * response.pageSize + 1}-
            {Math.min(response.page * response.pageSize, response.total)} of {response.total}
          </span>
          <div className="flex items-center gap-2">
            <Link href={`/drives?risk=${risk}&page=${Math.max(1, response.page - 1)}`}>
              <Button size="sm" variant="outline" disabled={response.page <= 1}>
                Prev
              </Button>
            </Link>
            <Link href={`/drives?risk=${risk}&page=${response.page + 1}`}>
              <Button
                size="sm"
                variant="outline"
                disabled={response.page * response.pageSize >= response.total}
              >
                Next
              </Button>
            </Link>
          </div>
        </div>
      </Card>
    </div>
  );
}
