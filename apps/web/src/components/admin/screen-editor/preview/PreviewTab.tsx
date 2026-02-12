"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import UIScreenRenderer from "@/components/answer/UIScreenRenderer";
import type { UIScreenBlock } from "@/components/answer/BlockRenderer";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type PreviewViewport = "desktop" | "tablet" | "mobile";

const VIEWPORT_WIDTH: Record<PreviewViewport, string> = {
  desktop: "100%",
  tablet: "820px",
  mobile: "390px",
};

function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function PreviewTab() {
  const editorState = useEditorState();
  const screen = editorState.screen;
  const [paramsText, setParamsText] = useState('{\n  "context": {}\n}');
  const [bindingsText, setBindingsText] = useState("{}");
  const [parseError, setParseError] = useState<string | null>(null);
  const [viewport, setViewport] = useState<PreviewViewport>("desktop");
  const [selectedActionId, setSelectedActionId] = useState<string>("");
  const [actionPayloadText, setActionPayloadText] = useState("{}");
  const [actionRunError, setActionRunError] = useState<string | null>(null);
  const [actionRunResult, setActionRunResult] = useState<string>("");
  const [isRunningAction, setIsRunningAction] = useState(false);
  const [autoRunEnabled, setAutoRunEnabled] = useState(false);
  const [autoRunMs, setAutoRunMs] = useState(15000);
  const [lastAutoRunAt, setLastAutoRunAt] = useState<number | null>(null);
  const [previewOverrides, setPreviewOverrides] = useState<{
    params: Record<string, unknown>;
    bindings: Record<string, string>;
  }>({
    params: { context: {} },
    bindings: {},
  });

  // Generate a key based on screen content to force re-render when screen changes
  const screenKey = useMemo(() => {
    if (!screen) return "empty";
    return JSON.stringify({
      screen,
      params: previewOverrides.params,
      bindings: previewOverrides.bindings,
    });
  }, [screen, previewOverrides.bindings, previewOverrides.params]);

  const previewBlock = useMemo(() => {
    if (!screen) return null;
    const block: UIScreenBlock = {
      type: "ui_screen",
      screen_id: screen.screen_id,
      params: previewOverrides.params,
      bindings: previewOverrides.bindings,
    };
    return block;
  }, [previewOverrides.bindings, previewOverrides.params, screen]);

  const actionOptions = useMemo(() => screen?.actions || [], [screen]);

  useEffect(() => {
    if (!selectedActionId && actionOptions.length > 0) {
      setSelectedActionId(actionOptions[0].id);
    }
  }, [actionOptions, selectedActionId]);

  const runSelectedAction = useCallback(async (source: "manual" | "auto" = "manual") => {
    if (!selectedActionId) return;
    let payload: Record<string, unknown> = {};
    try {
      payload = JSON.parse(actionPayloadText) as Record<string, unknown>;
      if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
        throw new Error("Action payload must be a JSON object");
      }
    } catch (error) {
      setActionRunError(error instanceof Error ? error.message : "Invalid action payload JSON");
      return;
    }
    setIsRunningAction(true);
    try {
      const result = await editorState.testAction(selectedActionId, payload);
      setActionRunResult(prettyJson(result));
      setActionRunError(null);
      if (source === "auto") {
        setLastAutoRunAt(Date.now());
      }
    } catch (error) {
      setActionRunError(error instanceof Error ? error.message : "Failed to run action");
    } finally {
      setIsRunningAction(false);
    }
  }, [actionPayloadText, editorState, selectedActionId]);

  useEffect(() => {
    if (!autoRunEnabled || !selectedActionId) return;
    const safeInterval = Number.isFinite(autoRunMs) && autoRunMs >= 1000 ? autoRunMs : 1000;
    const timer = window.setInterval(() => {
      void runSelectedAction("auto");
    }, safeInterval);
    return () => window.clearInterval(timer);
  }, [autoRunEnabled, autoRunMs, runSelectedAction, selectedActionId]);

  const applyOverrides = () => {
    try {
      const parsedParams = JSON.parse(paramsText) as Record<string, unknown>;
      const parsedBindings = JSON.parse(bindingsText) as Record<string, string>;
      if (
        !parsedParams ||
        typeof parsedParams !== "object" ||
        Array.isArray(parsedParams)
      ) {
        throw new Error("params must be a JSON object");
      }
      if (
        !parsedBindings ||
        typeof parsedBindings !== "object" ||
        Array.isArray(parsedBindings)
      ) {
        throw new Error("bindings must be a JSON object");
      }
      setPreviewOverrides({
        params: parsedParams,
        bindings: parsedBindings,
      });
      setParseError(null);
    } catch (error) {
      setParseError(error instanceof Error ? error.message : "Failed to parse JSON");
    }
  };

  if (!screen) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="" style={{ color: "var(--muted-foreground)"  }}>Loading preview...</p>
      </div>
    );
  }

  return (
    <div
      className="h-full overflow-auto rounded-lg border p-6" style={{ backgroundColor: "var(--surface-base)", borderColor: "var(--border)"  }}
      data-testid="preview-renderer"
    >
      <div className="mb-6 rounded-lg border p-4 space-y-3" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)"  }}>
        <p className="text-sm uppercase tracking-[0.25em]" style={{ color: "var(--muted-foreground)"  }}>Preview Data Overrides</p>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-2">
          <div className="lg:col-span-1">
            <p className="mb-1 text-xs" style={{ color: "var(--foreground-secondary)"  }}>Viewport</p>
            <Select value={viewport} onValueChange={(val) => setViewport(val as PreviewViewport)}>
              <SelectTrigger className="h-8 text-xs" style={{ backgroundColor: "var(--surface-base)", borderColor: "var(--border)"  }}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="desktop">Desktop</SelectItem>
                <SelectItem value="tablet">Tablet</SelectItem>
                <SelectItem value="mobile">Mobile</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div>
            <p className="mb-1 text-xs" style={{ color: "var(--foreground-secondary)"  }}>params (JSON)</p>
            <Textarea
              value={paramsText}
              onChange={(e) => setParamsText(e.target.value)}
              className="min-h-28 font-mono text-xs" style={{ backgroundColor: "var(--surface-base)", borderColor: "var(--border)"  }}
            />
          </div>
          <div>
            <p className="mb-1 text-xs" style={{ color: "var(--foreground-secondary)"  }}>bindings override (JSON)</p>
            <Textarea
              value={bindingsText}
              onChange={(e) => setBindingsText(e.target.value)}
              className="min-h-28 font-mono text-xs" style={{ backgroundColor: "var(--surface-base)", borderColor: "var(--border)"  }}
            />
          </div>
        </div>
        {parseError && (
          <p className="text-xs text-rose-300">{parseError}</p>
        )}
        <div className="flex justify-end">
          <Button
            size="sm"
            variant="secondary"
            className="text-xs"
            onClick={applyOverrides}
          >
            Apply Preview Data
          </Button>
        </div>
      </div>

      <div className="mb-6 rounded-lg border p-4 space-y-3" style={{ backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)"  }}>
        <p className="text-sm uppercase tracking-[0.25em]" style={{ color: "var(--muted-foreground)"  }}>Action Runner (Realtime Binding)</p>
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-2">
          <div className="lg:col-span-2">
            <p className="mb-1 text-xs" style={{ color: "var(--foreground-secondary)"  }}>Action</p>
            <Select value={selectedActionId} onValueChange={setSelectedActionId}>
              <SelectTrigger className="h-8 text-xs" style={{ backgroundColor: "var(--surface-base)", borderColor: "var(--border)"  }}>
                <SelectValue placeholder="Select action" />
              </SelectTrigger>
              <SelectContent>
                {actionOptions.map((action) => (
                  <SelectItem key={action.id} value={action.id}>
                    {(action.label || action.id) + " · " + (action.handler || "(unset)")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <p className="mb-1 text-xs" style={{ color: "var(--foreground-secondary)"  }}>Auto-run interval(ms)</p>
            <Input
              type="number"
              min={1000}
              step={500}
              value={autoRunMs}
              onChange={(e) => setAutoRunMs(Number(e.target.value || 1000))}
              className="h-8 text-xs" style={{ backgroundColor: "var(--surface-base)", borderColor: "var(--border)"  }}
            />
          </div>
          <div className="flex items-end gap-2">
            <Button
              type="button"
              size="sm"
              variant={autoRunEnabled ? "destructive" : "secondary"}
              className="h-8 text-xs"
              onClick={() => setAutoRunEnabled((prev) => !prev)}
              disabled={!selectedActionId}
            >
              {autoRunEnabled ? "Stop Auto-run" : "Start Auto-run"}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              className="h-8 text-xs"
              onClick={() => void runSelectedAction("manual")}
              disabled={!selectedActionId || isRunningAction}
            >
              {isRunningAction ? "Running..." : "Run Once"}
            </Button>
          </div>
        </div>
        <div>
          <p className="mb-1 text-xs" style={{ color: "var(--foreground-secondary)"  }}>Action payload (JSON)</p>
          <Textarea
            value={actionPayloadText}
            onChange={(e) => setActionPayloadText(e.target.value)}
            className="min-h-24 font-mono text-xs" style={{ backgroundColor: "var(--surface-base)", borderColor: "var(--border)"  }}
          />
        </div>
        {lastAutoRunAt && (
          <p className="text-[11px]" style={{ color: "var(--muted-foreground)"  }}>
            Last auto-run: {new Date(lastAutoRunAt).toLocaleTimeString()}
          </p>
        )}
        {actionRunError && <p className="text-xs text-rose-300">{actionRunError}</p>}
        {actionRunResult && (
          <div>
            <p className="mb-1 text-xs" style={{ color: "var(--foreground-secondary)"  }}>Latest action result</p>
            <Textarea
              value={actionRunResult}
              readOnly
              className="min-h-24 font-mono text-xs" style={{ backgroundColor: "var(--surface-base)", borderColor: "var(--border)"  }}
            />
          </div>
        )}
      </div>

      {/* Show validation errors if any */}
      {editorState.validationErrors.some(e => e.severity === "error") && (
        <div className="mb-6 rounded-lg border border-red-800 bg-red-950/50 p-4">
          <p className="text-sm font-semibold text-red-300 mb-2">
            Preview has validation errors
          </p>
          <div className="space-y-1">
            {editorState.validationErrors
              .filter(e => e.severity === "error")
              .slice(0, 3)
              .map((err, idx) => (
                <p key={idx} className="text-xs text-red-400">
                  {err.path}: {err.message}
                </p>
              ))}
          </div>
        </div>
      )}

      {/* Render screen using UIScreenRenderer - key forces re-render on screen changes */}
      <div className="mx-auto transition-all" style={{ width: VIEWPORT_WIDTH[viewport], maxWidth: "100%" }}>
        <UIScreenRenderer key={screenKey} block={previewBlock!} schemaOverride={screen} />
      </div>
    </div>
  );
}
