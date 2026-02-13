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
      <div className="inline-flex rounded-xl border border-border bg-surface-elevated p-1">
        <button
          onClick={() => setActiveTab("system")}
          className={cn(
            "px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition rounded-lg",
            activeTab === "system"
              ? "bg-sky-600 text-white"
              : "bg-transparent text-foreground hover:bg-surface-elevated"
          )}
        >
          System Monitoring
        </button>
        <button
          onClick={() => setActiveTab("cep")}
          className={cn(
            "px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition rounded-lg",
            activeTab === "cep"
              ? "bg-emerald-600 text-white"
              : "bg-transparent text-foreground hover:bg-surface-elevated"
          )}
        >
          Event Rule Monitoring
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "system" && <ObservabilityDashboard />}
      {activeTab === "cep" && <CEPDashboard />}
    </div>
  );
}
