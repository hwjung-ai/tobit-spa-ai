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
            "panel-tab rounded-lg",
            activeTab === "system"
              ? "panel-tab-active"
              : "panel-tab-inactive"
          )}
        >
          System Monitoring
        </button>
        <button
          onClick={() => setActiveTab("cep")}
          className={cn(
            "panel-tab rounded-lg",
            activeTab === "cep"
              ? "panel-tab-active"
              : "panel-tab-inactive"
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
