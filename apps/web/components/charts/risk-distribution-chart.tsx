'use client';

import { Pie, PieChart, ResponsiveContainer, Tooltip, Cell } from 'recharts';

const COLORS = ['#6ca164', '#dd9d3f', '#c55135'];

export function RiskDistributionChart({
  data,
}: {
  data: Array<{ bucket: string; count: number }>;
}) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data} dataKey="count" nameKey="bucket" innerRadius={56} outerRadius={95} paddingAngle={5}>
            {data.map((entry, index) => (
              <Cell key={entry.bucket} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
