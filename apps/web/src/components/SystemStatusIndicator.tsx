"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, Server, Database, Network } from "lucide-react";
import { authenticatedFetch } from "@/lib/apiClient/index";

interface HealthEntry {
  status: string;
  detail: string;
}

const DEFAULT_HEALTH: Record<string, HealthEntry> = {
  api: { status: "checking", detail: "" },
  service: { status: "ok", detail: "" },
  database: { status: "ok", detail: "" },
  network: { status: "ok", detail: "" },
};

export default function SystemStatusIndicator() {
  const [health, setHealth] = useState<Record<string, HealthEntry>>(DEFAULT_HEALTH);

  // Lightweight backend connectivity check via /health
  const checkApi = useCallback(async () => {
    try {
      const res = await fetch("/health", { signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        const json = await res.json();
        const up = json?.data?.status === "up";
        return { status: up ? "ok" : "error", detail: up ? "Backend API 정상" : "Backend 응답 비정상" };
      }
      return { status: "error", detail: `HTTP ${res.status}` };
    } catch {
      return { status: "error", detail: "Backend 연결 불가" };
    }
  }, []);

  // Full health check via /ops/summary/stats
  const fetchHealth = useCallback(async () => {
    const apiResult = await checkApi();

    let serviceHealth: Record<string, HealthEntry> = {
      service: { status: "ok", detail: "" },
      database: { status: "ok", detail: "" },
      network: { status: "ok", detail: "" },
    };

    try {
      const response = await authenticatedFetch<{
        data?: { health?: Record<string, HealthEntry | string> };
      }>("/ops/summary/stats");
      const data = (response as { data?: { health?: Record<string, HealthEntry | string> } })
        ?.data;
      if (data?.health) {
        const normalised: Record<string, HealthEntry> = {};
        for (const [k, v] of Object.entries(data.health)) {
          if (typeof v === "string") {
            normalised[k] = { status: v, detail: "" };
          } else {
            normalised[k] = v;
          }
        }
        serviceHealth = { ...serviceHealth, ...normalised };
      }
    } catch {
      // If /ops/summary/stats fails but /health succeeded, keep service entries at defaults
    }

    setHealth({
      api: apiResult,
      ...serviceHealth,
    });
  }, [checkApi]);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  const color = (status: string) =>
    status === "ok" ? "text-emerald-400" : status === "checking" ? "text-muted-foreground" : "text-rose-400";

  const items: { icon: typeof Server; key: string; label: string }[] = [
    { icon: Activity, key: "api", label: "API" },
    { icon: Server, key: "service", label: "서비스" },
    { icon: Database, key: "database", label: "DB" },
    { icon: Network, key: "network", label: "네트워크" },
  ];

  return (
    <div className="flex items-center gap-2">
      {items.map(({ icon: Icon, key, label }) => {
        const entry = health[key] ?? { status: "ok", detail: "" };
        const statusText = entry.status === "ok" ? "정상" : entry.status === "checking" ? "확인중" : "장애";
        const tooltipLines = [
          `${label}: ${statusText}`,
          ...(entry.detail ? [entry.detail] : []),
        ];

        return (
          <div
            key={key}
            className="group relative flex items-center gap-1 rounded-full border border-variant bg-surface-base px-2 py-1"

          >
            <Icon className={`h-3.5 w-3.5 ${color(entry.status)}`} />
            <span className={`text-xs font-medium ${color(entry.status)}`}>
              {statusText}
            </span>
            <div
              className="pointer-events-none absolute top-full left-1/2 mt-2 -translate-x-1/2 whitespace-nowrap rounded px-3 py-1.5 text-xs text-foreground opacity-0 transition group-hover:opacity-100 z-50"

            >
              <div className="absolute left-1/2 bottom-full -mb-1 -translate-x-1/2">
                <div className="h-2 w-2 rotate-45" />
              </div>
              {tooltipLines.map((line, i) => (
                <div
                  key={i}
                  className={i === 0 ? "font-semibold" : "mt-0.5 text-muted-foreground"}
                >
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
