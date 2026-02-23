import Link from 'next/link';
import { HardDrive, LayoutDashboard } from 'lucide-react';

const links = [
  { href: '/', label: 'Fleet Overview', icon: LayoutDashboard },
  { href: '/drives', label: 'Drives', icon: HardDrive },
];

export function TopNav() {
  return (
    <header className="sticky top-0 z-40 border-b border-border/70 bg-background/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground">ReliScore</p>
          <h1 className="text-lg font-semibold">Storage Risk Operations</h1>
        </div>

        <nav className="flex items-center gap-2">
          {links.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
