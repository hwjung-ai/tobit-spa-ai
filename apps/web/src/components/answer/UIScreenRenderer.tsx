"use client";

import React, { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Line,
  LineChart,
  ResponsiveContainer,
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
import { fetchApi } from "@/lib/adminUtils";
import type { UIScreenBlock } from "./BlockRenderer";

interface UIScreenRendererProps {
  block: UIScreenBlock;
  traceId?: string;
  onResult?: (blocks: unknown[]) => void;
  schemaOverride?: ScreenSchemaV1 | null;
}

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

export default function UIScreenRenderer({
  block,
  traceId,
  onResult,
  schemaOverride,
}: UIScreenRendererProps) {
  const [screenSchema, setScreenSchema] = useState<ScreenSchemaV1 | null>(null);
  const [state, setState] = useState<Record<string, unknown>>({});
  const [activeTabs, setActiveTabs] = useState<Record<string, number>>({});
  const screenId = block.screen_id;

  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

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
      context: {},
      trace_id: traceId || null,
    }),
    [state, traceId]
  );

  const handleAction = async (action: { handler: string; payload_template?: Record<string, unknown> }) => {
    setState((prev) => {
      const next = { ...prev };
      setLoading(next, action.handler, true);
      setError(next, action.handler, null);
      return next;
    });

    try {
      const payload = {
        trace_id: traceId || null,
        action_id: action.handler,
        inputs: renderTemplate(action.payload_template || {}, context) as Record<string, unknown>,
        context: {},
        screen_id: screenId,
      };

      const resp = await fetch(`/ops/ui-actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const envelope = await resp.json();
      const data = envelope?.data || {};
      const resultBlocks = data.blocks || [];
      const result = resultBlocks[0] || data;

      setState((prev) => {
        const next = { ...prev };
        applyActionResultToState(next, action.handler, result);
        setLoading(next, action.handler, false);
        setError(next, action.handler, null);
        return next;
      });

      if (resultBlocks.length && onResult) {
        onResult(resultBlocks);
      }
    } catch (err: unknown) {
      setState((prev) => {
        const next = { ...prev };
        setLoading(next, action.handler, false);
        setError(next, action.handler, err instanceof Error ? err.message : String(err));
        return next;
      });
    }
  };

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
      <div className="rounded-xl border border-slate-700 bg-slate-900/40 p-4 text-sm text-slate-300 animate-pulse">
        Loading screen {screenId}...
      </div>
    );
  }

  const renderComponent = (comp: Component) => {
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
      return (
        <div key={comp.id} className="text-sm text-slate-100" data-testid={`component-text-${comp.id}`}>
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
      const action = comp.actions?.[0];
      return (
        <button
          key={comp.id}
          type="button"
          className="rounded-full border border-slate-700 px-4 py-2 text-xs uppercase tracking-[0.2em] text-slate-100 hover:border-slate-500"
          disabled={disabled || isLoadingAction}
          onClick={() => action && handleAction(action)}
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
          className="w-full rounded-xl border border-slate-700 bg-slate-950/50 px-3 py-2 text-sm text-slate-100"
          placeholder={props.placeholder as string}
          type={(props.inputType as string) || "text"}
          value={String(value)}
          onChange={(e) => handleInputChange(comp, e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && comp.actions?.[0]) {
              handleAction(comp.actions[0]);
            }
          }}
          data-testid={`component-input-${comp.id}`}
        />
      );
    }

    if (comp.type === "table") {
      const rows = (props.rows as unknown[]) || (boundValue as unknown[]) || [];
      const columns = (props.columns as string[]) || (Array.isArray(rows[0]) ? Object.keys(rows[0]) : []);
      return (
        <table key={comp.id} className="min-w-full border border-slate-800 text-xs" data-testid={`component-table-${comp.id}`}>
          <thead className="bg-slate-900/80 text-slate-300">
            <tr>
              {columns.map((col) => (
                <th key={col} className="border border-slate-800 px-2 py-1 text-left">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row: unknown, index: number) => (
              <tr key={`${comp.id}-row-${index}`} className="border border-slate-800">
                {columns.map((col) => (
                  <td key={`${comp.id}-${col}-${index}`} className="border border-slate-800 px-2 py-1">
                    {String((row as Record<string, unknown>)?.[col] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      );
    }

    if (comp.type === "chart") {
      const series = (props.series as unknown[]) || [];
      const firstSeries = series[0] as Record<string, unknown> | undefined;
      const data = (firstSeries?.data as unknown[]) || [];
      return (
        <div key={comp.id} className="h-52 w-full rounded-2xl border border-slate-800 bg-slate-900/40 p-3" data-testid={`component-chart-${comp.id}`}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data as Record<string, unknown>[]}>
              <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
              <XAxis dataKey="x" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip />
              <Line type="monotone" dataKey="y" stroke="#38bdf8" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      );
    }

    if (comp.type === "badge") {
      const label = (props.label as string) || String(boundValue || comp.label || "Badge");
      return (
        <span key={comp.id} className="inline-flex rounded-full border border-slate-700 px-3 py-1 text-[10px] uppercase tracking-[0.2em] text-slate-200" data-testid={`component-badge-${comp.id}`}>
          {label}
        </span>
      );
    }

    if (comp.type === "tabs") {
      const tabs = (props.tabs as unknown[]) || [];
      const activeIndex = activeTabs[comp.id] ?? (props.activeIndex as number) ?? 0;
      const activeTab = tabs[activeIndex] as Record<string, unknown> | undefined;
      return (
        <div key={comp.id} className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4" data-testid={`component-tabs-${comp.id}`}>
          <div className="flex gap-2">
            {tabs.map((tab: unknown, index: number) => {
              const tabItem = tab as Record<string, unknown>;
              return (
                <button
                  key={`${comp.id}-tab-${index}`}
                  type="button"
                  className={`rounded-full px-3 py-1 text-[11px] uppercase tracking-[0.2em] ${
                    index === activeIndex ? "bg-slate-200 text-slate-900" : "border border-slate-700 text-slate-200"
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

    if (comp.type === "modal") {
      const isOpen = props.open as boolean | undefined;
      if (!isOpen) return null;
      const action = comp.actions?.[0];
      return (
        <div key={comp.id} className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70" data-testid={`component-modal-${comp.id}`}>
          <div className="w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-900 p-5">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-100">{(props.title as string) || comp.label}</h3>
              <button
                type="button"
                className="text-xs uppercase tracking-[0.2em] text-slate-400"
                onClick={() => action && handleAction(action)}
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
        <div key={comp.id} className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 text-xs" data-testid={`component-keyvalue-${comp.id}`}>
          {items.map((item: unknown, index: number) => {
            const kvItem = item as Record<string, unknown>;
            return (
              <div key={`${comp.id}-kv-${index}`} className="flex items-center justify-between border-b border-slate-800 py-1 last:border-b-0">
                <span className="text-slate-400">{kvItem.key as string}</span>
                <span className="text-slate-100">{kvItem.value as string}</span>
              </div>
            );
          })}
        </div>
      );
    }

    if (comp.type === "divider") {
      const orientation = (props.orientation as string) || "horizontal";
      return (
        <div key={comp.id} className={orientation === "vertical" ? "h-full w-px bg-slate-700" : "h-px w-full bg-slate-700"} data-testid={`component-divider-${comp.id}`} />
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
          style={{ gap: `${gap * 4}px` }}
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
          style={{ gap: `${gap * 4}px` }}
          data-testid={`component-column-${comp.id}`}
        >
          {children.map((child) => renderComponent(child))}
        </div>
      );
    }

    return (
      <div key={comp.id} className="text-xs text-slate-500">
        Unsupported component: {comp.type}
      </div>
    );
  };

  const renderByLayout = () => {
    const layout = screenSchema.layout;
    const components = screenSchema.components;

    // Determine layout type
    const layoutType = layout?.type || "stack";

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
    if (layoutType === "stack" || layoutType === "form" || layoutType === "dashboard") {
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
            <div key={comp.id} className="border-b border-slate-800 pb-3 last:border-b-0" data-testid={`list-item-${comp.id}`}>
              {renderComponent(comp)}
            </div>
          ))}
        </div>
      );
    }

    // Handle modal layout
    if (layoutType === "modal") {
      return (
        <div data-testid="layout-modal" className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70">
          <div className="w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-900 p-5">
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

  return (
    <UIScreenErrorBoundary>
      <div data-testid={`screen-renderer-${screenId}`}>
        {renderByLayout()}
      </div>
    </UIScreenErrorBoundary>
  );
}