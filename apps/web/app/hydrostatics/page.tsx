"use client";

import { useState } from "react";
import { QueryProvider } from "@/lib/query-provider";
import { InputPanel } from "./components/InputPanel";
import { HydrostaticCurves } from "./components/HydrostaticCurves";
import { ResultsTable } from "./components/ResultsTable";

type Tab = "curves" | "table";

function Dashboard() {
  const [tab, setTab] = useState<Tab>("curves");

  return (
    <div className="flex h-screen">
      <InputPanel />

      <main className="flex-1 overflow-y-auto p-4">
        <div className="mb-4 flex gap-1 border-b border-border">
          {(["curves", "table"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-2 text-sm font-medium ${
                tab === t
                  ? "border-b-2 border-primary text-primary"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {t === "curves" ? "Hydrostatic Curves" : "Results Table"}
            </button>
          ))}
        </div>

        {tab === "curves" ? <HydrostaticCurves /> : <ResultsTable />}
      </main>
    </div>
  );
}

export default function HydrostaticsPage() {
  return (
    <QueryProvider>
      <Dashboard />
    </QueryProvider>
  );
}
