"use client";

import { useMutation } from "@tanstack/react-query";
import { FileUpload } from "./FileUpload";
import { ReferencePointsForm } from "./ReferencePointsForm";
import { DraftRangeForm } from "./DraftRangeForm";
import { useHydrostaticsStore } from "@/lib/store";
import { calculateHydrostatics, ApiError } from "@/lib/api-client";
import { Loader2, PlayCircle, AlertTriangle } from "lucide-react";

export function InputPanel() {
  const {
    hullUpload, referencePoints, draftParams, waterDensity,
    setResults, calculateError, setCalculateError,
  } = useHydrostaticsStore();

  const mutation = useMutation({
    mutationFn: calculateHydrostatics,
    onSuccess: (data) => {
      setResults(data);
      setCalculateError(null);
    },
    onError: (err: unknown) => {
      const message = err instanceof ApiError ? err.message : "Calculation failed.";
      setCalculateError(message);
      setResults(null);
    },
  });

  const canRun = Boolean(hullUpload) && draftParams.final_draft > draftParams.initial_draft;

  function handleRun() {
    if (!hullUpload) return;
    mutation.mutate({
      hull_id: hullUpload.hull_id,
      reference_points: referencePoints,
      draft_params: draftParams,
      water_density: waterDensity,
    });
  }

  return (
    <aside className="flex w-80 shrink-0 flex-col gap-5 overflow-y-auto border-r border-border p-4">
      <div>
        <h1 className="text-base font-semibold">Hydrostatic Calculator</h1>
        <p className="text-xs text-muted-foreground">Hull-form based, geometric-only</p>
      </div>

      <FileUpload />
      <ReferencePointsForm />
      <DraftRangeForm />

      <button
        onClick={handleRun}
        disabled={!canRun || mutation.isPending}
        className="mt-2 flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-40"
      >
        {mutation.isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <PlayCircle className="h-4 w-4" />
        )}
        Run Calculation
      </button>

      {calculateError && (
        <div className="flex items-start gap-1.5 rounded-md bg-red-50 p-2 text-xs text-red-700">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{calculateError}</span>
        </div>
      )}
    </aside>
  );
}
