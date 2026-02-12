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
      <div className="flex items-center gap-3 border-b pb-4" style={{ borderColor: "var(--border)" }}>
        <button
          onClick={() => setActiveTab("system")}
          className="px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-[0.2em] transition-all"
          style={
            activeTab === "system"
              ? {
                  backgroundColor: "rgba(56, 189, 248, 0.12)",
                  border: "1px solid rgba(56, 189, 248, 0.45)",
                  color: "#38bdf8",
                  boxShadow: "0 0 15px rgba(56, 189, 248, 0.1)",
                }
              : {
                  border: "1px solid var(--border)",
                  backgroundColor: "var(--surface-elevated)",
                  color: "var(--muted-foreground)",
                }
          }
          onMouseEnter={(e) => {
            if (activeTab !== "system") {
              e.currentTarget.style.borderColor = "var(--primary)";
              e.currentTarget.style.color = "var(--foreground)";
              e.currentTarget.style.backgroundColor = "var(--surface-base)";
            }
          }}
          onMouseLeave={(e) => {
            if (activeTab !== "system") {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.color = "var(--muted-foreground)";
              e.currentTarget.style.backgroundColor = "var(--surface-elevated)";
            }
          }}
        >
          System Monitoring
        </button>
        <button
          onClick={() => setActiveTab("cep")}
          className="px-5 py-2 rounded-lg text-xs font-bold uppercase tracking-[0.2em] transition-all"
          style={
            activeTab === "cep"
              ? {
                  backgroundColor: "rgba(52, 211, 153, 0.12)",
                  border: "1px solid rgba(52, 211, 153, 0.45)",
                  color: "#34d399",
                  boxShadow: "0 0 15px rgba(52, 211, 153, 0.1)",
                }
              : {
                  border: "1px solid var(--border)",
                  backgroundColor: "var(--surface-elevated)",
                  color: "var(--muted-foreground)",
                }
          }
          onMouseEnter={(e) => {
            if (activeTab !== "cep") {
              e.currentTarget.style.borderColor = "var(--primary)";
              e.currentTarget.style.color = "var(--foreground)";
              e.currentTarget.style.backgroundColor = "var(--surface-base)";
            }
          }}
          onMouseLeave={(e) => {
            if (activeTab !== "cep") {
              e.currentTarget.style.borderColor = "var(--border)";
              e.currentTarget.style.color = "var(--muted-foreground)";
              e.currentTarget.style.backgroundColor = "var(--surface-elevated)";
            }
          }}
        >
          CEP Monitoring
        </button>
        <div className="ml-auto text-[10px] uppercase tracking-wider" style={{ color: "var(--muted-foreground)" }}>
          {activeTab === "system" ? "Trace & Regression KPIs" : "Rules & Channels & Events"}
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === "system" && <ObservabilityDashboard />}
      {activeTab === "cep" && <CEPDashboard />}
    </div>
  );
}
