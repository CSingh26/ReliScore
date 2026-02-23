import { Skeleton } from '@/components/ui/skeleton';

export default function DriveDetailLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-56" />
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
      <Skeleton className="h-80" />
      <Skeleton className="h-80" />
    </div>
  );
}
