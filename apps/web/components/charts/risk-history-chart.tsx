'use client';

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

export function RiskHistoryChart({
  data,
}: {
  data: Array<{ day: string; riskScore: number }>;
}) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: 8, right: 12, top: 12, bottom: 8 }}>
          <CartesianGrid strokeDasharray="4 4" stroke="#dfdbd2" />
          <XAxis dataKey="day" tickLine={false} axisLine={false} minTickGap={22} />
          <YAxis domain={[0, 1]} tickLine={false} axisLine={false} />
          <Tooltip />
          <Line type="monotone" dataKey="riskScore" stroke="#c55135" strokeWidth={2.5} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
