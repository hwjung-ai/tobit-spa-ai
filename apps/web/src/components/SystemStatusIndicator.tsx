"use client";

import { useCallback, useEffect, useState } from "react";
import { Server, Database, Network } from "lucide-react";
import { authenticatedFetch } from "@/lib/apiClient/index";

interface HealthEntry {
  status: string;
  detail: string;
}

const DEFAULT_HEALTH: Record<string, HealthEntry> = {
  service: { status: "ok", detail: "" },
  database: { status: "ok", detail: "" },
  network: { status: "ok", detail: "" },
};

export default function SystemStatusIndicator() {
  const [health, setHealth] = useState<Record<string, HealthEntry>>(DEFAULT_HEALTH);

  const fetchHealth = useCallback(async () => {
    try {
      const response = await authenticatedFetch<{
        data?: { health?: Record<string, HealthEntry | string> };
      }>("/ops/summary/stats");
      const data = (response as { data?: { health?: Record<string, HealthEntry | string> } })
        ?.data;
      if (data?.health) {
        // Normalise: accept both old "ok"/"error" strings and new {status, detail} objects
        const normalised: Record<string, HealthEntry> = {};
        for (const [k, v] of Object.entries(data.health)) {
          if (typeof v === "string") {
            normalised[k] = { status: v, detail: "" };
          } else {
            normalised[k] = v;
          }
        }
        setHealth(normalised);
      }
    } catch {
      // Silently ignore — status stays at last known state
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  const color = (status: string) =>
    status === "ok" ? "text-green-400" : "text-rose-400";

  const items: { icon: typeof Server; key: string; label: string }[] = [
    { icon: Server, key: "service", label: "서비스" },
    { icon: Database, key: "database", label: "DB" },
    { icon: Network, key: "network", label: "네트워크" },
  ];

  return (
    <div className="flex items-center gap-2">
      {items.map(({ icon: Icon, key, label }) => {
        const entry = health[key] ?? { status: "ok", detail: "" };
        const statusText = entry.status === "ok" ? "정상" : "장애";
        const tooltipLines = [
          `${label}: ${statusText}`,
          ...(entry.detail ? [entry.detail] : []),
        ];

        return (
          <div
            key={key}
            className="group relative flex items-center gap-1 rounded-full border border-slate-800 bg-slate-900/60 px-2 py-1"
          >
            <Icon className={`h-3.5 w-3.5 ${color(entry.status)}`} />
            <span className={`text-[11px] font-medium ${color(entry.status)}`}>
              {statusText}
            </span>
            <div className="pointer-events-none absolute top-full left-1/2 mt-2 -translate-x-1/2 whitespace-nowrap rounded bg-slate-800 px-2.5 py-1.5 text-[10px] text-white opacity-0 transition group-hover:opacity-100 z-50">
              <div className="absolute left-1/2 bottom-full -mb-1 -translate-x-1/2">
                <div className="h-2 w-2 rotate-45 bg-slate-800" />
              </div>
              {tooltipLines.map((line, i) => (
                <div key={i} className={i === 0 ? "font-semibold" : "text-slate-300 mt-0.5"}>
                  {line}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
