import { EmptyState } from '@/components/ui/empty-state';

export default function NotFound() {
  return (
    <EmptyState
      title="Drive not found"
      description="The requested drive does not exist or has not been scored yet."
    />
  );
}
