"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import ScreenEditorCopilotPanel from "./CopilotPanel";
import ScreenEditorHeader from "./ScreenEditorHeader";
import ScreenEditorTabs from "./ScreenEditorTabs";
import ScreenEditorErrors from "./common/ScreenEditorErrors";
import Toast from "@/components/admin/Toast";
import PublishGateModal from "./publish/PublishGateModal";

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

  const schemaSummary = useMemo(() => {
    const activeScreen = editorState.screen ?? screen;
    if (!activeScreen) {
      return "No screen loaded";
    }
    const layoutType = activeScreen.layout?.type || "unknown";
    const componentCount = Array.isArray(activeScreen.components) ? activeScreen.components.length : 0;
    return `${layoutType} · ${componentCount} component${componentCount === 1 ? "" : "s"}`;
     
  }, [editorState.screen, screen]);

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
            isSaving={isSaving}
            isPublishing={isPublishing}
            justPublished={justPublished}
            screenId={screen?.id}
            assetId={assetId}
            screenVersion={screen?.version ?? null}
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

        <ScreenEditorCopilotPanel
          screenId={screen?.screen_id ?? assetId}
          stage={status}
          schemaSummary={schemaSummary}
          selectedComponentId={selectedComponentId}
        />
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
