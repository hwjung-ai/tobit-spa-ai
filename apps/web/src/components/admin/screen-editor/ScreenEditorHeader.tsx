"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { CheckCircle, ExternalLink, Undo2, Redo2 } from "lucide-react";

interface ScreenEditorHeaderProps {
  status: "draft" | "published";
  isDirty: boolean;
  canPublish: boolean;
  onSaveDraft: () => void;
  onPublish: () => void;
  onRollback: () => void;
  onUndo?: () => void;
  onRedo?: () => void;
  canUndo?: boolean;
  canRedo?: boolean;
  isSaving: boolean;
  isPublishing: boolean;
  justPublished?: boolean;
  screenId?: string;
  assetId?: string;
  screenVersion?: string | null;
  screenName?: string;
}

export default function ScreenEditorHeader({
  status,
  isDirty,
  canPublish,
  onSaveDraft,
  onPublish,
  onRollback,
  onUndo,
  onRedo,
  canUndo = false,
  canRedo = false,
  isSaving,
  isPublishing,
  justPublished,
  screenId,
  assetId,
  screenVersion,
  screenName,
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
      <div className="border-b px-6 py-4" style={{ borderColor: "var(--border)", backgroundColor: "rgba(15, 23, 42, 0.5)" }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/admin/screens"
              className="transition-colors"
              style={{ color: "rgba(56, 189, 248, 1)" }}
            >
              ← Back to Screens
            </Link>

            {screenName && (
              <div className="flex items-center gap-2 border-r pr-3 mr-1" style={{ borderColor: "var(--border-muted)" }}>
                <h1 className="text-lg font-semibold" style={{ color: "var(--foreground)" }}>{screenName}</h1>
              </div>
            )}

            <div className="flex items-center gap-1 border-r pr-3 mr-1" style={{ borderColor: "var(--border-muted)" }}>
              <Button
                size="sm"
                variant="ghost"
                onClick={onUndo}
                disabled={!canUndo}
                title="Undo (Ctrl+Z)"
                className="h-7 w-7 p-0 disabled:opacity-30"
                style={{ color: "var(--muted-foreground)" }}
              >
                <Undo2 className="w-4 h-4" />
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={onRedo}
                disabled={!canRedo}
                title="Redo (Ctrl+Shift+Z)"
                className="h-7 w-7 p-0 disabled:opacity-30"
                style={{ color: "var(--muted-foreground)" }}
              >
                <Redo2 className="w-4 h-4" />
              </Button>
            </div>

            <div className="flex items-center gap-3">
              <span
                className={`inline-flex px-3 py-1 rounded text-xs font-bold uppercase tracking-wider border ${status === "published"
                  ? ""
                  : ""
                  }`}
                style={status === "published" ? { backgroundColor: "rgba(6, 78, 59, 0.5)", color: "#86efac", borderColor: "rgba(16, 185, 129, 0.5)" } : { backgroundColor: "rgba(30, 41, 59, 0.5)", color: "var(--muted-foreground)", borderColor: "rgba(51, 65, 85, 0.5)" }}
                data-testid="status-badge"
              >
                {status}
              </span>

              {isDirty && (
                <span className="text-xs font-medium" style={{ color: "rgba(234, 179, 8, 1)" }}>
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
                  className={`
                    ${isSaving || !isDirty
                      ? "cursor-not-allowed   /50"
                      : "cursor-pointer  text-white 0 hover:"
                    }
                  `} style={{ backgroundColor: "var(--surface-overlay)", backgroundColor: "var(--surface-elevated)", backgroundColor: "var(--surface-elevated)", color: "var(--muted-foreground)", borderColor: "var(--border)", borderColor: "var(--border)" }}
                  data-testid="btn-save-draft"
                >
                  {isSaving ? "Saving..." : "Save Draft"}
                </Button>

                <Button
                  onClick={onPublish}
                  disabled={isPublishing || !canPublish}
                  size="sm"
                  className={`bg-sky-600 hover:bg-sky-700 text-white border-none ${isPublishing || !canPublish ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}
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
                className="text-orange-400 border-orange-900 bg-orange-950/20 hover:bg-orange-950/40"
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
                className={`flex items-center gap-1  ${status === "draft" || !assetId
                  ? "cursor-not-allowed  "
                  : "  hover: hover:text-white hover:"
                  }`} style={{ backgroundColor: "var(--surface-overlay)", backgroundColor: "var(--surface-elevated)", backgroundColor: "var(--surface-elevated)", color: "var(--foreground-secondary)", color: "var(--muted-foreground)", borderColor: "var(--border)", borderColor: "var(--border)" }}
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
                  className={`text-[11px] uppercase tracking-wider ${ctaDisabled
                    ? "cursor-not-allowed   border /50"
                    : " hover: text-white border "
                    }`} style={{ backgroundColor: "var(--surface-overlay)", backgroundColor: "var(--surface-elevated)", backgroundColor: "var(--surface-elevated)", color: "var(--muted-foreground)", borderColor: "var(--border)", borderColor: "var(--border)" }}
                >
                  Run Regression
                </Button>
                <Button
                  onClick={handleOpenInspector}
                  disabled={ctaDisabled}
                  variant="outline"
                  size="sm"
                  className={`flex items-center gap-1 ${ctaDisabled
                    ? "cursor-not-allowed   /50"
                    : "   hover: hover:text-white"
                    }`} style={{ backgroundColor: "var(--surface-overlay)", backgroundColor: "var(--surface-elevated)", backgroundColor: "var(--surface-elevated)", color: "var(--foreground-secondary)", color: "var(--muted-foreground)", borderColor: "var(--border)", borderColor: "var(--border)" }}
                >
                  <ExternalLink className="w-3 h-3" />
                  <span className="text-[11px]">Open Inspector</span>
                </Button>
              </div>
              {publishHint && (
                <p className="text-[10px] " style={{ color: "var(--muted-foreground)" }}>{publishHint}</p>
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
