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
  onSaveDraft: () => void;
  onPublish: () => void;
  onRollback: () => void;
  isSaving: boolean;
  isPublishing: boolean;
  justPublished?: boolean;
  screenId?: string;
  assetId?: string;
  screenVersion?: string | null;
}

export default function ScreenEditorHeader({
  status,
  isDirty,
  canPublish,
  onSaveDraft,
  onPublish,
  onRollback,
  isSaving,
  isPublishing,
  justPublished,
  screenId,
  assetId,
  screenVersion,
}: ScreenEditorHeaderProps) {
  const router = useRouter();

  const buildContextQuery = () => {
    const params = new URLSearchParams();
    if (screenId) {
      params.set("screen_id", screenId);
    }
    if (assetId) {
      params.set("asset_id", assetId);
    }
    if (screenVersion) {
      params.set("version", screenVersion);
    }
    return params.toString();
  };

  const contextQuery = buildContextQuery();
  const contextQueryString = contextQuery ? `?${contextQuery}` : "";

  const isPublished = status === "published";
  const ctaDisabled = !isPublished || !screenId || !assetId;
  const publishHint =
    !isPublished
      ? "Publish the screen to access runtime, regression, and inspector tools."
      : null;

  const handleRunRegression = () => {
    if (!screenId) return;
    router.push(`/admin/regression${contextQueryString}`);
  };

  const handleOpenInspector = () => {
    if (!screenId && !assetId) return;
    window.open(`/admin/inspector${contextQueryString}`, "_blank");
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
            <div className="flex flex-col items-end gap-2">
              <Button
                onClick={() => {
                  if (status === "published" && assetId) {
                    router.push(`/ui/screens/${assetId}`);
                  }
                }}
                variant="outline"
                size="sm"
                className={`flex items-center gap-1 text-slate-200 border-slate-600 hover:border-slate-500 ${
                  status === "draft" || !assetId ? "cursor-not-allowed opacity-70" : "hover:bg-slate-800"
                }`}
                disabled={status === "draft" || !assetId}
                data-testid="btn-open-runtime"
              >
                <ExternalLink className="w-3 h-3" />
                <span className="text-[11px]">Open in UI</span>
              </Button>
              <div className="flex gap-2">
                <Button
                  onClick={handleRunRegression}
                  disabled={ctaDisabled}
                  size="sm"
                  className={`text-[11px] uppercase tracking-wider ${
                    ctaDisabled
                      ? "cursor-not-allowed opacity-70 border border-slate-700 text-slate-500"
                      : "bg-slate-800 hover:bg-slate-700 text-white"
                  }`}
                >
                  Run Regression
                </Button>
                <Button
                  onClick={handleOpenInspector}
                  disabled={ctaDisabled}
                  variant="outline"
                  size="sm"
                  className={`flex items-center gap-1 text-slate-200 border-slate-600 ${
                    ctaDisabled ? "cursor-not-allowed opacity-70" : "hover:border-slate-500 hover:bg-slate-800"
                  }`}
                >
                  <ExternalLink className="w-3 h-3" />
                  <span className="text-[11px]">Open Inspector</span>
                </Button>
              </div>
              {publishHint && (
                <p className="text-[10px] text-slate-500">{publishHint}</p>
              )}
            </div>
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
              onClick={handleOpenInspector}
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
