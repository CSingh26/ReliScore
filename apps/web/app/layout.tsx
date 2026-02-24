import './globals.css';
import type { Metadata } from 'next';
import { ReactNode } from 'react';
import { TopNav } from '@/components/layout/nav';

export const metadata: Metadata = {
  title: 'ReliScore Dashboard',
  description: 'Storage telemetry predictive risk dashboard',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <TopNav />
        <main className="mx-auto max-w-7xl px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
