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
      {/* Tab Navigation */}
      <div className="page-header">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setActiveTab("system")}
            className={cn(
              "px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all",
              activeTab === "system"
                ? "bg-sky-500/10 border border-sky-400/50 text-sky-400 shadow-[0_0_15px_rgba(56,189,248,0.1)]"
                : "border border-slate-300 bg-slate-50 text-slate-500 hover:border-sky-600 hover:text-slate-900 hover:bg-white dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 dark:hover:border-sky-400 dark:hover:text-slate-100 dark:hover:bg-slate-950"
            )}
          >
            System Monitoring
          </button>
          <button
            onClick={() => setActiveTab("cep")}
            className={cn(
              "px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-wider transition-all",
              activeTab === "cep"
                ? "bg-emerald-500/10 border border-emerald-400/50 text-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.1)]"
                : "border border-slate-300 bg-slate-50 text-slate-500 hover:border-sky-600 hover:text-slate-900 hover:bg-white dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400 dark:hover:border-sky-400 dark:hover:text-slate-100 dark:hover:bg-slate-950"
            )}
          >
            CEP Monitoring
          </button>
          <div className="ml-auto text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {activeTab === "system" ? "Trace & Regression KPIs" : "Rules & Channels & Events"}
          </div>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === "system" && <ObservabilityDashboard />}
      {activeTab === "cep" && <CEPDashboard />}
    </div>
  );
}
