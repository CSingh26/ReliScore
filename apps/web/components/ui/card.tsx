import { cn } from '@/lib/utils';
import { HTMLAttributes } from 'react';

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        'rounded-lg border border-border/80 bg-card/95 p-5 shadow-[0_6px_20px_rgba(34,35,38,0.06)] backdrop-blur',
        className,
      )}
      {...props}
    />
  );
}
