"use client";

import { useState } from "react";
import ObservabilityDashboard from "@/components/admin/ObservabilityDashboard";
import CEPDashboard from "@/components/admin/observability/DashboardPage";
import { cn } from "@/lib/utils";

type DashboardTab = "system" | "cep";

export default function ObservabilityPage() {
  const [activeTab, setActiveTab] = useState<DashboardTab>("system");

  return (
    <div className="space-y-6">
      {/* Tab Navigation - Standard Tab Group */}
      <div className="inline-flex rounded-xl border border-slate-300 bg-slate-100 dark:border-slate-700 dark:bg-slate-950/70 p-1">
        <button
          onClick={() => setActiveTab("system")}
          className={cn(
            "px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition rounded-lg",
            activeTab === "system"
              ? "bg-sky-600 text-white"
              : "bg-transparent text-slate-700 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800"
          )}
        >
          System
        </button>
        <button
          onClick={() => setActiveTab("cep")}
          className={cn(
            "px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition rounded-lg",
            activeTab === "cep"
              ? "bg-emerald-600 text-white"
              : "bg-transparent text-slate-700 hover:bg-slate-200 dark:text-slate-300 dark:hover:bg-slate-800"
          )}
        >
          CEP
        </button>
        <div className="ml-auto text-tiny uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {activeTab === "system" ? "Trace & Regression KPIs" : "Rules & Channels & Events"}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === "system" && <ObservabilityDashboard />}
      {activeTab === "cep" && <CEPDashboard />}
    </div>
  );
}
