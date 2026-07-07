"use client";

import { Bar, BarChart, ResponsiveContainer, Tooltip } from "recharts";

type Point = { day: string; calls: number };

export function WorkflowCallSparkline({ data }: { data: Point[] }) {
  return (
    <ResponsiveContainer width="100%" height={36}>
      <BarChart data={data} margin={{ top: 0, right: 0, bottom: 0, left: 0 }} barSize={5}>
        <Bar dataKey="calls" fill="var(--color-primary)" opacity={0.7} radius={[2, 2, 0, 0]} />
        <Tooltip
          contentStyle={{
            fontSize: 10,
            background: "var(--color-surface-container-high)",
            border: "none",
            borderRadius: 6,
          }}
          itemStyle={{ color: "var(--color-on-surface)" }}
          labelStyle={{ color: "var(--color-on-surface-variant)" }}
          cursor={{ fill: "var(--color-surface-container-highest)" }}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
