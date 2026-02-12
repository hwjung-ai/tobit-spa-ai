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
      <div className="flex items-center gap-3 border-b  pb-4 dark:" style={{borderColor: "var(--border)"}}>
        <button
          onClick={() => setActiveTab("system")}
          className={`px-5 py-2 rounded-lg text-[11px] font-bold uppercase tracking-[0.2em] transition-all ${
            activeTab === "system"
              ? "bg-sky-500/10 border border-sky-500/50 text-sky-400 shadow-[0_0_15px_rgba(56,189,248,0.1)]"
              : "border border-[var(--border)] text-[var(--muted-foreground)] hover:border-[var(--border)] hover:text-[var(--foreground)] dark:border-[var(--border)] dark:text-[var(--muted-foreground)] dark:hover:border-[var(--border)] dark:hover:text-[var(--foreground)]"
          }`}
        >
          System Monitoring
        </button>
        <button
          onClick={() => setActiveTab("cep")}
          className={`px-5 py-2 rounded-lg text-[11px] font-bold uppercase tracking-[0.2em] transition-all ${
            activeTab === "cep"
              ? "bg-emerald-500/10 border border-emerald-500/50 text-emerald-400 shadow-[0_0_15px_rgba(52,211,153,0.1)]"
              : "border border-[var(--border)] text-[var(--muted-foreground)] hover:border-[var(--border)] hover:text-[var(--foreground)] dark:border-[var(--border)] dark:text-[var(--muted-foreground)] dark:hover:border-[var(--border)] dark:hover:text-[var(--foreground)]"
          }`}
        >
          CEP Monitoring
        </button>
        <div className="ml-auto text-[10px] uppercase tracking-[0.25em]  dark:" style={{color: "var(--muted-foreground)"}}>
          {activeTab === "system" ? "Trace & Regression KPIs" : "Rules & Channels & Events"}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === "system" && <ObservabilityDashboard />}
      {activeTab === "cep" && <CEPDashboard />}
    </div>
  );
}
