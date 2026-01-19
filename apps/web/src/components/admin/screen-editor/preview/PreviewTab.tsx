"use client";

import React, { useMemo } from "react";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import UIScreenRenderer from "@/components/answer/UIScreenRenderer";

export default function PreviewTab() {
  const editorState = useEditorState();
  const previewBlock = useMemo(() => {
    if (!editorState.screen) return null;
    return {
      type: "ui_screen",
      screen_id: editorState.screen.screen_id,
      params: {},
    };
  }, [editorState.screen?.screen_id]);

  if (!editorState.screen) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-slate-400">Loading preview...</p>
      </div>
    );
  }

  return (
    <div
      className="h-full overflow-auto bg-slate-900 rounded-lg border border-slate-800 p-6"
      data-testid="preview-renderer"
    >
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

      {/* Render screen using UIScreenRenderer */}
      <UIScreenRenderer block={previewBlock!} schemaOverride={editorState.screen} />
    </div>
  );
}
