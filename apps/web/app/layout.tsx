import './globals.css';
import type { Metadata } from 'next';
import { ReactNode } from 'react';
import { Space_Grotesk } from 'next/font/google';
import { TopNav } from '@/components/layout/nav';

const font = Space_Grotesk({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
});

export const metadata: Metadata = {
  title: 'ReliScore Dashboard',
  description: 'Storage telemetry predictive risk dashboard',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className={font.className}>
        <TopNav />
        <main className="mx-auto max-w-7xl px-6 py-6">{children}</main>
      </body>
    </html>
  );
}
