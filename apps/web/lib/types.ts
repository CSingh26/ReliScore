export interface FleetSummary {
  day: string | null;
  totalDrives: number;
  drivesScoredToday: number;
  predictedFailures30d: number;
  riskDistribution: {
    LOW: number;
    MED: number;
    HIGH: number;
  };
}

export interface DriveListItem {
  driveId: string;
  model: string;
  datacenter: string | null;
  capacityBytes: number;
  firstSeen: string;
  lastSeen: string;
  latestPrediction:
    | {
        day: string;
        riskScore: number;
        riskBucket: 'LOW' | 'MED' | 'HIGH';
        modelVersion: string;
      }
    | null;
}

export interface DriveListResponse {
  page: number;
  pageSize: number;
  total: number;
  items: DriveListItem[];
}

export interface DriveDetailResponse {
  drive: {
    driveId: string;
    model: string;
    datacenter: string | null;
    capacityBytes: number;
    firstSeen: string;
    lastSeen: string;
  };
  telemetryTrend: Array<{
    day: string;
    smart5: number | null;
    smart197: number | null;
    smart198: number | null;
    smart199: number | null;
    temperature: number | null;
  }>;
  riskHistory: Array<{
    day: string;
    riskScore: number;
    riskBucket: 'LOW' | 'MED' | 'HIGH';
    modelVersion: string;
  }>;
  topReasons: Array<{ code: string; contribution: number; direction: 'UP' | 'DOWN' }>;
}
