'use client';

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export function TelemetryChart({
  data,
}: {
  data: Array<{ day: string; smart197: number | null; smart5: number | null; temperature: number | null }>;
}) {
  return (
    <div className="h-80 w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: 8, right: 12, top: 12, bottom: 8 }}>
          <CartesianGrid strokeDasharray="4 4" stroke="#dfdbd2" />
          <XAxis dataKey="day" tickLine={false} axisLine={false} minTickGap={20} />
          <YAxis yAxisId="smart" tickLine={false} axisLine={false} />
          <YAxis yAxisId="temp" orientation="right" tickLine={false} axisLine={false} />
          <Tooltip />
          <Line yAxisId="smart" type="monotone" dataKey="smart197" name="SMART 197" stroke="#b6552f" dot={false} strokeWidth={2.4} />
          <Line yAxisId="smart" type="monotone" dataKey="smart5" name="SMART 5" stroke="#705f4f" dot={false} strokeWidth={2} />
          <Line yAxisId="temp" type="monotone" dataKey="temperature" name="Temperature" stroke="#2f6f79" dot={false} strokeWidth={1.8} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
