"use client";

import { useHydrostaticsStore } from "@/lib/store";
import { AlertTriangle } from "lucide-react";
import type { HydrostaticResult } from "@/lib/types";

const COLUMNS: { key: keyof HydrostaticResult; label: string; digits: number }[] = [
  { key: "draft", label: "T (m)", digits: 2 },
  { key: "displacement", label: "Δ (t)", digits: 1 },
  { key: "volume", label: "∇ (m³)", digits: 1 },
  { key: "lcb", label: "LCB (m)", digits: 2 },
  { key: "vcb", label: "VCB (m)", digits: 2 },
  { key: "lcf", label: "LCF (m)", digits: 2 },
  { key: "aw", label: "Aw (m²)", digits: 1 },
  { key: "wsa", label: "WSA (m²)", digits: 1 },
  { key: "bwl", label: "Bwl (m)", digits: 2 },
  { key: "am", label: "Am (m²)", digits: 2 },
  { key: "cb", label: "Cb", digits: 3 },
  { key: "cm", label: "Cm", digits: 3 },
  { key: "cp", label: "Cp", digits: 3 },
  { key: "cw", label: "Cw", digits: 3 },
];

function exportCsv(rows: HydrostaticResult[]) {
  const header = COLUMNS.map((c) => c.label).join(",");
  const body = rows
    .map((row) => COLUMNS.map((c) => row[c.key]).join(","))
    .join("\n");
  const blob = new Blob([`${header}\n${body}`], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "hydrostatics.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export function ResultsTable() {
  const { results } = useHydrostaticsStore();

  if (!results || results.results.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
        Run a calculation to see the results table.
      </div>
    );
  }

  const designResult = results.design_draft_result;
  const rows = designResult
    ? [...results.results, designResult].sort((a, b) => a.draft - b.draft)
    : results.results;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Lpp = {results.lpp.toFixed(2)} m · ρ = {results.density} t/m³
        </p>
        <button
          onClick={() => exportCsv(results.results)}
          className="rounded border border-border px-2 py-1 text-xs hover:bg-muted"
        >
          Export CSV
        </button>
      </div>

      {results.warnings.map((w, i) => (
        <div key={i} className="flex items-start gap-1.5 rounded-md bg-amber-50 p-2 text-xs text-amber-700">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span>{w}</span>
        </div>
      ))}

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full text-xs">
          <thead className="bg-muted">
            <tr>
              {COLUMNS.map((c) => (
                <th key={c.key} className="whitespace-nowrap px-2 py-1.5 text-right font-medium">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              const isDesign = row === designResult;
              return (
                <tr
                  key={`${row.draft}-${i}`}
                  className={`font-mono-num ${
                    isDesign
                      ? "bg-blue-50 font-semibold"
                      : i % 2 === 0
                        ? "bg-background"
                        : "bg-muted/40"
                  } ${row.cp_consistency_flag ? "bg-amber-50" : ""}`}
                >
                  {COLUMNS.map((c, ci) => (
                    <td key={c.key} className="whitespace-nowrap px-2 py-1 text-right">
                      {ci === 0 && isDesign && (
                        <span className="mr-1 rounded bg-blue-600 px-1 py-0.5 text-[10px] font-semibold text-white">
                          DWL
                        </span>
                      )}
                      {(row[c.key] as number).toFixed(c.digits)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
