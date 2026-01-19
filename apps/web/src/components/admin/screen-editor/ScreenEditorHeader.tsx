"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { CheckCircle, ExternalLink } from "lucide-react";

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
  justPublished?: boolean;
  screenId?: string;
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
  justPublished,
  screenId,
}: ScreenEditorHeaderProps) {
  const router = useRouter();

  const handleRunRegression = () => {
    router.push(`/admin/regression?screen_id=${screenId}`);
  };

  const handleViewTraces = () => {
    window.open(`/admin/inspector?screen_id=${screenId}`, "_blank");
  };
  return (
    <>
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
                  className={isSaving || !isDirty ? "cursor-not-allowed" : "cursor-pointer"}
                  data-testid="btn-save-draft"
                >
                  {isSaving ? "Saving..." : "Save Draft"}
                </Button>

                <Button
                  onClick={onPublish}
                  disabled={isPublishing || !canPublish}
                  size="sm"
                  className={`bg-sky-600 hover:bg-sky-700 text-white ${isPublishing || !canPublish ? "cursor-not-allowed" : "cursor-pointer"}`}
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

      {justPublished && screenId && (
        <div className="bg-blue-950/50 border-b border-blue-800/50 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-blue-300">
              Screen published successfully. Run regression tests to verify?
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={handleViewTraces}
              variant="outline"
              size="sm"
              className="text-blue-300 border-blue-700 hover:bg-blue-950/50"
            >
              <ExternalLink className="w-3 h-3 mr-1" />
              View Traces
            </Button>
            <Button
              onClick={handleRunRegression}
              size="sm"
              className="bg-blue-600 hover:bg-blue-700 text-white"
            >
              Run Regression (Recommended)
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
