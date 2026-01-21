"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [showPublishGate, setShowPublishGate] = useState(false);
  const [justPublished, setJustPublished] = useState(false);
  const [authCheckDone, setAuthCheckDone] = useState(false);

  // Subscribe to specific state fields for re-renders
  const isDirty = editorState.draftModified;
  const canPublish = editorState.status === "draft" &&
    editorState.validationErrors.filter(e => e.severity === "error").length === 0;
  const canRollback = editorState.status === "published";

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

  const loadScreen = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      editorState.setAssetId(assetId);
      await editorState.loadScreen(assetId);
    } catch (err) {
      setError(resolveLoadErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [assetId, editorState]);

  useEffect(() => {
    if (authCheckDone) {
      loadScreen();
    }
  }, [authCheckDone, loadScreen]);

  const handleSaveDraft = async () => {
    try {
      await editorState.saveDraft();
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
      await editorState.publish();
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
      await editorState.rollback();
      setToast({ message: "Screen rolled back to draft", type: "success" });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to rollback";
      setToast({ message, type: "error" });
    }
  };

  const schemaSummary = useMemo(() => {
    const screen = editorState.screen;
    if (!screen) {
      return "No screen loaded";
    }
    const layoutType = screen.layout?.type || "unknown";
    const componentCount = Array.isArray(screen.components) ? screen.components.length : 0;
    return `${layoutType} · ${componentCount} component${componentCount === 1 ? "" : "s"}`;
  }, [editorState.screen]);

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

  if (!editorState.screen) {
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
            status={editorState.status}
            isDirty={isDirty}
            canPublish={canPublish}
            canRollback={canRollback}
            onSaveDraft={handleSaveDraft}
            onPublish={handlePublishClick}
            onRollback={handleRollback}
            isSaving={editorState.isSaving}
            isPublishing={editorState.isPublishing}
            justPublished={justPublished}
            screenId={editorState.screen?.id}
            assetId={assetId}
            screenVersion={editorState.screen?.version ?? null}
          />

          {/* Errors */}
          {editorState.validationErrors.length > 0 && (
            <ScreenEditorErrors errors={editorState.validationErrors} />
          )}

          {/* Tabs */}
          <div className="flex-1 overflow-hidden">
            <ScreenEditorTabs assetId={assetId} />
          </div>
        </div>

        <ScreenEditorCopilotPanel
          screenId={editorState.screen?.screen_id ?? assetId}
          stage={editorState.status}
          schemaSummary={schemaSummary}
          selectedComponentId={editorState.selectedComponentId}
        />
      </div>

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
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
