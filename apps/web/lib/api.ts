import { DriveDetailResponse, DriveListResponse, FleetSummary } from './types';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL ?? 'http://localhost:4000/api/v1';

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      cache: 'no-store',
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function getFleetSummary(): Promise<FleetSummary | null> {
  return getJson<FleetSummary>('/fleet/summary');
}

export async function getDrives(query?: { risk?: string; page?: number; pageSize?: number }) {
  const params = new URLSearchParams();
  if (query?.risk) params.set('risk', query.risk);
  if (query?.page) params.set('page', String(query.page));
  if (query?.pageSize) params.set('pageSize', String(query.pageSize));

  const qs = params.toString();
  const path = `/drives${qs ? `?${qs}` : ''}`;
  return getJson<DriveListResponse>(path);
}

export async function getDriveDetail(id: string) {
  return getJson<DriveDetailResponse>(`/drives/${id}`);
}
