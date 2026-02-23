import { Skeleton } from '@/components/ui/skeleton';

export default function DrivesLoading() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-48" />
      <Skeleton className="h-12" />
      <Skeleton className="h-[520px]" />
    </div>
  );
}
