"use client";

import {
  ComposedChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";
import { useHydrostaticsStore } from "@/lib/store";
import type { HydrostaticResult } from "@/lib/types";

// Traditional NA hydrostatic curve sheets plot Draft on the vertical axis
// (mirroring the waterline rising up the hull), with every property overlaid
// on ONE chart, each on its own horizontal scale. We replicate that with a
// single shared YAxis (draft) and one XAxis per property group (via
// xAxisId), rather than separate small charts per property.

interface LineSpec {
  key: keyof HydrostaticResult;
  label: string;
  color: string;
}

interface AxisGroup {
  id: string;
  title: string;
  orientation: "top" | "bottom";
  lines: LineSpec[];
}

// Recharts' tickLine/axisLine `transform` only moves the tick marks and the
// axis line itself -- the tick number labels are a separate rendered layer
// and need their own offset, or every stacked axis's numbers land on top of
// each other. This custom tick renders the number shifted by the same
// vertical offset as its axis's line.
function OffsetTick({
  x, y, payload, dy,
}: { x?: number; y?: number; payload?: { value: number }; dy: number }) {
  return (
    <text x={x} y={(y ?? 0) + dy} textAnchor="middle" fontSize={9} fill="hsl(var(--muted-foreground))">
      {payload?.value}
    </text>
  );
}

const AXIS_GROUPS: AxisGroup[] = [
  {
    id: "displacement",
    title: "Displacement (t) / Volume (m³)",
    orientation: "top",
    lines: [
      { key: "displacement", label: "Δ (t)", color: "#1d4ed8" },
      { key: "volume", label: "∇ (m³)", color: "#60a5fa" },
    ],
  },
  {
    id: "centers",
    title: "Centers (m)",
    orientation: "bottom",
    lines: [
      { key: "lcb", label: "LCB", color: "#dc2626" },
      { key: "lcf", label: "LCF", color: "#16a34a" },
      { key: "vcb", label: "VCB", color: "#9333ea" },
    ],
  },
  {
    id: "areas",
    title: "Areas (m²)",
    orientation: "top",
    lines: [
      { key: "aw", label: "Aw", color: "#0891b2" },
      { key: "wsa", label: "WSA", color: "#ea580c" },
    ],
  },
  {
    id: "coefficients",
    title: "Form Coefficients",
    orientation: "bottom",
    lines: [
      { key: "cb", label: "Cb", color: "#1d4ed8" },
      { key: "cm", label: "Cm", color: "#dc2626" },
      { key: "cp", label: "Cp", color: "#16a34a" },
      { key: "cw", label: "Cw", color: "#9333ea" },
    ],
  },
];

export function HydrostaticCurves() {
  const { results } = useHydrostaticsStore();

  if (!results || results.results.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Run a calculation to see hydrostatic curves.
      </div>
    );
  }

  const data = results.results;

  return (
    <div className="rounded-md border border-border p-3">
      <h4 className="mb-2 text-xs font-medium text-muted-foreground">
        Hydrostatic Curves vs. Draft
      </h4>
      <ResponsiveContainer width="100%" height={680}>
        <ComposedChart data={data} layout="vertical" margin={{ top: 150, right: 24, bottom: 150, left: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />

          <YAxis
            type="number"
            dataKey="draft"
            reversed
            tick={{ fontSize: 10 }}
            label={{ value: "Draft (m)", angle: -90, position: "insideLeft", fontSize: 11 }}
          />

          {AXIS_GROUPS.map((group, i) => {
            // Rank within its own orientation (top axes and bottom axes are
            // stacked independently), not the raw index into AXIS_GROUPS --
            // otherwise same-orientation axes can end up unevenly spaced.
            const rank = AXIS_GROUPS.slice(0, i).filter((g) => g.orientation === group.orientation).length;
            const step = 60; // px between stacked axes of the same orientation
            const offset = group.orientation === "top" ? -rank * step : rank * step;
            const labelDy = group.orientation === "top" ? offset - 14 : offset + 14;
            return (
            <XAxis
              key={group.id}
              xAxisId={group.id}
              type="number"
              orientation={group.orientation}
              tick={<OffsetTick dy={offset} />}
              tickLine={{ transform: `translate(0, ${offset})` }}
              axisLine={{ transform: `translate(0, ${offset})` }}
              label={{
                value: group.title,
                position: group.orientation === "top" ? "top" : "bottom",
                dy: labelDy,
                fontSize: 10,
              }}
            />
            );
          })}

          <Tooltip
            contentStyle={{ fontSize: 11 }}
            labelFormatter={(v) => `Draft: ${Number(v).toFixed(2)} m`}
          />
          <Legend wrapperStyle={{ fontSize: 10 }} />

          {AXIS_GROUPS.flatMap((group) =>
            group.lines.map((line) => (
              <Line
                key={line.key}
                xAxisId={group.id}
                type="monotone"
                dataKey={line.key}
                name={line.label}
                stroke={line.color}
                dot={false}
                strokeWidth={1.75}
              />
            ))
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
