import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  async rewrites() {
    const internalApi = process.env.API_INTERNAL_URL ?? 'http://api:4000/api/v1';
    return [
      {
        source: '/backend/:path*',
        destination: `${internalApi}/:path*`,
      },
    ];
  },
};

export default nextConfig;
