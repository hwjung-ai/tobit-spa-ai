"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import BuilderCopilotPanel from "@/components/chat/BuilderCopilotPanel";
import UIScreenRenderer from "@/components/answer/UIScreenRenderer";
import type { UIScreenBlock } from "@/components/answer/BlockRenderer";
import {
  extractJsonCandidates,
  stripCodeFences,
  tryParseJson,
} from "@/lib/copilot/json-utils";
import { recordCopilotMetric } from "@/lib/copilot/metrics";
import ScreenEditorHeader from "./ScreenEditorHeader";
import ScreenEditorTabs from "./ScreenEditorTabs";
import ScreenEditorErrors from "./common/ScreenEditorErrors";
import Toast from "@/components/admin/Toast";
import PublishGateModal from "./publish/PublishGateModal";

const SCREEN_COPILOT_INSTRUCTION = `You are Tobit Screen Schema V1 Copilot.
You must generate JSON Patch (RFC 6902) operations to modify an existing screen.
Return only one JSON payload compatible with contract type=screen_patch.
Prefer minimal patch operations and stable paths.

The screen follows ScreenSchemaV1 with these key paths:
- /title - Screen title (string)
- /layout/type - Layout type: "flex" | "grid" | "tabs"
- /layout/direction - "row" | "column"
- /components/N - Component at index N
- /components/N/type - Component type (text, table, chart, form, button, image, card, stat, markdown, divider, spacer, container, tabs, badge, alert)
- /components/N/props - Component-specific properties
- /components/N/props/label - Display label
- /components/N/props/content - Content text (for text/markdown)
- /components/N/bindings - Data bindings (key: binding expression)

When the user asks to modify the screen, respond with:
{"type":"screen_patch","patch":[{"op":"replace","path":"/name","value":"New Name"}],"notes":"optional"}

Always respond in the same language as the user's message.`;

const ALLOWED_COMPONENT_TYPES = new Set([
  "text", "table", "chart", "form", "button", "image", "card", "stat", "markdown",
  "divider", "spacer", "container", "tabs", "badge", "alert", "row", "column",
  "modal", "list", "accordion",
]);

function validatePatchArray(patchArray: unknown[]): string[] {
  const errors: string[] = [];
  patchArray.forEach((entry, index) => {
    if (!entry || typeof entry !== "object") {
      errors.push(`patch[${index}] must be an object`);
      return;
    }
    const op = (entry as { op?: unknown }).op;
    const path = (entry as { path?: unknown }).path;
    const hasValue = Object.prototype.hasOwnProperty.call(entry, "value");

    if (typeof op !== "string" || !["add", "remove", "replace", "move", "copy", "test"].includes(op)) {
      errors.push(`patch[${index}].op is invalid`);
    }
    if (typeof path !== "string" || !path.startsWith("/")) {
      errors.push(`patch[${index}].path must start with "/"`);
    }
    if ((op === "add" || op === "replace" || op === "test") && !hasValue) {
      errors.push(`patch[${index}].value is required for ${op}`);
    }

    if (typeof path === "string" && path.includes("/components/") && hasValue) {
      const value = (entry as { value?: unknown }).value;
      if (value && typeof value === "object" && "type" in (value as Record<string, unknown>)) {
        const candidate = (value as Record<string, unknown>).type;
        if (typeof candidate === "string" && !ALLOWED_COMPONENT_TYPES.has(candidate)) {
          errors.push(`patch[${index}] has unsupported component type: ${candidate}`);
        }
      }
    }
  });
  return errors;
}

interface ScreenEditorProps {
  assetId: string;
}

export default function ScreenEditor({ assetId }: ScreenEditorProps) {
  const router = useRouter();
  const editorState = useEditorState();
  const screen = useEditorState((state) => state.screen);
  const draftModified = useEditorState((state) => state.draftModified);
  const status = useEditorState((state) => state.status);
  const validationErrors = useEditorState((state) => state.validationErrors);
  const setAssetId = useEditorState((state) => state.setAssetId);
  const loadScreenFromStore = useEditorState((state) => state.loadScreen);
  const saveDraft = useEditorState((state) => state.saveDraft);
  const publish = useEditorState((state) => state.publish);
  const rollback = useEditorState((state) => state.rollback);
  const isSaving = useEditorState((state) => state.isSaving);
  const isPublishing = useEditorState((state) => state.isPublishing);
  const selectedComponentId = useEditorState((state) => state.selectedComponentId);
  const draftConflict = useEditorState((state) => state.draftConflict);
  const clearDraftConflict = useEditorState((state) => state.clearDraftConflict);
  const applyAutoMergedConflict = useEditorState((state) => state.applyAutoMergedConflict);
  const reloadFromServer = useEditorState((state) => state.reloadFromServer);
  const forceSaveDraft = useEditorState((state) => state.forceSaveDraft);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [showPublishGate, setShowPublishGate] = useState(false);
  const [justPublished, setJustPublished] = useState(false);
  const [authCheckDone, setAuthCheckDone] = useState(false);

  // Subscribe to specific state fields for re-renders
  const isDirty = draftModified;
  const canPublish = status === "draft" &&
    validationErrors.filter(e => e.severity === "error").length === 0;

  // Check authentication on mount
  useEffect(() => {
    const enableAuth = process.env.NEXT_PUBLIC_ENABLE_AUTH === "true";
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

    // If auth is disabled, skip token check
    if (!enableAuth) {
      setAuthCheckDone(true);
      return;
    }

    // If auth is enabled, require token
    if (!token) {
      console.warn("[ScreenEditor] No access token found, redirecting to login");
      router.push("/login");
      return;
    }
    setAuthCheckDone(true);
  }, [router]);

  const resolveLoadErrorMessage = (err: unknown) => {
    const statusCode = typeof err === "object" && err !== null ? (err as Record<string, unknown>).statusCode : undefined;
    if (statusCode === 404) {
      return "Screen asset not found or not accessible.";
    }
    if (statusCode === 403) {
      return "You don't have permission to view this screen asset.";
    }
    if (statusCode) {
      return `Unable to load screen asset (status ${statusCode}).`;
    }
    return err instanceof Error ? err.message : "Failed to load screen asset.";
  };

  useEffect(() => {
    if (!authCheckDone) {
      return;
    }

    const run = async () => {
      try {
        setLoading(true);
        setError(null);
        setAssetId(assetId);
        await loadScreenFromStore(assetId);
      } catch (err) {
        setError(resolveLoadErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [authCheckDone, assetId, loadScreenFromStore, setAssetId]);

  const handleSaveDraft = async () => {
    try {
      await saveDraft();
      setToast({ message: "Draft saved successfully", type: "success" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to save draft";
      setToast({ message, type: "error" });
    }
  };

  const handlePublishClick = () => {
    setShowPublishGate(true);
  };

  const handlePublishConfirm = async () => {
    try {
      await publish();
      setJustPublished(true);
      setToast({ message: "Screen published successfully", type: "success" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to publish";
      setToast({ message, type: "error" });
    }
  };

  const handleRollback = async () => {
    if (!confirm("Are you sure you want to rollback to draft?")) return;

    try {
      await rollback();
      setToast({ message: "Screen rolled back to draft", type: "success" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to rollback";
      setToast({ message, type: "error" });
    }
  };

  // AI Copilot: extract JSON Patch from assistant messages and apply
  const handleAssistantMessageComplete = useCallback(
    (text: string) => {
      const candidates = [stripCodeFences(text), text];
      let patchArray: unknown[] | null = null;

      for (const candidate of candidates) {
        const direct = tryParseJson(candidate);
        if (Array.isArray(direct)) {
          patchArray = direct;
          break;
        }
        if (
          direct &&
          typeof direct === "object" &&
          Array.isArray((direct as { patch?: unknown }).patch)
        ) {
          patchArray = (direct as { patch: unknown[] }).patch;
          break;
        }

        for (const extracted of extractJsonCandidates(candidate)) {
          const parsed = tryParseJson(extracted);
          if (Array.isArray(parsed)) {
            patchArray = parsed;
            break;
          }
          if (
            parsed &&
            typeof parsed === "object" &&
            Array.isArray((parsed as { patch?: unknown }).patch)
          ) {
            patchArray = (parsed as { patch: unknown[] }).patch;
            break;
          }
        }

        if (patchArray) break;
      }

      if (!Array.isArray(patchArray) || patchArray.length === 0) {
        recordCopilotMetric("screen-editor", "parse_failure", "patch array not found");
        setToast({
          message: "AI 응답에서 JSON Patch를 찾지 못했습니다. 다시 시도해 주세요.",
          type: "error",
        });
        return;
      }

      const patchErrors = validatePatchArray(patchArray);
      if (patchErrors.length > 0) {
        recordCopilotMetric("screen-editor", "parse_failure", patchErrors.join("; "));
        setToast({
          message: `Patch validation failed: ${patchErrors[0]}`,
          type: "error",
        });
        return;
      }

      editorState.setProposedPatch(JSON.stringify(patchArray));
      editorState.previewPatch();
      recordCopilotMetric("screen-editor", "parse_success");
    },
    [editorState]
  );

  const schemaSummary = useMemo(() => {
    const activeScreen = editorState.screen ?? screen;
    if (!activeScreen) {
      return "No screen loaded";
    }
    const layoutType = activeScreen.layout?.type || "unknown";
    const componentCount = Array.isArray(activeScreen.components) ? activeScreen.components.length : 0;
    return `${layoutType} · ${componentCount} component${componentCount === 1 ? "" : "s"}`;
     
  }, [editorState.screen, screen]);

  const proposedPatchSummary = useMemo(() => {
    if (!editorState.proposedPatch) return [];
    const parsed = tryParseJson(editorState.proposedPatch);
    if (!Array.isArray(parsed)) return [];
    return parsed
      .map((item) => {
        if (!item || typeof item !== "object") return null;
        const op = (item as { op?: string }).op ?? "?";
        const path = (item as { path?: string }).path ?? "?";
        return `${op} ${path}`;
      })
      .filter((line): line is string => Boolean(line));
  }, [editorState.proposedPatch]);

  const livePreviewBlock = useMemo<UIScreenBlock | null>(() => {
    if (!screen?.screen_id) return null;
    return {
      type: "ui_screen",
      screen_id: screen.screen_id,
      params: {},
      bindings: {},
    };
  }, [screen?.screen_id]);

  const copilotBuilderContext = useMemo(
    () => ({
      screen: screen
        ? {
            screen_id: screen.screen_id,
            name: screen.name ?? null,
            layout_type: screen.layout?.type ?? null,
            component_count: Array.isArray(screen.components)
              ? screen.components.length
              : 0,
          }
        : null,
      draft_modified: draftModified,
      selected_component_id: selectedComponentId,
    }),
    [draftModified, screen, selectedComponentId]
  );

  if (!authCheckDone || loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-slate-400">Loading screen editor...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <div className="rounded-lg border border-red-800 bg-red-950/50 p-4 text-red-300">
          <p className="font-semibold">Failed to load editor</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!screen) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-slate-400">No screen data</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100" data-testid="screen-editor">
      <div className="flex flex-1 gap-6 overflow-hidden">
        <div className="flex flex-1 flex-col overflow-hidden">
          {/* Header */}
          <ScreenEditorHeader
            status={status}
            isDirty={isDirty}
            canPublish={canPublish}
            onSaveDraft={handleSaveDraft}
            onPublish={handlePublishClick}
            onRollback={handleRollback}
            onUndo={editorState.undo}
            onRedo={editorState.redo}
            canUndo={editorState.canUndo}
            canRedo={editorState.canRedo}
            isSaving={isSaving}
            isPublishing={isPublishing}
            justPublished={justPublished}
            screenId={screen?.id}
            assetId={assetId}
            screenVersion={screen?.version ?? null}
            screenName={screen?.name}
          />

          {/* Errors */}
          {validationErrors.length > 0 && (
            <ScreenEditorErrors errors={validationErrors} />
          )}
          {draftConflict.hasConflict && (
            <div
              className="mx-6 mt-3 rounded-md border border-amber-700/70 bg-amber-900/30 px-3 py-2 text-xs text-amber-100"
              data-testid="screen-editor-draft-conflict"
            >
              <div className="flex items-center justify-between gap-3">
                <span>
                  {draftConflict.message || "Draft conflict detected."}
                </span>
                <div className="flex gap-2">
                  {draftConflict.autoMergedScreen && (
                    <button
                      type="button"
                      className="rounded border border-sky-500/60 px-2 py-1 text-[10px] uppercase tracking-[0.15em]"
                      onClick={() => {
                        applyAutoMergedConflict();
                        setToast({ message: "Auto-merge applied to draft", type: "success" });
                      }}
                    >
                      Apply Auto-Merge
                    </button>
                  )}
                  <button
                    type="button"
                    className="rounded border border-slate-500/60 px-2 py-1 text-[10px] uppercase tracking-[0.15em]"
                    onClick={() => {
                      void (async () => {
                        try {
                          await reloadFromServer();
                          setToast({ message: "Reloaded latest version", type: "success" });
                        } catch (err) {
                          const message =
                            err instanceof Error ? err.message : "Failed to reload";
                          setToast({ message, type: "error" });
                        }
                      })();
                    }}
                  >
                    Reload Latest
                  </button>
                  <button
                    type="button"
                    className="rounded border border-amber-500/60 px-2 py-1 text-[10px] uppercase tracking-[0.15em]"
                    onClick={() => {
                      void (async () => {
                        try {
                          await forceSaveDraft();
                          setToast({ message: "Draft force-saved", type: "success" });
                        } catch (err) {
                          const message =
                            err instanceof Error ? err.message : "Force save failed";
                          setToast({ message, type: "error" });
                        }
                      })();
                    }}
                  >
                    Force Save
                  </button>
                  <button
                    type="button"
                    className="rounded border border-slate-500/60 px-2 py-1 text-[10px] uppercase tracking-[0.15em]"
                    onClick={() => clearDraftConflict()}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="flex-1 overflow-hidden">
            <ScreenEditorTabs />
          </div>
        </div>

        <div className="w-80 flex-shrink-0 flex flex-col border-l border-slate-800 bg-slate-950">
          <div className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Schema</p>
              <p className="text-[11px] text-slate-300">{schemaSummary}</p>
            </div>
          </div>
          <div className="flex-1 overflow-hidden">
            <BuilderCopilotPanel
              builderSlug="screen-editor"
              instructionPrompt={SCREEN_COPILOT_INSTRUCTION}
              expectedContract="screen_patch"
              builderContext={copilotBuilderContext}
              onAssistantMessageComplete={handleAssistantMessageComplete}
              inputPlaceholder="Describe changes to apply..."
            />
          </div>
          {editorState.proposedPatch && (
            <div className="border-t border-slate-800 px-4 py-3 space-y-2">
              {proposedPatchSummary.length > 0 && (
                <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-2 text-[11px] text-slate-300">
                  <p className="text-[10px] uppercase tracking-[0.15em] text-slate-500">Patch Diff</p>
                  {proposedPatchSummary.map((line) => (
                    <p key={line}>{line}</p>
                  ))}
                </div>
              )}
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    try {
                      editorState.applyProposedPatch();
                      setToast({ message: "Patch applied to draft", type: "success" });
                    } catch (err) {
                      setToast({
                        message: err instanceof Error ? err.message : "Failed to apply patch",
                        type: "error",
                      });
                    }
                  }}
                  className="flex-1 rounded-2xl bg-emerald-600 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-white transition hover:bg-emerald-500"
                >
                  Apply
                </button>
                <button
                  type="button"
                  onClick={() => editorState.discardProposal()}
                  className="flex-1 rounded-2xl border border-slate-700 px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-400 transition hover:border-slate-500"
                >
                  Discard
                </button>
              </div>
            </div>
          )}
          {livePreviewBlock && (
            <div className="border-t border-slate-800 px-4 py-3">
              <p className="mb-2 text-[10px] uppercase tracking-[0.15em] text-slate-500">Live Preview</p>
              <div className="max-h-60 overflow-auto rounded-lg border border-slate-800 bg-slate-900/40 p-2">
                <UIScreenRenderer block={livePreviewBlock} schemaOverride={screen} />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}

      {/* Publish Gate Modal */}
      <PublishGateModal
        open={showPublishGate}
        onOpenChange={setShowPublishGate}
        onConfirm={handlePublishConfirm}
      />
    </div>
  );
}
