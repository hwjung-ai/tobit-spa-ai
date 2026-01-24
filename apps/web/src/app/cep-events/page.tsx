"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ModuleRegistry, AllCommunityModule } from "ag-grid-community";
import { AgGridReact } from "ag-grid-react";
import type { ColDef, GridApi, RowClickedEvent } from "ag-grid-community";
import { useSearchParams } from "next/navigation";
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

type CepEventSummary = {
  event_id: string;
  triggered_at: string;
  status: string;
  summary: string;
  severity: string;
  ack: boolean;
  ack_at?: string | null;
  rule_id: string | null;
  rule_name: string | null;
  notification_id: string;
};

type CepEventDetail = {
  event_id: string;
  triggered_at: string;
  status: string;
  reason: string | null;
  summary: string;
  severity: string;
  ack: boolean;
  ack_at: string | null;
  ack_by: string | null;
  rule_id: string | null;
  rule_name: string | null;
  notification_id: string;
  payload: Record<string, unknown>;
  condition_evaluated: boolean | null;
  extracted_value: unknown;
  exec_log: Record<string, unknown> | null;
};

type CepRunDetail = {
  found: boolean;
  tenant_id?: string | null;
  exec_log_id?: string | null;
  simulation_id?: string | null;
  created_at?: string;
  rule_id?: string;
  status?: string;
  duration_ms?: number;
  error_message?: string | null;
  condition_evaluated?: boolean | null;
  extracted_value?: unknown;
  evidence?: Record<string, unknown> | null;
  raw?: string | null;
  message?: string | null;
};

type SummaryResponse = {
  unacked_count: number;
  by_severity: Record<string, number>;
};

type EventListResponse = {
  events: CepEventSummary[];
  limit: number;
  offset: number;
};

ModuleRegistry.registerModules([AllCommunityModule]);

const normalizeBaseUrl = (value?: string) => {
  if (!value) {
    return "";
  }
  return value.endsWith("/") ? value.slice(0, -1) : value;
};

const formatTimestamp = (value?: string | null) => {
  if (!value) {
    return "-";
  }
  try {
    let dateStr = value;
    if (value.includes("T") && !value.endsWith("Z") && !/[+-]\d{2}:?\d{2}$/.test(value)) {
      dateStr = `${value}Z`;
    }
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
  } catch {
    return value;
  }
};

const normalizeError = (error: unknown) => {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  try {
    return JSON.stringify(error);
  } catch {
    return "Unknown error";
  }
};

export default function CepEventBrowserPage() {
  const apiBaseUrl = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  const [selectedEvent, setSelectedEvent] = useState<CepEventDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [ackedFilter, setAckedFilter] = useState<"all" | "acked" | "unacked">("unacked");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [ruleFilter, setRuleFilter] = useState<string>("");
  const [sinceFilter, setSinceFilter] = useState<string>("");
  const [untilFilter, setUntilFilter] = useState<string>("");
  const [leftWidth, setLeftWidth] = useState<number | null>(null);
  const [isResizing, setIsResizing] = useState(false);
  const [isUserSized, setIsUserSized] = useState(false);
  const gridApiRef = useRef<GridApi | null>(null);
  const queryClient = useQueryClient();
  const searchParams = useSearchParams();
  const execLogParam = searchParams.get("exec_log_id");
  const simulationParam = searchParams.get("simulation_id");
  const [runDetail, setRunDetail] = useState<CepRunDetail | null>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const columnDefs = useMemo<ColDef[]>(
    () => [
      {
        headerName: "Time",
        field: "triggered_at",
        minWidth: 180,
        valueFormatter: ({ value }) => formatTimestamp(value as string),
      },
      {
        headerName: "Severity",
        field: "severity",
        minWidth: 110,
        cellRenderer: (params: { value?: unknown }) => {
          const val = params.value ? String(params.value).toUpperCase() : "";
          let color = "text-slate-400";
          if (val === "HIGH" || val === "CRITICAL") color = "text-rose-400 font-bold";
          else if (val === "MEDIUM" || val === "WARN") color = "text-amber-400 font-bold";
          else if (val === "INFO" || val === "LOW") color = "text-sky-400";
          return <span className={color}>{val}</span>;
        },
      },
      {
        headerName: "Rule name",
        field: "rule_name",
        minWidth: 180,
      },
      {
        headerName: "Summary",
        field: "summary",
        flex: 1,
        minWidth: 240,
      },
      {
        headerName: "ACK",
        field: "ack",
        minWidth: 90,
        cellRenderer: (params: { value?: unknown }) => {
          const isAck = params.value === true;
          return (
            <span className={isAck ? "text-emerald-400/80" : "text-rose-400 font-semibold"}>
              {isAck ? "ACK" : "UNACK"}
            </span>
          );
        },
      },
    ],
    []
  );

  const defaultColDef = useMemo<ColDef>(
    () => ({
      sortable: true,
      filter: true,
      resizable: true,
    }),
    []
  );

  const eventsQueryKey = useMemo(
    () => [
      "cep-events",
      { ackedFilter, severityFilter, ruleFilter, sinceFilter, untilFilter },
    ],
    [ackedFilter, severityFilter, ruleFilter, sinceFilter, untilFilter]
  );

  const summaryQuery = useQuery({
    queryKey: ["cep-events-summary"],
    queryFn: async () => {
      const response = await fetch(`${apiBaseUrl}/cep/events/summary`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "Failed to load summary");
      }
      return payload.data?.summary as SummaryResponse;
    },
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const eventsQuery = useQuery({
    queryKey: eventsQueryKey,
    queryFn: async () => {
      const params = new URLSearchParams();
      if (ackedFilter !== "all") {
        params.set("acked", ackedFilter === "acked" ? "true" : "false");
      }
      if (severityFilter !== "all") {
        params.set("severity", severityFilter);
      }
      if (ruleFilter.trim()) {
        params.set("rule_id", ruleFilter.trim());
      }
      if (sinceFilter) {
        params.set("since", sinceFilter);
      }
      if (untilFilter) {
        params.set("until", untilFilter);
      }
      params.set("limit", "200");
      const response = await fetch(`${apiBaseUrl}/cep/events?${params.toString()}`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "Failed to load events");
      }
      const data = payload.data as EventListResponse | undefined;
      return data?.events ?? [];
    },
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  useEffect(() => {
    let canceled = false;
    if (!execLogParam && !simulationParam) {
      setRunDetail(null);
      setRunError(null);
      setRunLoading(false);
      return;
    }
    setRunLoading(true);
    setRunError(null);
    const params = new URLSearchParams();
    if (execLogParam) {
      params.set("exec_log_id", execLogParam);
    } else if (simulationParam) {
      params.set("simulation_id", simulationParam);
    }
    const url = `${apiBaseUrl}/cep/events/run${params.toString() ? `?${params.toString()}` : ""}`;
    fetch(url, { headers: { "Content-Type": "application/json" } })
      .then(async (response) => {
        const payload = await response.json().catch(() => null);
        if (!response.ok) {
          throw new Error(payload?.message ?? "Failed to load CEP run");
        }
        return payload?.data?.run ?? null;
      })
      .then((detail) => {
        if (!canceled) {
          setRunDetail(detail);
          setRunLoading(false);
        }
      })
      .catch((error) => {
        if (!canceled) {
          setRunError(error?.message ?? "Unknown error");
          setRunLoading(false);
        }
      });
    return () => {
      canceled = true;
    };
  }, [apiBaseUrl, execLogParam, simulationParam]);

  const fetchEventDetail = useCallback(
    async (eventId: string) => {
      setDetailError(null);
      try {
        const response = await fetch(`${apiBaseUrl}/cep/events/${eventId}`);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.message ?? "Failed to load event detail");
        }
        setSelectedEvent(payload.data?.event ?? null);
      } catch (error) {
        setDetailError(normalizeError(error));
        setSelectedEvent(null);
      }
    },
    [apiBaseUrl]
  );

  const handleRowClick = useCallback(
    (event: RowClickedEvent<CepEventSummary>) => {
      if (!event.data) {
        return;
      }
      fetchEventDetail(event.data.event_id);
    },
    [fetchEventDetail]
  );

  const handleAck = useCallback(async () => {
    if (!selectedEvent || selectedEvent.ack) {
      return;
    }
    try {
      const response = await fetch(`${apiBaseUrl}/cep/events/${selectedEvent.event_id}/ack`, {
        method: "POST",
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "ACK failed");
      }
      await fetchEventDetail(selectedEvent.event_id);
    } catch (error) {
      setDetailError(normalizeError(error));
    }
  }, [apiBaseUrl, fetchEventDetail, selectedEvent]);

  useEffect(() => {
    if (leftWidth === null) {
      setLeftWidth(Math.round(window.innerWidth * 0.8));
    }
  }, [leftWidth]);

  useEffect(() => {
    const eventSource = new EventSource(`${apiBaseUrl}/cep/events/stream`);
    const handleSummary = (event: MessageEvent) => {
      const data = JSON.parse(event.data) as SummaryResponse;
      queryClient.setQueryData(["cep-events-summary"], data);
    };
    const handleNewEvent = (event: MessageEvent) => {
      const data = JSON.parse(event.data) as CepEventSummary & { ack_at?: string | null };
      queryClient.setQueryData<CepEventSummary[]>(eventsQueryKey, (prev) => {
        const current = prev ?? [];
        if (current.find((item) => item.event_id === data.event_id)) {
          return current;
        }
        if (ackedFilter === "acked" && !data.ack) {
          return current;
        }
        if (ackedFilter === "unacked" && data.ack) {
          return current;
        }
        if (severityFilter !== "all" && data.severity !== severityFilter) {
          return current;
        }
        if (ruleFilter.trim() && data.rule_id !== ruleFilter.trim()) {
          return current;
        }
        return [data, ...current];
      });
    };
    const handleAckEvent = (event: MessageEvent) => {
      const data = JSON.parse(event.data) as { event_id: string; ack: boolean; ack_at?: string | null };
      queryClient.setQueryData<CepEventSummary[]>(eventsQueryKey, (prev) => {
        const current = prev ?? [];
        const next = current.map((item) =>
          item.event_id === data.event_id ? { ...item, ack: data.ack, ack_at: data.ack_at ?? null } : item
        );
        if (ackedFilter === "unacked") {
          return next.filter((item) => !item.ack);
        }
        if (ackedFilter === "acked") {
          return next.filter((item) => item.ack);
        }
        return next;
      });
    };
    eventSource.addEventListener("summary", handleSummary);
    eventSource.addEventListener("new_event", handleNewEvent);
    eventSource.addEventListener("ack_event", handleAckEvent);
    return () => eventSource.close();
  }, [ackedFilter, apiBaseUrl, eventsQueryKey, queryClient, ruleFilter, severityFilter]);

  useEffect(() => {
    const handleResize = () => {
      if (!isUserSized) {
        setLeftWidth(Math.round(window.innerWidth * 0.8));
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [isUserSized]);

  useEffect(() => {
    if (!isResizing) {
      return;
    }
    const handleMove = (event: MouseEvent) => {
      setLeftWidth(Math.max(0, event.clientX - 32));
    };
    const handleUp = () => setIsResizing(false);
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("mouseup", handleUp);
    return () => {
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("mouseup", handleUp);
    };
  }, [isResizing]);

  return (
    <div className="space-y-6 builder-shell builder-text">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold text-slate-400">CEP Event Browser</h2>
          <p className="text-sm text-slate-400">
            알림 발화 이력과 ACK 상태를 확인합니다. (SSE 갱신)
          </p>
        </div>
        <div className="flex flex-wrap gap-3 rounded-2xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-xs uppercase tracking-wider text-slate-400">
          <span>Unacked: {summaryQuery.data?.unacked_count ?? "-"}</span>
          {summaryQuery.data?.by_severity
            ? Object.entries(summaryQuery.data.by_severity).map(([key, value]) => (
              <span key={key}>
                {key}: {value}
              </span>
            ))
            : null}
        </div>
      </header>
      {runLoading ? (
        <section className="rounded-3xl border border-slate-800 bg-slate-900/70 px-5 py-4">
          <p className="text-sm text-slate-400">Loading CEP run details …</p>
        </section>
      ) : runDetail ? (
        <section className="rounded-3xl border border-slate-800 bg-slate-900/70 px-5 py-4 space-y-3">
          {runError ? (
            <p className="text-sm text-rose-300">
              {runError}
            </p>
          ) : null}
          {runDetail.found ? (
            <>
              <div className="grid grid-cols-2 gap-4 text-sm text-slate-300">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Exec Log ID</p>
                  <p className="text-slate-100">{runDetail.exec_log_id ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Simulation ID</p>
                  <p className="text-slate-100">{runDetail.simulation_id ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Rule ID</p>
                  <p className="text-slate-100">{runDetail.rule_id ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Created</p>
                  <p className="text-slate-100">{runDetail.created_at ? formatTimestamp(runDetail.created_at) : "—"}</p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Condition</p>
                  <p className="text-slate-100">
                    {runDetail.condition_evaluated == null ? "—" : String(runDetail.condition_evaluated)}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Tenant</p>
                  <p className="text-slate-100">{runDetail.tenant_id ?? "—"}</p>
                </div>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Evidence</p>
                <div className="mt-2 overflow-x-auto">
                  <table className="min-w-full text-left text-xs text-slate-300">
                    <thead>
                      <tr>
                        {["endpoint", "method", "value_path", "op", "threshold", "extracted_value", "evaluated", "status", "error"].map(
                          (column) => (
                            <th
                              key={column}
                              className="border-b border-slate-800 px-2 py-1 font-semibold uppercase tracking-[0.3em] text-slate-500"
                            >
                              {column}
                            </th>
                          )
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      <tr className="bg-slate-900/40">
                        <td className="px-2 py-1">{runDetail.evidence?.runtime_endpoint as ReactNode ?? "—"}</td>
                        <td className="px-2 py-1">{runDetail.evidence?.method as ReactNode ?? "—"}</td>
                        <td className="px-2 py-1">{runDetail.evidence?.value_path as ReactNode ?? "—"}</td>
                        <td className="px-2 py-1">{runDetail.evidence?.op as ReactNode ?? "—"}</td>
                        <td className="px-2 py-1">{runDetail.evidence?.threshold as ReactNode ?? "—"}</td>
                        <td className="px-2 py-1">{runDetail.evidence?.extracted_value as ReactNode ?? "—"}</td>
                        <td className="px-2 py-1">{String(runDetail.evidence?.condition_evaluated ?? "—")}</td>
                        <td className="px-2 py-1">{runDetail.evidence?.fetch_status as ReactNode ?? "—"}</td>
                        <td className="px-2 py-1">{runDetail.evidence?.fetch_error as ReactNode ?? "—"}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              {runDetail.raw ? (
                <details className="rounded-2xl border border-slate-800 bg-slate-900/40 p-3 text-xs text-slate-400">
                  <summary className="cursor-pointer uppercase tracking-[0.3em] text-slate-500">
                    Raw references
                  </summary>
                  <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap">{runDetail.raw}</pre>
                </details>
              ) : null}
            </>
          ) : (
            <div className="text-sm text-slate-400">
              <p className="text-slate-100 font-semibold">CEP run not found</p>
              <p>
                Tenant: {runDetail.tenant_id ?? "unknown"}, exec_log_id: {runDetail.exec_log_id ?? "없음"}, simulation_id:{" "}
                {runDetail.simulation_id ?? "없음"}
              </p>
              {runDetail.message ? <p>{runDetail.message}</p> : null}
            </div>
          )}
        </section>
      ) : null}

      <div
        className="grid gap-0"
        style={{
          gridTemplateColumns: `${leftWidth ?? 0}px 12px minmax(0, 1fr)`,
        }}
      >
        <section className="rounded-3xl border border-slate-800 bg-slate-950/60 p-4">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <select
              value={ackedFilter}
              onChange={(event) => setAckedFilter(event.target.value as typeof ackedFilter)}
              className="rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-[11px] text-slate-200 tracking-normal"
            >
              <option value="all">All</option>
              <option value="unacked">Unacked</option>
              <option value="acked">Acked</option>
            </select>
            <select
              value={severityFilter}
              onChange={(event) => setSeverityFilter(event.target.value)}
              className="rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-[11px] text-slate-200 tracking-normal"
            >
              <option value="all">Severity</option>
              <option value="info">info</option>
              <option value="warn">warn</option>
              <option value="critical">critical</option>
            </select>
            <input
              value={ruleFilter}
              onChange={(event) => setRuleFilter(event.target.value)}
              placeholder="Rule ID"
              className="rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-[11px] text-slate-200 tracking-normal"
            />
            <input
              type="datetime-local"
              value={sinceFilter}
              onChange={(event) => setSinceFilter(event.target.value)}
              className="rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-[11px] text-slate-200 tracking-normal"
            />
            <input
              type="datetime-local"
              value={untilFilter}
              onChange={(event) => setUntilFilter(event.target.value)}
              className="rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-[11px] text-slate-200 tracking-normal"
            />
            <button
              onClick={() => eventsQuery.refetch()}
              className="rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-2 text-[11px] text-slate-200 transition hover:border-slate-600 tracking-normal"
            >
              Refresh
            </button>
          </div>
          {eventsQuery.error ? (
            <p className="mb-3 text-sm text-rose-400">
              {normalizeError(eventsQuery.error)}
            </p>
          ) : null}
          <div className="ag-theme-cep h-[540px] w-full rounded-2xl border border-slate-800 bg-slate-950/70">
            <AgGridReact<CepEventSummary>
              rowData={eventsQuery.data ?? []}
              columnDefs={columnDefs}
              defaultColDef={defaultColDef}
              theme="legacy"
              rowSelection="single"
              onRowClicked={handleRowClick}
              onGridReady={(params) => {
                gridApiRef.current = params.api;
              }}
              overlayLoadingTemplate="Loading events..."
              loadingOverlayComponentParams={{}}
              loading={eventsQuery.isLoading}
              domLayout="normal"
            />
          </div>
        </section>

        <div className="flex items-stretch">
          <div
            onMouseDown={() => {
              setIsResizing(true);
              setIsUserSized(true);
            }}
            className={`mx-2 w-2 cursor-col-resize rounded-full border border-slate-800 bg-slate-900/80 ${isResizing ? "bg-sky-500/40" : ""
              }`}
            aria-hidden="true"
          />
        </div>

        <aside className="space-y-4 rounded-3xl border border-slate-800 bg-slate-950/60 p-4 overflow-y-auto custom-scrollbar max-h-[610px]">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-wider text-slate-500">Event detail</p>
              <h3 className="text-lg font-semibold text-white">
                {selectedEvent?.rule_name ?? "Select an event"}
              </h3>
              <p className="text-xs text-slate-400">
                {selectedEvent ? formatTimestamp(selectedEvent.triggered_at) : "No event selected"}
              </p>
            </div>
            {selectedEvent ? (
              <button
                onClick={handleAck}
                disabled={selectedEvent.ack}
                className="rounded-2xl border border-slate-800 bg-emerald-500/80 px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-white transition hover:bg-emerald-400 disabled:bg-slate-700"
              >
                {selectedEvent.ack ? "ACKED" : "ACK"}
              </button>
            ) : null}
          </div>
          {detailError ? <p className="text-sm text-rose-400">{detailError}</p> : null}
          {selectedEvent ? (
            <div className="space-y-3 text-sm text-slate-200">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
                <p className="text-xs uppercase tracking-wider text-slate-500">Summary</p>
                <p className="mt-2 text-sm text-slate-200">{selectedEvent.summary}</p>
              </div>
              <div className="grid gap-2 rounded-2xl border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-300">
                <p>Severity: {selectedEvent.severity}</p>
                <p>Status: {selectedEvent.status}</p>
                <p>ACK: {selectedEvent.ack ? "true" : "false"}</p>
                <p>Rule ID: {selectedEvent.rule_id ?? "-"}</p>
                <p>Notification ID: {selectedEvent.notification_id}</p>
                <p>Condition evaluated: {String(selectedEvent.condition_evaluated ?? "-")}</p>
                <p>Extracted value: {String(selectedEvent.extracted_value ?? "-")}</p>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
                <p className="text-xs uppercase tracking-wider text-slate-500">Payload</p>
                <pre className="mt-2 max-h-72 overflow-auto text-xs text-slate-200 custom-scrollbar">
                  {JSON.stringify(selectedEvent.payload, null, 2)}
                </pre>
              </div>
              {selectedEvent.exec_log ? (
                <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-3">
                  <p className="text-xs uppercase tracking-wider text-slate-500">Exec log</p>
                  <pre className="mt-2 max-h-64 overflow-auto text-xs text-slate-200 custom-scrollbar">
                    {JSON.stringify(selectedEvent.exec_log, null, 2)}
                  </pre>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-slate-400">이벤트를 선택하면 상세 정보가 표시됩니다.</p>
          )}
        </aside>
      </div>
    </div>
  );
}
