"use client";

import { useState } from "react";
import ObservabilityDashboard from "@/components/admin/ObservabilityDashboard";
import CEPDashboard from "@/components/admin/observability/DashboardPage";

type DashboardTab = "system" | "cep";

export default function ObservabilityPage() {
  const [activeTab, setActiveTab] = useState<DashboardTab>("system");

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="flex items-center gap-3 border-b border-slate-200 pb-4 dark:border-slate-800">
        <button
          onClick={() => setActiveTab("system")}
          className={`px-5 py-2 rounded-lg text-[11px] font-bold uppercase tracking-[0.2em] transition-all ${
            activeTab === "system"
              ? "bg-sky-500/10 border border-sky-500/50 text-sky-400 shadow-[0_0_15px_rgba(56,189,248,0.1)]"
              : "border border-slate-300 text-slate-600 hover:border-slate-400 hover:text-slate-900 dark:border-slate-700 dark:text-slate-400 dark:hover:border-slate-600 dark:hover:text-slate-100"
          }`}
        >
          System Monitoring
        </button>
        <button
          onClick={() => setActiveTab("cep")}
          className={`px-5 py-2 rounded-lg text-[11px] font-bold uppercase tracking-[0.2em] transition-all ${
            activeTab === "cep"
              ? "bg-emerald-500/10 border border-emerald-500/50 text-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.1)]"
              : "border border-slate-300 text-slate-600 hover:border-slate-400 hover:text-slate-900 dark:border-slate-700 dark:text-slate-400 dark:hover:border-slate-600 dark:hover:text-slate-100"
          }`}
        >
          CEP Monitoring
        </button>
        <div className="ml-auto text-[10px] uppercase tracking-[0.25em] text-slate-500 dark:text-slate-500">
          {activeTab === "system" ? "Trace & Regression KPIs" : "Rules & Channels & Events"}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === "system" && <ObservabilityDashboard />}
      {activeTab === "cep" && <CEPDashboard />}
    </div>
  );
}
