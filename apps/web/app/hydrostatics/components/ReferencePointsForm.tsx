"use client";

import { useHydrostaticsStore } from "@/lib/store";

function NumberField({
  label, value, onChange, step = 0.01,
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

export function ReferencePointsForm() {
  const { referencePoints, setReferencePoints } = useHydrostaticsStore();

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">Reference Points</h3>
      <div className="space-y-1.5 rounded-md border border-border p-3">
        <NumberField
          label="Baseline (Z)"
          value={referencePoints.baseline_z}
          onChange={(v) => setReferencePoints({ baseline_z: v })}
        />
        <NumberField
          label="AP (X)"
          value={referencePoints.ap_x}
          onChange={(v) => setReferencePoints({ ap_x: v })}
        />
        <NumberField
          label="FP (X)"
          value={referencePoints.fp_x}
          onChange={(v) => setReferencePoints({ fp_x: v })}
        />
        <NumberField
          label="Midship (X)"
          value={referencePoints.midship_x}
          onChange={(v) => setReferencePoints({ midship_x: v })}
        />
      </div>
      {referencePoints.baseline_z !== 0 && (
        <p className="text-[11px] text-amber-700">
          Note: this MVP assumes mesh Z=0 is the Baseline. A non-zero value
          here is not applied as an offset yet.
        </p>
      )}
    </div>
  );
}
