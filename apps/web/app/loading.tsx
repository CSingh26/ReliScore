import { Skeleton } from '@/components/ui/skeleton';

export default function RootLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-60" />
      <div className="grid gap-4 md:grid-cols-4">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
      <Skeleton className="h-80" />
    </div>
  );
}
