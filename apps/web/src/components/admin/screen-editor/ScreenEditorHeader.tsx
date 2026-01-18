"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import Link from "next/link";

interface ScreenEditorHeaderProps {
  status: "draft" | "published";
  isDirty: boolean;
  canPublish: boolean;
  canRollback: boolean;
  onSaveDraft: () => void;
  onPublish: () => void;
  onRollback: () => void;
  isSaving: boolean;
  isPublishing: boolean;
}

export default function ScreenEditorHeader({
  status,
  isDirty,
  canPublish,
  canRollback,
  onSaveDraft,
  onPublish,
  onRollback,
  isSaving,
  isPublishing,
}: ScreenEditorHeaderProps) {
  return (
    <div className="border-b border-slate-800 bg-slate-900/50 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/admin/screens"
            className="text-sky-400 hover:text-sky-300 transition-colors"
          >
            ← Back to Screens
          </Link>

          <div className="flex items-center gap-3">
            <span
              className={`inline-flex px-3 py-1 rounded text-xs font-bold uppercase tracking-wider ${
                status === "published"
                  ? "bg-emerald-950/50 text-emerald-300 border border-emerald-800/50"
                  : "bg-slate-800/50 text-slate-400 border border-slate-700/50"
              }`}
              data-testid="status-badge"
            >
              {status}
            </span>

            {isDirty && (
              <span className="text-yellow-500 text-xs font-medium">
                Unsaved changes
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {status === "draft" && (
            <>
              <Button
                onClick={onSaveDraft}
                disabled={isSaving || !isDirty}
                variant="outline"
                size="sm"
                data-testid="btn-save-draft"
              >
                {isSaving ? "Saving..." : "Save Draft"}
              </Button>

              <Button
                onClick={onPublish}
                disabled={isPublishing || !canPublish}
                size="sm"
                className="bg-sky-600 hover:bg-sky-700 text-white"
                data-testid="btn-publish-screen"
              >
                {isPublishing ? "Publishing..." : "Publish"}
              </Button>
            </>
          )}

          {status === "published" && (
            <Button
              onClick={onRollback}
              variant="outline"
              size="sm"
              className="text-orange-400 border-orange-700 hover:bg-orange-950/30"
              data-testid="btn-rollback-screen"
            >
              Rollback to Draft
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
