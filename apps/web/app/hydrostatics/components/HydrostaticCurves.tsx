"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";
import { useHydrostaticsStore } from "@/lib/store";
import type { HydrostaticResult } from "@/lib/types";

// Traditional NA hydrostatic curve sheets plot Draft on the vertical axis
// (mirroring the waterline rising up the hull) with each property on its
// own horizontal scale -- we use Recharts' layout="vertical" to achieve
// this orientation rather than the library's default (independent variable
// on X).

interface CurveSpec {
  title: string;
  lines: { key: keyof HydrostaticResult; label: string; color: string }[];
}

const CURVE_GROUPS: CurveSpec[] = [
  { title: "Displacement (t)", lines: [{ key: "displacement", label: "Δ", color: "#1d4ed8" }] },
  { title: "Volume (m³)", lines: [{ key: "volume", label: "∇", color: "#1d4ed8" }] },
  {
    title: "Centers (m)",
    lines: [
      { key: "lcb", label: "LCB", color: "#dc2626" },
      { key: "lcf", label: "LCF", color: "#16a34a" },
      { key: "vcb", label: "VCB", color: "#9333ea" },
    ],
  },
  {
    title: "Areas (m²)",
    lines: [
      { key: "aw", label: "Aw", color: "#0891b2" },
      { key: "wsa", label: "WSA", color: "#ea580c" },
    ],
  },
  {
    title: "Form Coefficients",
    lines: [
      { key: "cb", label: "Cb", color: "#1d4ed8" },
      { key: "cm", label: "Cm", color: "#dc2626" },
      { key: "cp", label: "Cp", color: "#16a34a" },
      { key: "cw", label: "Cw", color: "#9333ea" },
    ],
  },
];

function SingleCurve({ spec, data }: { spec: CurveSpec; data: HydrostaticResult[] }) {
  return (
    <div className="rounded-md border border-border p-3">
      <h4 className="mb-2 text-xs font-medium text-muted-foreground">{spec.title}</h4>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} layout="vertical" margin={{ top: 4, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
          <XAxis type="number" tick={{ fontSize: 10 }} />
          <YAxis
            type="number"
            dataKey="draft"
            tick={{ fontSize: 10 }}
            label={{ value: "Draft (m)", angle: -90, position: "insideLeft", fontSize: 10 }}
          />
          <Tooltip
            contentStyle={{ fontSize: 11 }}
            labelFormatter={(v) => `Draft: ${Number(v).toFixed(2)} m`}
          />
          {spec.lines.length > 1 && <Legend wrapperStyle={{ fontSize: 10 }} />}
          {spec.lines.map((line) => (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              name={line.label}
              stroke={line.color}
              dot={false}
              strokeWidth={1.75}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HydrostaticCurves() {
  const { results } = useHydrostaticsStore();

  if (!results || results.results.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Run a calculation to see hydrostatic curves.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-4 xl:grid-cols-3">
      {CURVE_GROUPS.map((spec) => (
        <SingleCurve key={spec.title} spec={spec} data={results.results} />
      ))}
    </div>
  );
}
