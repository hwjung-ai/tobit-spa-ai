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
      <div className="flex items-center gap-3 border-b  pb-4 dark:" style={{borderColor: "rgb(203, 213, 225)"}}>
        <button
          onClick={() => setActiveTab("system")}
          className={`px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-[0.2em] transition-all ${
            activeTab === "system"
              ? "bg-sky-500/10 border border-sky-500/50 text-sky-400 shadow-[0_0_15px_rgba(56,189,248,0.1)]"
              : "border border-slate-300 text-[var(--muted-foreground)] hover:border-slate-300 hover:text-slate-900 dark:border-slate-300 dark:text-[var(--muted-foreground)] dark:hover:border-slate-300 dark:hover:text-slate-900"
          }`}
        >
          System Monitoring
        </button>
        <button
          onClick={() => setActiveTab("cep")}
          className={`px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-[0.2em] transition-all ${
            activeTab === "cep"
              ? "bg-emerald-500/10 border border-emerald-500/50 text-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.1)]"
              : "border border-slate-300 text-[var(--muted-foreground)] hover:border-slate-300 hover:text-slate-900 dark:border-slate-300 dark:text-[var(--muted-foreground)] dark:hover:border-slate-300 dark:hover:text-slate-900"
          }`}
        >
          CEP Monitoring
        </button>
        <div className="ml-auto text-[10px] uppercase tracking-wider  dark:" style={{color: "rgb(71, 85, 105)"}}>
          {activeTab === "system" ? "Trace & Regression KPIs" : "Rules & Channels & Events"}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === "system" && <ObservabilityDashboard />}
      {activeTab === "cep" && <CEPDashboard />}
    </div>
  );
}
