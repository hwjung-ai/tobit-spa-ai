"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";

// Font size mapping from prop values to Tailwind classes
const FONT_SIZE_MAP: Record<string, string> = {
  xs: "text-xs",
  sm: "text-sm",
  base: "text-base",
  lg: "text-lg",
  xl: "text-xl",
  "2xl": "text-2xl",
  "3xl": "text-3xl",
  "4xl": "text-4xl",
};

// Font weight mapping from prop values to Tailwind classes
const FONT_WEIGHT_MAP: Record<string, string> = {
  normal: "font-normal",
  medium: "font-medium",
  semibold: "font-semibold",
  bold: "font-bold",
};
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Line,
  LineChart,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import { ScreenSchemaV1, Component } from "@/lib/ui-screen/screen.schema";
import { getComponentDescriptor } from "@/lib/ui-screen/component-registry";
import {
  applyActionResultToState,
  applyBindings,
  get,
  renderTemplate,
  set,
  setError,
  setLoading,
} from "@/lib/ui-screen/binding-engine";
import { StreamManager, extractStreamConfigs, StreamState } from "@/lib/ui-screen/stream-binding";
import { fetchApi } from "@/lib/adminUtils";
import { THEME_PRESETS, tokensToCSSVariables, ThemePreset } from "@/lib/ui-screen/design-tokens";
import type { UIScreenBlock } from "./BlockRenderer";

interface UIScreenRendererProps {
  block: UIScreenBlock;
  traceId?: string;
  onResult?: (blocks: unknown[]) => void;
  schemaOverride?: ScreenSchemaV1 | null;
}

interface UIActionPayload {
  handler: string;
  endpoint?: string;
  method?: string;
  payload_template?: Record<string, unknown>;
  continue_on_error?: boolean;
  stop_on_error?: boolean;
  retry_count?: number;
  retry_delay_ms?: number;
  run_if?: string;
  on_error_action_index?: number;
  on_error_action_indexes?: number[];
  response_mapping?: Record<string, string>;
}

interface AutoRefreshConfig {
  key: string;
  componentId: string;
  componentLabel: string;
  action: UIActionPayload;
  intervalMs: number;
  backoffMs: number;
  maxFailures: number;
}

interface AutoRefreshStatus {
  failures: number;
  lastSuccessAt: number | null;
  lastError: string | null;
  paused: boolean;
  stopped: boolean;
}

interface ActionExecutionResult {
  ok: boolean;
  error?: string;
}

interface ActionLogEntry {
  id: string;
  handler: string;
  status: "ok" | "error";
  source: "user" | "auto_refresh";
  startedAt: number;
  durationMs: number;
  attempt: number;
  error?: string;
}

type TableSortDirection = "asc" | "desc";

interface TableUiState {
  sortKey: string | null;
  sortDir: TableSortDirection;
  page: number;
}

type ConditionalStyleRule = {
  field: string;
  operator: string;
  value: string;
  color?: string;
  bg_color?: string;
  border_color?: string;
  series_name?: string;
  target?: string;
  variant?: string;
};

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class UIScreenErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("UIScreen Error Boundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-xl border border-rose-500/40 bg-rose-500/5 p-4 text-xs text-rose-200 space-y-2">
          <p className="font-semibold">Screen Rendering Error</p>
          <p className="text-rose-300">{this.state.error?.message || "Unknown error"}</p>
          <p className="text-rose-400 text-[10px]">Check browser console for details</p>
        </div>
      );
    }
    return this.props.children;
  }
}

function parseMaybeNumber(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function evaluateConditionalRule(
  leftValue: unknown,
  operatorRaw: string,
  rightValue: unknown
): boolean {
  const operator = String(operatorRaw || "eq");
  const leftNum = parseMaybeNumber(leftValue);
  const rightNum = parseMaybeNumber(rightValue);
  const leftStr = String(leftValue ?? "");
  const rightStr = String(rightValue ?? "");

  if (operator === "eq") return leftStr === rightStr;
  if (operator === "ne") return leftStr !== rightStr;
  if (operator === "contains") return leftStr.includes(rightStr);
  if (operator === "gt") {
    if (leftNum !== null && rightNum !== null) return leftNum > rightNum;
    return leftStr > rightStr;
  }
  if (operator === "gte") {
    if (leftNum !== null && rightNum !== null) return leftNum >= rightNum;
    return leftStr >= rightStr;
  }
  if (operator === "lt") {
    if (leftNum !== null && rightNum !== null) return leftNum < rightNum;
    return leftStr < rightStr;
  }
  if (operator === "lte") {
    if (leftNum !== null && rightNum !== null) return leftNum <= rightNum;
    return leftStr <= rightStr;
  }
  return false;
}

function toConditionalStyleRules(raw: unknown): ConditionalStyleRule[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    const obj = (item || {}) as Record<string, unknown>;
    return {
      field: String(obj.field || ""),
      operator: String(obj.operator || "eq"),
      value: String(obj.value ?? ""),
      color: String(obj.color || ""),
      bg_color: String(obj.bg_color || ""),
      border_color: String(obj.border_color || ""),
      series_name: String(obj.series_name || ""),
      target: String(obj.target || "auto"),
      variant: String(obj.variant || ""),
    };
  });
}

function badgeVariantClass(variant: string): string {
  const normalized = String(variant || "default").toLowerCase();
  if (normalized === "secondary") {
    return "border-[var(--border)] bg-[var(--surface-elevated)] text-[var(--foreground-secondary)]";
  }
  if (normalized === "success") {
    return "border-emerald-700 bg-emerald-900/50 text-emerald-200";
  }
  if (normalized === "warning") {
    return "border-amber-700 bg-amber-900/50 text-amber-200";
  }
  if (normalized === "danger" || normalized === "destructive") {
    return "border-rose-700 bg-rose-900/50 text-rose-200";
  }
  if (normalized === "outline") {
    return "border-[var(--border)] bg-transparent text-[var(--foreground-secondary)]";
  }
  if (normalized === "ghost") {
    return "border-transparent bg-transparent text-[var(--foreground-secondary)]";
  }
  return "border-[var(--border)] bg-[var(--surface-overlay)] text-[var(--foreground-secondary)]";
}

export default function UIScreenRenderer({
  block,
  traceId,
  onResult,
  schemaOverride,
}: UIScreenRendererProps) {
  const [screenSchema, setScreenSchema] = useState<ScreenSchemaV1 | null>(null);
  const [state, setState] = useState<Record<string, unknown>>({});
  const [activeTabs, setActiveTabs] = useState<Record<string, number>>({});
  const [activeAccordions, setActiveAccordions] = useState<Record<string, number[]>>({});
  const [tableUiState, setTableUiState] = useState<Record<string, TableUiState>>({});
  const screenId = block.screen_id;

  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [streamStates, setStreamStates] = useState<Record<string, StreamState>>({});
  const streamManagerRef = useRef<StreamManager | null>(null);
  const [autoRefreshConfigs, setAutoRefreshConfigs] = useState<AutoRefreshConfig[]>([]);
  const [autoRefreshStatus, setAutoRefreshStatus] = useState<Record<string, AutoRefreshStatus>>({});
  const [actionLogs, setActionLogs] = useState<ActionLogEntry[]>([]);
  const contextRef = useRef({
    state: {} as Record<string, unknown>,
    inputs: {} as Record<string, unknown>,
    context: {} as Record<string, unknown>,
    trace_id: traceId || null,
  });
  const inFlightAutoActionsRef = useRef<Set<string>>(new Set());
  const autoRefreshFailuresRef = useRef<Record<string, number>>({});
  const autoRefreshCooldownUntilRef = useRef<Record<string, number>>({});
  const autoRefreshControlsRef = useRef<Record<string, { paused: boolean; stopped: boolean }>>({});
  const [isFullScreen, setIsFullScreen] = useState(false);
  const lastNavigationRef = useRef<string>("");

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setLoadError(null);
      try {
        let schema: ScreenSchemaV1 | null = schemaOverride || null;

        if (!schema) {
          const assetResp = await fetchApi(`/asset-registry/assets/${screenId}?stage=published`);
          const assetData = (assetResp.data as Record<string, unknown> | undefined)?.asset || assetResp.data || assetResp;
          const asset = (assetData as Record<string, unknown>) || {};
          schema = (asset?.schema_json || asset?.screen_schema) as ScreenSchemaV1;
          if (!schema) {
            throw new Error("Asset registry response missing screen schema");
          }
        }

        if (!schema || typeof schema !== "object") {
          throw new Error("Invalid screen schema: missing or non-object");
        }

        setScreenSchema(schema);

        const initial = schema.state?.initial || {};
        const baseState: Record<string, unknown> = { ...initial, params: block.params || {} };
        const paramsPayload = (block.params || {}) as Record<string, unknown>;
        if (paramsPayload.inputs && typeof paramsPayload.inputs === "object") {
          baseState.inputs = {
            ...((baseState.inputs as Record<string, unknown>) || {}),
            ...(paramsPayload.inputs as Record<string, unknown>),
          };
        }
        if (paramsPayload.state && typeof paramsPayload.state === "object") {
          Object.assign(baseState, paramsPayload.state as Record<string, unknown>);
        }

        applyBindings(baseState, schema.bindings || null, {
          state: baseState,
          inputs: baseState.inputs as Record<string, unknown> | undefined,
          context: {},
          trace_id: traceId || null,
        });

        applyBindings(baseState, block.bindings || null, {
          state: baseState,
          inputs: baseState.inputs as Record<string, unknown> | undefined,
          context: {},
          trace_id: traceId || null,
        });

        setState(baseState);
      } catch (e) {
        const errorMsg = e instanceof Error ? e.message : String(e);
        console.error('UIScreen load error:', errorMsg);
        setLoadError(errorMsg);
      } finally {
        setIsLoading(false);
      }
    }

    load();
  }, [screenId, block.bindings, block.params, schemaOverride, traceId]);

  const context = useMemo(
    () => ({
      state,
      inputs: (state.inputs as Record<string, unknown>) || {},
      context:
        ((state.params as Record<string, unknown> | undefined)?.context as Record<
          string,
          unknown
        >) || {},
      trace_id: traceId || null,
    }),
    [state, traceId]
  );

  useEffect(() => {
    contextRef.current = context;
  }, [context]);

  // SSE Stream lifecycle management
  useEffect(() => {
    if (!screenSchema || isLoading) return;

    const components = screenSchema.components || [];
    const streamConfigs = extractStreamConfigs(
      components as Array<{ id: string; props?: Record<string, unknown> }>,
      (template: string) => {
        const result = renderTemplate(template, contextRef.current);
        return typeof result === "string" ? result : String(result ?? "");
      }
    );

    if (streamConfigs.length === 0) return;

    const manager = new StreamManager(
      (path: string, value: unknown) => {
        setState((prev) => {
          const next = { ...prev };
          set(next, path, value);
          return next;
        });
      },
      (streamId: string, streamState: StreamState) => {
        setStreamStates((prev) => ({ ...prev, [streamId]: streamState }));
      }
    );
    streamManagerRef.current = manager;

    for (const config of streamConfigs) {
      manager.subscribe(config);
    }

    return () => {
      manager.dispose();
      streamManagerRef.current = null;
    };
  }, [screenSchema, isLoading]);

  useEffect(() => {
    const nav = (state.__nav as Record<string, unknown> | undefined) || null;
    if (!nav) return;
    const to = typeof nav.to === "string" ? nav.to : "";
    if (!to) return;
    const query = nav.query && typeof nav.query === "object" ? (nav.query as Record<string, unknown>) : {};
    const queryString = Object.keys(query).length
      ? `?${new URLSearchParams(
        Object.entries(query).map(([k, v]) => [k, String(v ?? "")])
      ).toString()}`
      : "";
    const target = `${to}${queryString}`;
    if (!target || lastNavigationRef.current === target) {
      return;
    }
    lastNavigationRef.current = target;
    if (typeof window !== "undefined") {
      window.history.pushState({}, "", target);
      window.dispatchEvent(new PopStateEvent("popstate"));
    }
  }, [state.__nav]);

  const handleAction = useCallback(async (
    action: UIActionPayload,
    opts?: {
      silent?: boolean;
      runtimeContext?: Record<string, unknown>;
    }
  ): Promise<ActionExecutionResult> => {
    setState((prev) => {
      const next = { ...prev };
      setLoading(next, action.handler, true);
      setError(next, action.handler, null);
      return next;
    });

    try {
      const mergedContext = {
        ...(contextRef.current.context || {}),
        ...(opts?.runtimeContext || {}),
      };

      let data: Record<string, unknown>;
      let resultBlocks: unknown[];

      if (action.endpoint) {
        // Direct API call mode: call the specified endpoint directly
        const endpointUrl = typeof action.endpoint === "string"
          ? (renderTemplate(action.endpoint, { ...contextRef.current, context: mergedContext }) as string)
          : action.endpoint;
        const method = (action.method || "GET").toUpperCase();

        const fetchOpts: RequestInit = {
          method,
          headers: { "Content-Type": "application/json" },
        };
        if (method !== "GET" && action.payload_template) {
          fetchOpts.body = JSON.stringify(
            renderTemplate(action.payload_template, {
              ...contextRef.current,
              context: mergedContext,
            })
          );
        }

        const resp = await fetch(endpointUrl, fetchOpts);
        if (!resp.ok) {
          throw new Error(`API call failed: ${resp.status} ${resp.statusText}`);
        }
        const envelope = await resp.json();
        // Support ResponseEnvelope format (envelope.data) or plain JSON
        data = (envelope?.data as Record<string, unknown>) || envelope || {};
        resultBlocks = (data.blocks as unknown[]) || [];

        // Apply response_mapping if defined, or use state_patch, or apply entire data
        const statePatch = action.response_mapping
          ? Object.fromEntries(
            Object.entries(action.response_mapping).map(([stateKey, dataPath]) => [
              stateKey,
              get(data, dataPath),
            ])
          )
          : (data.state_patch as Record<string, unknown>) || data;

        setState((prev) => {
          const next = { ...prev };
          // Apply state_patch keys to state
          if (statePatch && typeof statePatch === "object") {
            for (const [key, value] of Object.entries(statePatch)) {
              if (key !== "blocks" && key !== "state_patch" && key !== "meta" && key !== "status") {
                set(next, key, value);
              }
            }
          }
          applyActionResultToState(next, action.handler, statePatch);
          setLoading(next, action.handler, false);
          setError(next, action.handler, null);
          return next;
        });
      } else {
        // Standard ui-actions mode: route through /ops/ui-actions
        const payload = {
          trace_id: traceId || null,
          action_id: action.handler,
          inputs: renderTemplate(
            action.payload_template || {},
            {
              ...contextRef.current,
              context: mergedContext,
            }
          ) as Record<string, unknown>,
          context: mergedContext,
          screen_id: screenId,
        };

        const resp = await fetch(`/ops/ui-actions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const envelope = await resp.json();
        data = (envelope?.data as Record<string, unknown>) || {};
        resultBlocks = (data.blocks as unknown[]) || [];
        const result = resultBlocks[0] || data;

        setState((prev) => {
          const next = { ...prev };
          applyActionResultToState(next, action.handler, result);
          setLoading(next, action.handler, false);
          setError(next, action.handler, null);
          return next;
        });
      }

      if (resultBlocks.length && onResult) {
        if (!opts?.silent) {
          onResult(resultBlocks);
        }
      }
      return { ok: true };
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : String(err);
      setState((prev) => {
        const next = { ...prev };
        setLoading(next, action.handler, false);
        setError(next, action.handler, errorMessage);
        return next;
      });
      return { ok: false, error: errorMessage };
    }
  }, [onResult, screenId, traceId]);

  const executeActionWithPolicy = useCallback(
    async (
      action: UIActionPayload,
      opts?: {
        silent?: boolean;
        runtimeContext?: Record<string, unknown>;
        source?: "user" | "auto_refresh";
      }
    ) => {
      const retryCount = Math.max(0, Number(action.retry_count || 0));
      const retryDelayMs = Math.max(0, Number(action.retry_delay_ms || 500));

      for (let attempt = 0; attempt <= retryCount; attempt += 1) {
        const startedAt = Date.now();
        const result = await handleAction(action, {
          silent: opts?.silent,
          runtimeContext: opts?.runtimeContext,
        });
        const durationMs = Date.now() - startedAt;
        setActionLogs((prev) => {
          const next: ActionLogEntry[] = [
            {
              id: `${action.handler}-${startedAt}-${attempt}`,
              handler: action.handler,
              status: result.ok ? "ok" : "error",
              source: opts?.source || "user",
              startedAt,
              durationMs,
              attempt,
              error: result.error,
            },
            ...prev,
          ];
          return next.slice(0, 30);
        });

        if (result.ok) {
          return result;
        }
        if (attempt >= retryCount) {
          return result;
        }
        if (retryDelayMs > 0) {
          const waitMs = retryDelayMs * (attempt + 1);
          await new Promise((resolve) => window.setTimeout(resolve, waitMs));
        }
      }

      return { ok: false, error: "retry policy exhausted" } as ActionExecutionResult;
    },
    [handleAction]
  );

  const executeActions = useCallback(
    async (
      actions: UIActionPayload[] | undefined,
      opts?: { silent?: boolean; runtimeContext?: Record<string, unknown> }
    ) => {
      if (!actions || actions.length === 0) return;
      const shouldRun = (action: UIActionPayload): boolean => {
        if (!action.run_if) return true;
        const rendered = renderTemplate(action.run_if, {
          ...contextRef.current,
          context: {
            ...(contextRef.current.context || {}),
            ...(opts?.runtimeContext || {}),
          },
        });
        if (typeof rendered === "boolean") return rendered;
        if (typeof rendered === "number") return rendered !== 0;
        if (typeof rendered === "string") {
          const v = rendered.trim().toLowerCase();
          if (v === "" || v === "false" || v === "0" || v === "no") return false;
          if (v === "true" || v === "1" || v === "yes") return true;
          return true;
        }
        return !!rendered;
      };
      for (let idx = 0; idx < actions.length; idx += 1) {
        const action = actions[idx];
        if (!shouldRun(action)) {
          continue;
        }
        const result = await executeActionWithPolicy(action, {
          silent: opts?.silent,
          runtimeContext: opts?.runtimeContext,
          source: opts?.silent ? "auto_refresh" : "user",
        });
        const stopOnError = action.stop_on_error !== false;
        const continueOnError = action.continue_on_error === true;
        if (!result.ok && stopOnError && !continueOnError) {
          const queue: number[] = [];
          const multiple = Array.isArray(action.on_error_action_indexes)
            ? action.on_error_action_indexes
            : [];
          for (const candidate of multiple) {
            const num = Number(candidate);
            if (Number.isFinite(num) && num >= 0 && num !== idx) {
              queue.push(num);
            }
          }
          const fallbackIndex = Number(action.on_error_action_index ?? -1);
          if (Number.isFinite(fallbackIndex) && fallbackIndex >= 0 && fallbackIndex !== idx) {
            queue.push(fallbackIndex);
          }
          const fallbackOrder = [...new Set(queue)];
          for (const fallbackIdx of fallbackOrder) {
            if (fallbackIdx < 0 || fallbackIdx >= actions.length) continue;
            const fallback = actions[fallbackIdx];
            const fallbackResult = await executeActionWithPolicy(fallback, {
              silent: opts?.silent,
              runtimeContext: opts?.runtimeContext,
              source: opts?.silent ? "auto_refresh" : "user",
            });
            if (fallbackResult.ok) {
              break;
            }
          }
          break;
        }
      }
    },
    [executeActionWithPolicy]
  );

  const toggleAutoRefreshPaused = useCallback((key: string) => {
    const current = autoRefreshControlsRef.current[key] || { paused: false, stopped: false };
    autoRefreshControlsRef.current[key] = { ...current, paused: !current.paused };
    setAutoRefreshStatus((prev) => ({
      ...prev,
      [key]: {
        failures: prev[key]?.failures || 0,
        lastSuccessAt: prev[key]?.lastSuccessAt || null,
        lastError: prev[key]?.lastError || null,
        paused: !current.paused,
        stopped: current.stopped,
      },
    }));
  }, []);

  useEffect(() => {
    const collectAutoRefreshConfigs = (components: Component[]): AutoRefreshConfig[] => {
      const out: AutoRefreshConfig[] = [];
      const walk = (items: Component[]) => {
        for (const comp of items) {
          const props = (comp.props || {}) as Record<string, unknown>;
          const autoRefresh = (props.auto_refresh ||
            props.refresh ||
            null) as Record<string, unknown> | null;
          const legacyInterval = Number(props.refresh_interval_ms || 0);
          const actions = comp.actions || [];

          if (actions.length > 0) {
            const configuredEnabled = autoRefresh ? autoRefresh.enabled !== false : true;
            const intervalRaw = autoRefresh ? Number(autoRefresh.interval_ms || 0) : 0;
            const intervalMs = intervalRaw > 0 ? intervalRaw : legacyInterval;
            if (configuredEnabled && intervalMs > 0) {
              const actionIndexRaw = autoRefresh ? Number(autoRefresh.action_index || 0) : 0;
              const actionIndex = Number.isFinite(actionIndexRaw) ? actionIndexRaw : 0;
              const selectedAction = actions[actionIndex] || actions[0];
              if (selectedAction?.handler) {
                const maxFailuresRaw = autoRefresh
                  ? Number(autoRefresh.max_failures || 3)
                  : 3;
                const backoffRaw = autoRefresh
                  ? Number(autoRefresh.backoff_ms || 0)
                  : 0;
                const config: AutoRefreshConfig = {
                  key: `${comp.id}:${selectedAction.handler}:${actionIndex}`,
                  componentId: comp.id,
                  componentLabel: comp.label || comp.id,
                  action: {
                    handler: selectedAction.handler,
                    payload_template: selectedAction.payload_template || {},
                  },
                  intervalMs: Math.max(1000, intervalMs),
                  backoffMs: Math.max(0, backoffRaw),
                  maxFailures: Math.max(1, maxFailuresRaw),
                };
                out.push(config);
              }
            }
          }

          const propChildren = (props.components as Component[]) || [];
          const directChildren = ((comp as unknown as { children?: Component[] }).children || []);
          if (propChildren.length > 0) walk(propChildren);
          if (directChildren.length > 0) walk(directChildren);
        }
      };
      walk(components);
      return out;
    };

    if (!screenSchema) {
      return;
    }

    const configs = collectAutoRefreshConfigs(screenSchema.components || []);
    setAutoRefreshConfigs(configs);
    if (configs.length === 0) {
      return;
    }

    setAutoRefreshStatus((prev) => {
      const next = { ...prev };
      for (const config of configs) {
        if (!next[config.key]) {
          next[config.key] = {
            failures: 0,
            lastSuccessAt: null,
            lastError: null,
            paused: false,
            stopped: false,
          };
        }
        if (!autoRefreshControlsRef.current[config.key]) {
          autoRefreshControlsRef.current[config.key] = {
            paused: false,
            stopped: false,
          };
        }
      }
      return next;
    });

    const timers: number[] = [];
    let disposed = false;

    // Execute all auto-refresh actions immediately on mount
    configs.forEach((config) => {
      void (async () => {
        if (disposed) return;
        try {
          await executeActionWithPolicy(config.action, {
            silent: true,
            source: "auto_refresh",
          });
        } catch {
          // ignore initial load errors
        }
      })();
    });

    configs.forEach((config) => {
      const timer = window.setInterval(async () => {
        if (disposed) return;
        const control = autoRefreshControlsRef.current[config.key];
        if (control?.paused || control?.stopped) return;
        if (typeof document !== "undefined" && document.hidden) return;

        const cooldownUntil = autoRefreshCooldownUntilRef.current[config.key] || 0;
        if (Date.now() < cooldownUntil) return;

        if (inFlightAutoActionsRef.current.has(config.key)) return;
        inFlightAutoActionsRef.current.add(config.key);

        try {
          const result = await executeActionWithPolicy(config.action, {
            silent: true,
            source: "auto_refresh",
          });
          if (result.ok) {
            autoRefreshFailuresRef.current[config.key] = 0;
            autoRefreshCooldownUntilRef.current[config.key] = 0;
            setAutoRefreshStatus((prev) => ({
              ...prev,
              [config.key]: {
                failures: 0,
                lastSuccessAt: Date.now(),
                lastError: null,
                paused: autoRefreshControlsRef.current[config.key]?.paused || false,
                stopped: autoRefreshControlsRef.current[config.key]?.stopped || false,
              },
            }));
            return;
          }

          const nextFailures = (autoRefreshFailuresRef.current[config.key] || 0) + 1;
          autoRefreshFailuresRef.current[config.key] = nextFailures;

          if (nextFailures >= config.maxFailures) {
            autoRefreshCooldownUntilRef.current[config.key] = Number.MAX_SAFE_INTEGER;
            autoRefreshControlsRef.current[config.key] = { paused: false, stopped: true };
            setAutoRefreshStatus((prev) => ({
              ...prev,
              [config.key]: {
                failures: nextFailures,
                lastSuccessAt: prev[config.key]?.lastSuccessAt || null,
                lastError: `Stopped after ${nextFailures} failures`,
                paused: false,
                stopped: true,
              },
            }));
            return;
          }

          if (config.backoffMs > 0) {
            const backoffMultiplier = 2 ** Math.max(0, nextFailures - 1);
            autoRefreshCooldownUntilRef.current[config.key] =
              Date.now() + config.backoffMs * backoffMultiplier;
          }
          setAutoRefreshStatus((prev) => ({
            ...prev,
            [config.key]: {
              failures: nextFailures,
              lastSuccessAt: prev[config.key]?.lastSuccessAt || null,
              lastError: `refresh failed (${nextFailures}/${config.maxFailures})`,
              paused: autoRefreshControlsRef.current[config.key]?.paused || false,
              stopped: autoRefreshControlsRef.current[config.key]?.stopped || false,
            },
          }));
        } finally {
          inFlightAutoActionsRef.current.delete(config.key);
        }
      }, config.intervalMs);
      timers.push(timer);
    });

    return () => {
      disposed = true;
      timers.forEach((timer) => window.clearInterval(timer));
    };
  }, [executeActionWithPolicy, screenSchema]);

  const handleInputChange = (component: Component, value: unknown) => {
    setState((prev) => {
      const next = { ...prev };
      const path = component.bind || `state.${component.id}`;
      set(next, path.replace(/^state\./, ""), value);

      const inputs = { ...(next.inputs as Record<string, unknown>) || {} };
      const inputKey = (component.props?.name as string) || component.id;
      inputs[inputKey] = value;
      next.inputs = inputs;
      return next;
    });
  };

  const scopedThemeVars = useMemo<React.CSSProperties>(() => {
    if (!screenSchema?.theme) {
      return {};
    }

    const styleVars: React.CSSProperties = {};
    const preset = screenSchema.theme.preset;
    if (preset && (preset as ThemePreset) in THEME_PRESETS) {
      const presetVars = tokensToCSSVariables(THEME_PRESETS[preset as ThemePreset]);
      Object.assign(styleVars, presetVars as React.CSSProperties);
    }

    const overrides = screenSchema.theme.overrides;
    if (overrides && typeof overrides === "object") {
      for (const [key, value] of Object.entries(overrides)) {
        if (typeof value !== "string" && typeof value !== "number") continue;
        const cssVarKey = key.startsWith("--") ? key : `--${key}`;
        (styleVars as Record<string, string | number>)[cssVarKey] = value;
      }
    }

    return styleVars;
  }, [screenSchema?.theme]);

  if (loadError) {
    return (
      <div className="rounded-xl border border-rose-500/40 bg-rose-500/5 p-4 text-sm text-rose-200 space-y-2">
        <p className="font-semibold">Failed to load screen</p>
        <p className="text-rose-300 text-xs">{loadError}</p>
        <p className="text-rose-400 text-[10px]">Screen ID: {screenId}</p>
      </div>
    );
  }

  if (isLoading || !screenSchema) {
    return (
      <div className="rounded-xl border border-variant bg-surface-overlay p-4 text-sm text-foreground-secondary animate-pulse">
        Loading screen {screenId}...
      </div>
    );
  }

  const evaluateVisibility = (rule: unknown): boolean => {
    if (rule === null || rule === undefined || rule === "") return true;
    const rendered =
      typeof rule === "string" ? renderTemplate(rule, context) : rule;
    if (typeof rendered === "boolean") return rendered;
    if (typeof rendered === "number") return rendered !== 0;
    if (typeof rendered === "string") {
      const normalized = rendered.trim().toLowerCase();
      if (normalized === "" || normalized === "false" || normalized === "0" || normalized === "no") {
        return false;
      }
      if (normalized === "true" || normalized === "1" || normalized === "yes") {
        return true;
      }
      return true;
    }
    if (Array.isArray(rendered)) return rendered.length > 0;
    return !!rendered;
  };

  const renderComponent = (comp: Component): React.ReactNode => {
    if (!evaluateVisibility(comp.visibility?.rule)) {
      return null;
    }
    const desc = getComponentDescriptor(comp.type);
    const boundValue = comp.bind ? get(state, comp.bind.replace(/^state\./, "")) : undefined;
    const props = renderTemplate(comp.props || {}, context) as Record<string, unknown>;

    if (!desc) {
      return (
        <div key={comp.id} className="rounded-xl border border-rose-500/40 bg-rose-500/5 p-3 text-xs text-rose-200">
          Unsupported component: {comp.type}
        </div>
      );
    }

    if (comp.type === "text") {
      const content = (props.content as string) || String(boundValue || comp.label || "");
      const fontSize = FONT_SIZE_MAP[(props.fontSize as string) || "sm"] || "text-sm";
      const fontWeight = FONT_WEIGHT_MAP[(props.fontWeight as string) || "normal"] || "font-normal";
      return (
        <div key={comp.id} className={`${fontSize} ${fontWeight} text-foreground`} data-testid={`component-text-${comp.id}`}>
          {content}
        </div>
      );
    }

    if (comp.type === "markdown") {
      const content = (props.content as string) || String(boundValue || comp.label || "");
      return (
        <div key={comp.id} className="prose prose-invert max-w-none text-sm" data-testid={`component-markdown-${comp.id}`}>
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      );
    }

    if (comp.type === "button") {
      const label = comp.label || (props.label as string) || "Button";
      const disabled = !!props.disabled;
      const actionId = comp.actions?.[0]?.handler;
      const isLoadingAction = actionId ? !!(state.__loading as Record<string, boolean>)?.[actionId] : false;
      return (
        <button
          key={comp.id}
          type="button"
          className="rounded-full border px-4 py-2 text-xs uppercase tracking-wider hover:border-sky-500 border-slate-200 dark:border-slate-700 text-foreground"
          disabled={disabled || isLoadingAction}
          onClick={() => executeActions(comp.actions as UIActionPayload[])}
          data-testid={`component-button-${comp.id}`}
        >
          {isLoadingAction ? "Loading..." : label}
        </button>
      );
    }

    if (comp.type === "input") {
      const value = boundValue ?? props.default ?? "";
      return (
        <input
          key={comp.id}
          className="w-full rounded-xl border border-variant px-3 py-2 text-sm text-foreground bg-surface-base"
          placeholder={props.placeholder as string}
          type={(props.inputType as string) || "text"}
          value={String(value)}
          onChange={(e) => handleInputChange(comp, e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && comp.actions?.length) {
              executeActions(comp.actions as UIActionPayload[]);
            }
          }}
          data-testid={`component-input-${comp.id}`}
        />
      );
    }

    if (comp.type === "form") {
      const title = String(props.title || comp.label || "Form");
      const submitLabel = String(props.submit_label || "Submit");
      const children = (props.components as Component[]) || [];
      return (
        <form
          key={comp.id}
          className="space-y-3 rounded-2xl border border-variant bg-surface-overlay p-4"
          onSubmit={(e) => {
            e.preventDefault();
            void executeActions(comp.actions as UIActionPayload[]);
          }}
          data-testid={`component-form-${comp.id}`}
        >
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
            {title}
          </div>
          <div className="space-y-3">{children.map((child) => renderComponent(child))}</div>
          <div className="pt-1">
            <button
              type="submit"
              className="rounded-full border px-4 py-2 text-xs uppercase tracking-wider hover:border-sky-500 border-slate-200 dark:border-slate-700 text-foreground"
            >
              {submitLabel}
            </button>
          </div>
        </form>
      );
    }

    if (comp.type === "table") {
      const rawRows = (props.rows as unknown[]) || (boundValue as unknown[]) || [];
      const rows = Array.isArray(rawRows) ? rawRows : [];
      const explicitColumns = Array.isArray(props.columns)
        ? (props.columns as unknown[])
        : [];
      const columnsMeta =
        explicitColumns.length > 0
          ? explicitColumns.map((col) => {
            if (typeof col === "string") {
              return { key: col, label: col, sortable: true, format: "" };
            }
            const meta = col as Record<string, unknown>;
            const key = String(meta.field || meta.key || "");
            return {
              key,
              label: String(meta.header || meta.label || key),
              sortable: meta.sortable !== false,
              format: String(meta.format || ""),
            };
          })
          : (Array.isArray(rows[0]) ? [] : Object.keys((rows[0] as Record<string, unknown>) || {})).map(
            (key) => ({ key, label: key, sortable: true, format: "" })
          );
      const conditionalRules = toConditionalStyleRules(props.conditional_styles);
      const resolveCellStyle = (field: string, cellValue: unknown): React.CSSProperties => {
        for (const rule of conditionalRules) {
          if (rule.field !== field) continue;
          if (!evaluateConditionalRule(cellValue, rule.operator, rule.value)) continue;
          return {
            color: String(rule.color || ""),
            backgroundColor: String(rule.bg_color || ""),
            borderColor: String(rule.border_color || ""),
            fontWeight: 600,
          };
        }
        return {};
      };
      const formatCell = (value: unknown, format: string) => {
        if (value === null || value === undefined) return "";
        if (!format) return String(value);
        if (format === "number") {
          const n = Number(value);
          return Number.isFinite(n) ? n.toLocaleString() : String(value);
        }
        if (format === "percent") {
          const n = Number(value);
          return Number.isFinite(n) ? `${(n * 100).toFixed(1)}%` : String(value);
        }
        if (format === "date") {
          const d = new Date(String(value));
          return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString();
        }
        if (format === "datetime") {
          const d = new Date(String(value));
          return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
        }
        return String(value);
      };

      const sortableEnabled = props.sortable !== false;
      const rowClickActionIndex = Number(
        props.row_click_action_index ?? props.rowClickActionIndex ?? -1
      );
      const pageSizeRaw = Number(props.page_size ?? props.pageSize ?? 0);
      const pageSize = Number.isFinite(pageSizeRaw) && pageSizeRaw > 0 ? pageSizeRaw : 0;
      const currentTableState = tableUiState[comp.id] || {
        sortKey: null,
        sortDir: "asc" as TableSortDirection,
        page: 0,
      };

      const processedRows =
        sortableEnabled && currentTableState.sortKey
          ? [...rows].sort((a, b) => {
            const key = currentTableState.sortKey as string;
            const av = (a as Record<string, unknown>)?.[key];
            const bv = (b as Record<string, unknown>)?.[key];
            const aNorm = av === null || av === undefined ? "" : String(av).toLowerCase();
            const bNorm = bv === null || bv === undefined ? "" : String(bv).toLowerCase();
            if (aNorm < bNorm) return currentTableState.sortDir === "asc" ? -1 : 1;
            if (aNorm > bNorm) return currentTableState.sortDir === "asc" ? 1 : -1;
            return 0;
          })
          : [...rows];

      const totalPages = pageSize > 0 ? Math.max(1, Math.ceil(processedRows.length / pageSize)) : 1;
      const safePage = Math.min(currentTableState.page, totalPages - 1);
      const pagedRows =
        pageSize > 0
          ? processedRows.slice(safePage * pageSize, safePage * pageSize + pageSize)
          : processedRows;

      const updateTableState = (updater: (prev: TableUiState) => TableUiState) => {
        setTableUiState((prev) => {
          const base = prev[comp.id] || {
            sortKey: null,
            sortDir: "asc" as TableSortDirection,
            page: 0,
          };
          return {
            ...prev,
            [comp.id]: updater(base),
          };
        });
      };

      return (
        <div key={comp.id} className="space-y-2" data-testid={`component-table-${comp.id}`}>
          <table className="min-w-full border border-variant text-xs">
            <thead className="bg-surface-base text-muted-foreground">
              <tr>
                {columnsMeta.map((col) => {
                  const isSorted = currentTableState.sortKey === col.key;
                  const sortIndicator = isSorted
                    ? currentTableState.sortDir === "asc"
                      ? " ▲"
                      : " ▼"
                    : "";
                  return (
                    <th key={col.key} className="border border-variant px-2 py-1 text-left">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1"
                        disabled={!sortableEnabled || !col.sortable || !col.key}
                        onClick={() => {
                          if (!sortableEnabled || !col.sortable || !col.key) return;
                          updateTableState((prev) => {
                            if (prev.sortKey === col.key) {
                              return {
                                ...prev,
                                sortDir: prev.sortDir === "asc" ? "desc" : "asc",
                                page: 0,
                              };
                            }
                            return { ...prev, sortKey: col.key, sortDir: "asc", page: 0 };
                          });
                        }}
                      >
                        {col.label}
                        {sortIndicator}
                      </button>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {pagedRows.map((row: unknown, index: number) => (
                <tr
                  key={`${comp.id}-row-${index}`}
                  className={`border border-variant bg-surface-overlay ${rowClickActionIndex >= 0 ? "cursor-pointer hover:" : ""
                    }`}
                  onClick={() => {
                    if (rowClickActionIndex < 0) return;
                    const rowAction = (comp.actions || [])[rowClickActionIndex];
                    if (!rowAction) return;
                    setState((prev) => ({ ...prev, selected_row: row }));
                    void executeActions([rowAction as UIActionPayload], {
                      runtimeContext: {
                        row,
                        row_index: index,
                        component_id: comp.id,
                      },
                    });
                  }}
                >
                  {columnsMeta.map((col) => (
                    <td
                      key={`${comp.id}-${col.key}-${index}`}
                      className="border border-variant px-2 py-1"
                      style={{
                        ...(resolveCellStyle(col.key, (row as Record<string, unknown>)?.[col.key]) || {}),
                      }}
                    >
                      {formatCell((row as Record<string, unknown>)?.[col.key], col.format)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          {pageSize > 0 && (
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>
                Page {safePage + 1}/{totalPages} · {processedRows.length} rows
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className="rounded border border-variant px-2 py-1 disabled:opacity-40"
                  disabled={safePage <= 0}
                  onClick={() =>
                    updateTableState((prev) => ({ ...prev, page: Math.max(0, prev.page - 1) }))
                  }
                >
                  Prev
                </button>
                <button
                  type="button"
                  className="rounded border border-variant px-2 py-1 disabled:opacity-40"
                  disabled={safePage >= totalPages - 1}
                  onClick={() =>
                    updateTableState((prev) => ({
                      ...prev,
                      page: Math.min(totalPages - 1, prev.page + 1),
                    }))
                  }
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      );
    }

    if (comp.type === "chart") {
      const rawSeries = Array.isArray(props.series) ? (props.series as unknown[]) : [];
      const rows = (props.data as unknown[]) || (boundValue as unknown[]) || [];
      const firstSeries = rawSeries[0] as Record<string, unknown> | undefined;
      const fallbackData = (firstSeries?.data as unknown[]) || [];
      const data = Array.isArray(rows) && rows.length > 0 ? rows : fallbackData;
      const xKey = String(props.x_key || props.xKey || "x");
      const chartType = String(props.chart_type || props.type || "line").toLowerCase();
      const seriesDefs =
        rawSeries.length > 0
          ? rawSeries.map((item, index) => {
            const def = item as Record<string, unknown>;
            const dataKey = String(
              def.data_key || def.dataKey || def.key || (index === 0 ? "y" : `y${index + 1}`)
            );
            return {
              dataKey,
              stroke: String(def.color || def.stroke || "#38bdf8"),
              name: String(def.name || dataKey),
            };
          })
          : [{ dataKey: "y", stroke: "#38bdf8", name: "y" }];
      const conditionalRules = toConditionalStyleRules(props.conditional_styles);
      const latestRow =
        Array.isArray(data) && data.length > 0
          ? (data[data.length - 1] as Record<string, unknown>)
          : null;
      const styleBySeries = new Map<
        string,
        {
          stroke?: string;
          fill?: string;
          dotFill?: string;
          dotStroke?: string;
        }
      >();
      if (latestRow) {
        for (const rule of conditionalRules) {
          const targetField = rule.field;
          if (!targetField) continue;
          const leftValue = latestRow[targetField];
          if (!evaluateConditionalRule(leftValue, rule.operator, rule.value)) continue;
          const targetSeries = rule.series_name || targetField;
          const target = String(rule.target || "auto").toLowerCase();
          const prev = styleBySeries.get(targetSeries) || {};
          const next = { ...prev };
          if (target === "area") {
            if (rule.bg_color || rule.color) next.fill = rule.bg_color || rule.color;
            if (rule.color) next.stroke = rule.color;
          } else if (target === "point" || target === "dot") {
            if (rule.color) next.dotFill = rule.color;
            if (rule.border_color || rule.color) next.dotStroke = rule.border_color || rule.color;
          } else if (target === "bar" || target === "pie") {
            if (rule.bg_color || rule.color) next.fill = rule.bg_color || rule.color;
            if (rule.color) next.stroke = rule.color;
          } else {
            if (rule.color) next.stroke = rule.color;
            if (rule.bg_color) next.fill = rule.bg_color;
            if (rule.border_color) next.dotStroke = rule.border_color;
          }
          styleBySeries.set(targetSeries, next);
        }
      }
      const showLegend = props.show_legend !== false;
      const showGrid = props.show_grid !== false;
      const yAxis = (props.y_axis || {}) as Record<string, unknown>;
      const yMin = (yAxis.min as number | undefined) ?? (props.y_min as number | undefined);
      const yMax = (yAxis.max as number | undefined) ?? (props.y_max as number | undefined);
      const yTitle = String(yAxis.title || "");
      const legendCfg = (props.legend || {}) as Record<string, unknown>;
      const tooltipCfg = (props.tooltip || {}) as Record<string, unknown>;
      const containerHeight = Number(props.height || 208);
      const isResponsive = props.responsive !== false;
      const pieDataKey = seriesDefs[0]?.dataKey || "value";

      const renderChartBody = () => {
        if (chartType === "bar") {
          return (
            <BarChart data={data as Record<string, unknown>[]}>
              {showGrid && <CartesianGrid stroke="var(--chart-grid-color)" strokeDasharray="3 3" />}
              <XAxis dataKey={xKey} stroke="var(--chart-text-color)" />
              <YAxis
                stroke="var(--chart-text-color)"
                domain={[yMin !== undefined ? yMin : "auto", yMax !== undefined ? yMax : "auto"]}
                label={yTitle ? { value: yTitle, angle: -90, position: "insideLeft" } : undefined}
              />
              <Tooltip {...(tooltipCfg as object)} />
              {showLegend && <Legend {...(legendCfg as object)} />}
              {seriesDefs.map((serie) => (
                <Bar
                  key={`${comp.id}-${serie.dataKey}`}
                  dataKey={serie.dataKey}
                  fill={
                    styleBySeries.get(serie.name)?.fill ||
                    styleBySeries.get(serie.name)?.stroke ||
                    styleBySeries.get(serie.dataKey)?.fill ||
                    styleBySeries.get(serie.dataKey)?.stroke ||
                    serie.stroke
                  }
                  name={serie.name}
                />
              ))}
            </BarChart>
          );
        }

        if (chartType === "area") {
          return (
            <AreaChart data={data as Record<string, unknown>[]}>
              {showGrid && <CartesianGrid stroke="var(--chart-grid-color)" strokeDasharray="3 3" />}
              <XAxis dataKey={xKey} stroke="var(--chart-text-color)" />
              <YAxis
                stroke="var(--chart-text-color)"
                domain={[yMin !== undefined ? yMin : "auto", yMax !== undefined ? yMax : "auto"]}
                label={yTitle ? { value: yTitle, angle: -90, position: "insideLeft" } : undefined}
              />
              <Tooltip {...(tooltipCfg as object)} />
              {showLegend && <Legend {...(legendCfg as object)} />}
              {seriesDefs.map((serie) => {
                const style = styleBySeries.get(serie.name) || styleBySeries.get(serie.dataKey) || {};
                const stroke = style.stroke || serie.stroke;
                const fill = style.fill || style.stroke || serie.stroke;
                return (
                  <Area
                    key={`${comp.id}-${serie.dataKey}`}
                    type="monotone"
                    dataKey={serie.dataKey}
                    stroke={stroke}
                    fill={fill}
                    fillOpacity={0.2}
                    name={serie.name}
                  />
                );
              })}
            </AreaChart>
          );
        }

        if (chartType === "scatter") {
          return (
            <ScatterChart data={data as Record<string, unknown>[]}>
              {showGrid && <CartesianGrid stroke="var(--chart-grid-color)" strokeDasharray="3 3" />}
              <XAxis dataKey={xKey} stroke="var(--chart-text-color)" />
              <YAxis
                stroke="var(--chart-text-color)"
                domain={[yMin !== undefined ? yMin : "auto", yMax !== undefined ? yMax : "auto"]}
                label={yTitle ? { value: yTitle, angle: -90, position: "insideLeft" } : undefined}
              />
              <Tooltip {...(tooltipCfg as object)} />
              {showLegend && <Legend {...(legendCfg as object)} />}
              {seriesDefs.map((serie) => (
                <Scatter
                  key={`${comp.id}-${serie.dataKey}`}
                  dataKey={serie.dataKey}
                  fill={
                    styleBySeries.get(serie.name)?.fill ||
                    styleBySeries.get(serie.name)?.stroke ||
                    styleBySeries.get(serie.dataKey)?.fill ||
                    styleBySeries.get(serie.dataKey)?.stroke ||
                    serie.stroke
                  }
                  name={serie.name}
                />
              ))}
            </ScatterChart>
          );
        }

        if (chartType === "pie") {
          const pieRows = (data as Record<string, unknown>[]) || [];
          return (
            <PieChart>
              <Tooltip {...(tooltipCfg as object)} />
              {showLegend && <Legend {...(legendCfg as object)} />}
              <Pie
                data={pieRows}
                dataKey={pieDataKey}
                nameKey={xKey}
                cx="50%"
                cy="50%"
                outerRadius={80}
                label
              >
                {pieRows.map((_, index) => (
                  <Cell
                    key={`cell-${comp.id}-${index}`}
                    fill={
                      styleBySeries.get(seriesDefs[index % Math.max(1, seriesDefs.length)]?.name || "")
                        ?.fill ||
                      styleBySeries.get(
                        seriesDefs[index % Math.max(1, seriesDefs.length)]?.dataKey || ""
                      )?.fill ||
                      seriesDefs[index % Math.max(1, seriesDefs.length)]?.stroke ||
                      "#38bdf8"
                    }
                  />
                ))}
              </Pie>
            </PieChart>
          );
        }

        return (
          <LineChart data={data as Record<string, unknown>[]}>
            {showGrid && <CartesianGrid stroke="var(--chart-grid-color)" strokeDasharray="3 3" />}
            <XAxis dataKey={xKey} stroke="var(--chart-text-color)" />
            <YAxis
              stroke="var(--chart-text-color)"
              domain={[
                yMin !== undefined ? yMin : "auto",
                yMax !== undefined ? yMax : "auto",
              ]}
              label={yTitle ? { value: yTitle, angle: -90, position: "insideLeft" } : undefined}
            />
            <Tooltip {...(tooltipCfg as object)} />
            {showLegend && <Legend {...(legendCfg as object)} />}
            {seriesDefs.map((serie) => (
              <Line
                key={`${comp.id}-${serie.dataKey}`}
                type="monotone"
                dataKey={serie.dataKey}
                stroke={(styleBySeries.get(serie.name) || styleBySeries.get(serie.dataKey) || {}).stroke || serie.stroke}
                strokeWidth={2}
                dot={
                  ((styleBySeries.get(serie.name) || styleBySeries.get(serie.dataKey) || {}).dotFill ||
                    (styleBySeries.get(serie.name) || styleBySeries.get(serie.dataKey) || {}).dotStroke)
                    ? {
                      r: 3,
                      fill:
                        (styleBySeries.get(serie.name) || styleBySeries.get(serie.dataKey) || {})
                          .dotFill ||
                        serie.stroke,
                      stroke:
                        (styleBySeries.get(serie.name) || styleBySeries.get(serie.dataKey) || {})
                          .dotStroke ||
                        serie.stroke,
                      strokeWidth: 1,
                    }
                    : false
                }
                name={serie.name}
              />
            ))}
          </LineChart>
        );
      };
      return (
        <div
          key={comp.id}
          className="w-full rounded-2xl border border-variant bg-surface-overlay p-3"

          data-testid={`component-chart-${comp.id}`}
        >
          <ResponsiveContainer width={isResponsive ? "100%" : "99%"} height="100%">
            {renderChartBody()}
          </ResponsiveContainer>
        </div>
      );
    }

    if (comp.type === "badge") {
      const label = (props.label as string) || String(boundValue || comp.label || "Badge");
      const conditionalRules = toConditionalStyleRules(props.conditional_styles);
      const badgeStyle: React.CSSProperties = {};
      let badgeVariant = String(props.variant || "default");
      for (const rule of conditionalRules) {
        if (rule.field && rule.field !== "value" && rule.field !== "label") continue;
        if (!evaluateConditionalRule(label, rule.operator, rule.value)) continue;
        if (rule.variant) badgeVariant = rule.variant;
        if (rule.color) badgeStyle.color = rule.color;
        if (rule.bg_color) badgeStyle.backgroundColor = rule.bg_color;
        if (rule.border_color) badgeStyle.borderColor = rule.border_color;
        break;
      }
      return (
        <span
          key={comp.id}
          className={`inline-flex rounded-full border px-3 py-1 text-[10px] uppercase tracking-wider ${badgeVariantClass(
            badgeVariant
          )}`}
          style={badgeStyle}
          data-testid={`component-badge-${comp.id}`}
        >
          {label}
        </span>
      );
    }

    if (comp.type === "tabs") {
      const tabs = (props.tabs as unknown[]) || [];
      const activeIndex = activeTabs[comp.id] ?? (props.activeIndex as number) ?? 0;
      const activeTab = tabs[activeIndex] as Record<string, unknown> | undefined;
      return (
        <div key={comp.id} className="rounded-2xl border border-variant bg-surface-overlay p-4" data-testid={`component-tabs-${comp.id}`}>
          <div className="flex gap-2">
            {tabs.map((tab: unknown, index: number) => {
              const tabItem = tab as Record<string, unknown>;
              return (
                <button
                  key={`${comp.id}-tab-${index}`}
                  type="button"
                  className={`rounded-full px-3 py-1 text-xs uppercase tracking-wider ${index === activeIndex ? "bg-sky-600 text-white" : "border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300"
                    }`}
                  onClick={() => setActiveTabs((prev) => ({ ...prev, [comp.id]: index }))}
                >
                  {(tabItem.label as string) || `Tab ${index + 1}`}
                </button>
              );
            })}
          </div>
          <div className="mt-4 space-y-3">
            {activeTab?.components ? (activeTab.components as Component[]).map((child: Component) => renderComponent(child)) : null}
          </div>
        </div>
      );
    }

    if (comp.type === "accordion") {
      const items = (props.items as unknown[]) || [];
      const allowMultiple = props.allow_multiple === true;
      const active = activeAccordions[comp.id] || [0];
      return (
        <div
          key={comp.id}
          className="rounded-2xl border border-variant bg-surface-overlay p-3 space-y-2"
          data-testid={`component-accordion-${comp.id}`}
        >
          {items.map((rawItem, index) => {
            const item = (rawItem || {}) as Record<string, unknown>;
            const expanded = active.includes(index);
            const title = String(item.title || `Section ${index + 1}`);
            const children = ((item.components as Component[]) || []);
            return (
              <div key={`${comp.id}-acc-${index}`} className="rounded-lg border border-variant overflow-hidden">
                <button
                  type="button"
                  className="flex w-full items-center justify-between bg-surface-base px-3 py-2 text-left text-xs text-foreground"
                  onClick={() => {
                    setActiveAccordions((prev) => {
                      const current = prev[comp.id] || [0];
                      if (allowMultiple) {
                        const next = current.includes(index)
                          ? current.filter((i) => i !== index)
                          : [...current, index];
                        return { ...prev, [comp.id]: next };
                      }
                      return { ...prev, [comp.id]: current.includes(index) ? [] : [index] };
                    });
                  }}
                >
                  <span>{title}</span>
                  <span className="text-muted-foreground">{expanded ? "−" : "+"}</span>
                </button>
                {expanded && <div className="space-y-3 p-3">{children.map((child) => renderComponent(child))}</div>}
              </div>
            );
          })}
        </div>
      );
    }

    if (comp.type === "modal") {
      const isOpen = props.open as boolean | undefined;
      if (!isOpen) return null;
      return (
        <div key={comp.id} className="fixed inset-0 z-50 flex items-center justify-center bg-surface-base/70" data-testid={`component-modal-${comp.id}`}>
          <div className="w-full max-w-xl rounded-2xl border border-variant bg-surface-base p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">{(props.title as string) || comp.label}</h3>
              <button
                type="button"
                className="text-xs uppercase tracking-wider text-slate-500 dark:text-slate-400"
                onClick={() => executeActions(comp.actions as UIActionPayload[])}
              >
                Close
              </button>
            </div>
            <div className="mt-4 space-y-3">
              {props.components ? (props.components as Component[]).map((child: Component) => renderComponent(child)) : null}
            </div>
          </div>
        </div>
      );
    }

    if (comp.type === "keyvalue") {
      const items = (props.items as unknown[]) || (boundValue as unknown[]) || [];
      return (
        <div key={comp.id} className="rounded-2xl border border-variant bg-surface-overlay p-4 text-xs" data-testid={`component-keyvalue-${comp.id}`}>
          {items.map((item: unknown, index: number) => {
            const kvItem = item as Record<string, unknown>;
            return (
              <div key={`${comp.id}-kv-${index}`} className="flex items-center justify-between border-b border-variant py-1 last:border-b-0">
                <span className="text-muted-foreground">{kvItem.key as string}</span>
                <span className="text-foreground">{kvItem.value as string}</span>
              </div>
            );
          })}
        </div>
      );
    }

    if (comp.type === "divider") {
      const orientation = (props.orientation as string) || "horizontal";
      return (
        <div key={comp.id} className={orientation === "vertical" ? "h-full w-px bg-[var(--surface-elevated)]" : "h-px w-full bg-[var(--surface-elevated)]"} data-testid={`component-divider-${comp.id}`} />
      );
    }

    if (comp.type === "row") {
      const gap = (props.gap as number) ?? 4;
      const align = (props.align as string) || "stretch";
      const justify = (props.justify as string) || "start";
      const children = (props.components as Component[]) || [];
      const alignClass: Record<string, string> = {
        start: "items-start",
        center: "items-center",
        end: "items-end",
        stretch: "items-stretch",
      };
      const justifyClass: Record<string, string> = {
        start: "justify-start",
        center: "justify-center",
        end: "justify-end",
        between: "justify-between",
        around: "justify-around",
      };
      return (
        <div
          key={comp.id}
          className={`flex flex-row ${alignClass[align] || "items-stretch"} ${justifyClass[justify] || "justify-start"}`}
          style={{gap: `${gap * 4}px`}}
          data-testid={`component-row-${comp.id}`}
        >
          {children.map((child) => (
            <div key={child.id} className="flex-1">
              {renderComponent(child)}
            </div>
          ))}
        </div>
      );
    }

    if (comp.type === "column") {
      const gap = (props.gap as number) ?? 4;
      const align = (props.align as string) || "stretch";
      const children = (props.components as Component[]) || [];
      const alignClass: Record<string, string> = {
        start: "items-start",
        center: "items-center",
        end: "items-end",
        stretch: "items-stretch",
      };
      return (
        <div
          key={comp.id}
          className={`flex flex-col ${alignClass[align] || "items-stretch"}`}
          style={{gap: `${gap * 4}px`}}
          data-testid={`component-column-${comp.id}`}
        >
          {children.map((child) => renderComponent(child))}
        </div>
      );
    }

    return (
      <div key={comp.id} className="text-xs text-muted-foreground">
        Unsupported component: {comp.type}
      </div>
    );
  };

  const renderByLayout = () => {
    const layout = screenSchema.layout;
    const components = screenSchema.components;


    // Determine layout type
    const layoutType = layout?.type || "stack";

    // Handle dashboard layout (absolute grid positioning)
    if (layoutType === "dashboard") {
      const COLS = 12;
      const ROW_HEIGHT = 60;

      return (
        <div className="relative min-h-[600px]" data-testid="layout-dashboard">
          {components.map((comp) => {
            const compLayout = (comp.props?.layout as { x: number; y: number; w: number; h: number }) || { x: 0, y: 0, w: 4, h: 2 };

            // Calculate percentage-based positioning for responsiveness
            const leftPercent = (compLayout.x / COLS) * 100;
            const widthPercent = (compLayout.w / COLS) * 100;
            const topPx = compLayout.y * ROW_HEIGHT;
            const heightPx = compLayout.h * ROW_HEIGHT;

            return (
              <div
                key={comp.id}
                className="absolute"
                style={{left: `${leftPercent}%`, width: `${widthPercent}%`, top: `${topPx}px`, height: `${heightPx}px`}}
                data-testid={`dashboard-item-${comp.id}`}
              >
                <div className="w-full h-full p-2">
                  {renderComponent(comp)}
                </div>
              </div>
            );
          })}
        </div>
      );
    }

    // Handle grid layout
    if (layoutType === "grid") {
      const cols = (layout?.cols as number) || 2;
      const gap = (layout?.gap as number) || 4;
      return (
        <div className={`grid grid-cols-${cols} gap-${gap}`} data-testid="layout-grid">
          {components.map((comp) => (
            <div key={comp.id} data-testid={`grid-item-${comp.id}`}>
              {renderComponent(comp)}
            </div>
          ))}
        </div>
      );
    }

    // Handle stack (vertical/horizontal) layout
    if (layoutType === "stack" || layoutType === "form") {
      const direction = (layout?.direction as string) || "vertical";
      const gap = (layout?.gap as number) || 4;
      const isVertical = direction === "vertical";
      const containerClass = isVertical
        ? `space-y-${gap}`
        : `flex gap-${gap} flex-row`;

      return (
        <div className={containerClass} data-testid={`layout-stack-${direction}`}>
          {components.map((comp) => (
            <React.Fragment key={comp.id}>{renderComponent(comp)}</React.Fragment>
          ))}
        </div>
      );
    }

    // Handle list layout
    if (layoutType === "list") {
      const gap = (layout?.gap as number) || 2;
      return (
        <div className={`space-y-${gap}`} data-testid="layout-list">
          {components.map((comp) => (
            <div key={comp.id} className="border-b border-variant pb-3 last:border-b-0" data-testid={`list-item-${comp.id}`}>
              {renderComponent(comp)}
            </div>
          ))}
        </div>
      );
    }

    // Handle modal layout
    if (layoutType === "modal") {
      return (
        <div data-testid="layout-modal" className="fixed inset-0 z-50 flex items-center justify-center bg-surface-base/70">
          <div className="w-full max-w-xl rounded-2xl border border-variant bg-surface-base p-5">
            <div className="space-y-4">
              {components.map((comp) => (
                <React.Fragment key={comp.id}>{renderComponent(comp)}</React.Fragment>
              ))}
            </div>
          </div>
        </div>
      );
    }

    // Fallback to default stack
    return (
      <div className="space-y-4" data-testid="layout-default">
        {components.map((comp) => (
          <React.Fragment key={comp.id}>{renderComponent(comp)}</React.Fragment>
        ))}
      </div>
    );
  };

  const hideDebugPanels = screenSchema.metadata?.tags?.hide_debug_panels === "true" || (screenSchema.metadata as any)?.hide_debug_panels === true;

  return (
    <UIScreenErrorBoundary>
      <div
        data-testid={`screen-renderer-${screenId}`}
        className={isFullScreen ? "fixed inset-0 z-50 overflow-auto bg-[var(--surface-base)] p-6 animate-in fade-in zoom-in-95 duration-300" : "relative"}
        style={isFullScreen ? { ...scopedThemeVars, backgroundColor: "var(--background)" } : scopedThemeVars}
      >
        {/* Fullscreen Toggle */}
        <div className="absolute right-4 top-4 z-10 flex gap-2">
          <button
            onClick={() => setIsFullScreen(!isFullScreen)}
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-variant bg-surface-base text-foreground-secondary/80 hover:bg-surface-elevated hover:text-foreground"
            title={isFullScreen ? "Exit Fullscreen" : "Enter Fullscreen"}
          >
            {isFullScreen ? (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" /></svg>
            ) : (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" /></svg>
            )}
          </button>
        </div>

        {!hideDebugPanels && autoRefreshConfigs.length > 0 && (
          <div
            className="mb-3 rounded-xl border border-variant bg-surface-overlay p-3 text-xs text-foreground-secondary/80"
            data-testid="auto-refresh-panel"
          >
            <p className="mb-2 uppercase tracking-wider text-slate-500 dark:text-slate-400">Auto Refresh</p>
            <div className="space-y-2">
              {autoRefreshConfigs.map((config) => {
                const status = autoRefreshStatus[config.key];
                return (
                  <div key={config.key} className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-foreground">
                        {config.componentLabel} · {config.action.handler}
                      </p>
                      <p className="text-muted-foreground">
                        {status?.stopped
                          ? "stopped"
                          : status?.paused
                            ? "paused"
                            : `every ${Math.round(config.intervalMs / 1000)}s`}
                        {status?.failures ? ` · failures ${status.failures}` : ""}
                        {status?.lastSuccessAt
                          ? ` · last ok ${new Date(status.lastSuccessAt).toLocaleTimeString()}`
                          : ""}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="rounded border border-variant px-2 py-1 text-[10px] uppercase tracking-wider text-foreground"
                      onClick={() => toggleAutoRefreshPaused(config.key)}
                      disabled={!!status?.stopped}
                    >
                      {status?.paused ? "Resume" : "Pause"}
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        {!hideDebugPanels && actionLogs.length > 0 && (
          <div
            className="mb-3 rounded-xl border border-variant bg-surface-overlay p-3 text-xs text-foreground-secondary/80"
            data-testid="action-log-panel"
          >
            <div className="mb-2 flex items-center justify-between">
              <p className="uppercase tracking-wider text-slate-500 dark:text-slate-400">Action Log</p>
              <button
                type="button"
                className="rounded border border-variant px-2 py-1 text-[10px] uppercase tracking-wider"
                onClick={() => setActionLogs([])}
              >
                Clear
              </button>
            </div>
            <div className="max-h-48 space-y-1 overflow-y-auto">
              {actionLogs.map((log) => (
                <div key={log.id} className="flex items-center justify-between gap-3">
                  <p className="truncate text-foreground">
                    {log.handler} · {log.source} · attempt {log.attempt + 1}
                  </p>
                  <p
                    className={
                      log.status === "ok" ? "text-emerald-300" : "text-rose-300"
                    }
                  >
                    {log.status} · {log.durationMs}ms
                    {log.error ? ` · ${log.error}` : ""}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}
        {/* Stream connection status */}
        {Object.keys(streamStates).length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {Object.entries(streamStates).map(([id, ss]) => (
              <span
                key={id}
                className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-[10px] border-variant bg-surface-overlay text-muted-foreground ${ss.status === "connected"
                  ? "bg-emerald-950/50 text-emerald-300 border border-emerald-800/50"
                  : ss.status === "connecting"
                    ? "bg-sky-950/50 text-sky-300 border border-sky-800/50"
                    : ss.status === "error"
                      ? "bg-rose-950/50 text-rose-300 border border-rose-800/50"
                      : ""
                  }`}
              >
                <span
                  className={`inline-block w-1.5 h-1.5 rounded-full bg-surface-base ${ss.status === "connected"
                    ? "bg-emerald-400"
                    : ss.status === "connecting"
                      ? "bg-sky-400 animate-pulse"
                      : ss.status === "error"
                        ? "bg-rose-400"
                        : ""
                    }`}
                />
                {id.replace("stream_", "")}
              </span>
            ))}
          </div>
        )}
        {renderByLayout()}
      </div>
    </UIScreenErrorBoundary>
  );
}
