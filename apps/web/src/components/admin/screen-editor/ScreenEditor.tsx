"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useEditorState } from "@/lib/ui-screen/editor-state";
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
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) {
      console.warn("[ScreenEditor] No access token found, redirecting to login");
      router.push("/login");
      return;
    }
    setAuthCheckDone(true);
  }, [router]);

  useEffect(() => {
    if (authCheckDone) {
      loadScreen();
    }
  }, [assetId, authCheckDone]);

  const loadScreen = async () => {
    try {
      setLoading(true);
      setError(null);
      editorState.setAssetId(assetId);
      await editorState.loadScreen(assetId);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load screen";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

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
      />

      {/* Errors */}
      {editorState.validationErrors.length > 0 && (
        <ScreenEditorErrors errors={editorState.validationErrors} />
      )}

      {/* Tabs */}
      <div className="flex-1 overflow-hidden">
        <ScreenEditorTabs assetId={assetId} />
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
