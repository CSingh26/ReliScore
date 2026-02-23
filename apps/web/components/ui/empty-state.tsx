import { Card } from './card';

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <Card className="border-dashed text-center">
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
    </Card>
  );
}
