"use client";

import { useHydrostaticsStore } from "@/lib/store";
import { WATER_DENSITY } from "@/lib/types";

function NumberField({
  label, value, onChange, step = 0.1,
}: { label: string; value: number; onChange: (v: number) => void; step?: number }) {
  return (
    <label className="flex items-center justify-between gap-2 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="w-24 rounded border border-border bg-background px-2 py-1 text-right font-mono-num"
      />
    </label>
  );
}

export function DraftRangeForm() {
  const { draftParams, setDraftParams, waterDensity, setWaterDensity } =
    useHydrostaticsStore();

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <h3 className="text-sm font-medium">Draft Range</h3>
        <div className="space-y-1.5 rounded-md border border-border p-3">
          <NumberField
            label="Initial Draft"
            value={draftParams.initial_draft}
            onChange={(v) => setDraftParams({ initial_draft: v })}
          />
          <NumberField
            label="Final Draft"
            value={draftParams.final_draft}
            onChange={(v) => setDraftParams({ final_draft: v })}
          />
          <NumberField
            label="Increment"
            value={draftParams.increment}
            onChange={(v) => setDraftParams({ increment: v })}
          />
          <NumberField
            label="Design Draft"
            value={draftParams.design_draft ?? 0}
            onChange={(v) => setDraftParams({ design_draft: v || null })}
          />
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-sm font-medium">Environment</h3>
        <div className="flex gap-2 rounded-md border border-border p-3">
          {[
            { label: "Freshwater (1.000)", value: WATER_DENSITY.FRESHWATER },
            { label: "Seawater (1.025)", value: WATER_DENSITY.SEAWATER },
          ].map((opt) => (
            <button
              key={opt.value}
              onClick={() => setWaterDensity(opt.value)}
              className={`flex-1 rounded px-2 py-1.5 text-xs transition-colors ${
                waterDensity === opt.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-border"
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
