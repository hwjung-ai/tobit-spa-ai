"use client";

import { useState } from "react";
import { fetchApi } from "../../lib/adminUtils";
import { cn } from "../../lib/utils";
import { useConfirm } from "@/hooks/use-confirm";

interface ToolAsset {
    asset_id: string;
    asset_type: string;
    name: string;
    description: string | null;
    version: number;
    status: string;
    tool_type: string;
    tool_catalog_ref?: string | null;
    tool_config: Record<string, unknown>;
    tool_input_schema: Record<string, unknown>;
    tool_output_schema: Record<string, unknown> | null;
    tags: Record<string, unknown> | null;
    created_by: string | null;
    published_by: string | null;
    published_at: string | null;
    created_at: string;
    updated_at: string;
}

interface ToolTestPanelProps {
    tool: ToolAsset;
    onClose: () => void;
    onRefresh?: () => void;
}

interface TestResult {
    success: boolean;
    data: unknown;
    error: string | null;
    error_details: Record<string, unknown> | null;
}

export default function ToolTestPanel({ tool, onClose, onRefresh }: ToolTestPanelProps) {
    const [testInput, setTestInput] = useState(
        JSON.stringify(generateDefaultInput(tool.tool_input_schema), null, 2)
    );
    const [testResult, setTestResult] = useState<TestResult | null>(null);
    const [isExecuting, setIsExecuting] = useState(false);
    const [isPublishing, setIsPublishing] = useState(false);
    const [isUnpublishing, setIsUnpublishing] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [publishError, setPublishError] = useState<string | null>(null);
    const [activeTab, setActiveTab] = useState<"test" | "schema" | "config">("test");
    const [confirmDialog, ConfirmDialogComponent] = useConfirm();

    const handleTest = async () => {
        setIsExecuting(true);
        setTestResult(null);

        try {
            const parsedInput = JSON.parse(testInput);
            const response = await fetchApi<TestResult>(
                `/asset-registry/tools/${tool.asset_id}/test`,
                {
                    method: "POST",
                    body: JSON.stringify(parsedInput),
                }
            );
            // API returns ResponseEnvelope with data = { success, data, error, error_details }
            const testData = response.data as TestResult;
            setTestResult(testData);
        } catch (err) {
            setTestResult({
                success: false,
                data: null,
                error: err instanceof Error ? err.message : "Test failed",
                error_details: null,
            });
        } finally {
            setIsExecuting(false);
        }
    };

    const handlePublish = async () => {
        setIsPublishing(true);
        setPublishError(null);
        try {
            await fetchApi(`/asset-registry/tools/${tool.asset_id}/publish`, {
                method: "POST",
            });
            onRefresh?.();
            onClose();
        } catch (err) {
            console.error("Publish failed:", err);
            setPublishError(err instanceof Error ? err.message : "Failed to publish tool");
        } finally {
            setIsPublishing(false);
        }
    };

    const handleUnpublish = async () => {
        const ok = await confirmDialog({
            title: "Return to Draft",
            description: "Are you sure you want to return this tool to draft status?",
            confirmLabel: "Return",
        });
        if (!ok) return;

        setIsUnpublishing(true);
        setPublishError(null);
        try {
            await fetchApi(`/asset-registry/tools/${tool.asset_id}/unpublish`, {
                method: "POST",
            });
            onRefresh?.();
            onClose();
        } catch (err) {
            console.error("Unpublish failed:", err);
            setPublishError(err instanceof Error ? err.message : "Failed to unpublish tool");
        } finally {
            setIsUnpublishing(false);
        }
    };

    const handleDeleteDraft = async () => {
        const ok = await confirmDialog({
            title: "Delete Draft Tool",
            description: "Delete this draft tool? This action cannot be undone.",
            confirmLabel: "Delete",
            variant: "destructive",
        });
        if (!ok) return;

        setIsDeleting(true);
        setPublishError(null);
        try {
            await fetchApi(`/asset-registry/tools/${tool.asset_id}`, {
                method: "DELETE",
            });
            onRefresh?.();
            onClose();
        } catch (err) {
            console.error("Delete failed:", err);
            setPublishError(err instanceof Error ? err.message : "Failed to delete tool");
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <>
        <div className="rounded-2xl border border-variant bg-surface-base overflow-hidden shadow-2xl backdrop-blur-sm h-full flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-variant flex items-start justify-between">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <span className={cn(
                            "inline-flex px-3 py-1 rounded-full text-tiny uppercase font-bold tracking-widest border",
                            tool.status === "published"
                                ? "bg-success/15 text-success border-success/30"
                                : "bg-surface-elevated text-muted-foreground border-border"
                        )}>
                            {tool.status}
                        </span>
                        <span className="text-tiny font-mono text-muted-foreground">v{tool.version}</span>
                    </div>
                    <h3 className="text-foreground font-bold text-base mt-2 truncate">{tool.name}</h3>
                    <p className="text-tiny mt-1 line-clamp-2 text-muted-foreground">{tool.description || "No description"}</p>
                </div>
                <button
                    onClick={onClose}
                    className="text-muted-foreground hover:text-foreground transition-colors p-1"
                >
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-variant">
                {[
                    { key: "test", label: "Test" },
                    { key: "schema", label: "Schema" },
                    { key: "config", label: "Config" },
                ].map((tab) => (
                    <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key as "test" | "schema" | "config")}
                        className={cn(
                            "panel-tab flex-1 rounded-none border-0 border-b-2 border-transparent px-4 py-3 text-tiny",
                            activeTab === tab.key
                                ? "panel-tab-active border-b-sky-500"
                                : "panel-tab-inactive hover:text-foreground"
                        )}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4">
                {activeTab === "test" && (
                    <div className="space-y-4">
                        <div>
                            <label className="block text-tiny font-bold uppercase tracking-widest mb-2 text-muted-foreground">
                                Test Input (JSON)
                            </label>
                            <textarea
                                value={testInput}
                                onChange={(e) => setTestInput(e.target.value)}
                                rows={6}
                                className="w-full px-3 py-2 border border-variant rounded-lg font-mono text-xs focus:outline-none focus:border-sky-500 transition-all resize-none bg-surface-base text-foreground"
                            />
                        </div>

                        <button
                            onClick={handleTest}
                            disabled={isExecuting}
                            className={cn(
                                "w-full py-3 rounded-lg transition-all font-bold text-tiny uppercase tracking-widest shadow-lg shadow-sky-900/20",
                                isExecuting
                                    ? "bg-surface-elevated text-muted-foreground cursor-not-allowed"
                                    : "bg-sky-600 hover:bg-sky-500 text-white"
                            )}
                        >
                            {isExecuting ? (
                                <span className="flex items-center justify-center gap-2">
                                    <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24" fill="none">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Executing...
                                </span>
                            ) : (
                                "Run Test"
                            )}
                        </button>

                        {testResult && (
                            <div className={cn(
                                "rounded-lg border p-4",
                                testResult.success
                                    ? "bg-success/10 border-success/30"
                                    : "bg-error/10 border-error/30"
                            )}>
                                <div className="flex items-center gap-2 mb-2">
                                    {testResult.success ? (
                                        <svg className="w-4 h-4 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                    ) : (
                                        <svg className="w-4 h-4 text-error" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                    )}
                                    <span className={cn(
                                        "text-tiny font-bold uppercase tracking-wider",
                                        testResult.success ? "text-success" : "text-error"
                                    )}>
                                        {testResult.success ? "Success" : "Failed"}
                                    </span>
                                </div>

                                {testResult.error && (
                                    <div className="text-error text-tiny mb-2">
                                        {testResult.error}
                                    </div>
                                )}

                                {testResult.data && (
                                    <div className="mt-2">
                                        <label className="block text-tiny font-bold uppercase tracking-widest mb-1 text-muted-foreground">
                                            Output
                                        </label>
                                        <pre className="rounded-lg p-3 text-tiny font-mono overflow-x-auto max-h-60 overflow-y-auto bg-surface-base text-muted-foreground">
                                            {JSON.stringify(testResult.data, null, 2)}
                                        </pre>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === "schema" && (
                    <div className="space-y-4">
                        <div>
                            <label className="block text-tiny font-bold uppercase tracking-widest mb-2 text-muted-foreground">
                                Input Schema
                            </label>
                            <pre className="rounded-lg p-3 text-tiny font-mono overflow-x-auto max-h-60 overflow-y-auto border border-variant bg-surface-base text-muted-foreground">
                                {JSON.stringify(tool.tool_input_schema, null, 2)}
                            </pre>
                        </div>

                        {tool.tool_output_schema && (
                            <div>
                                <label className="block text-tiny font-bold uppercase tracking-widest mb-2 text-muted-foreground">
                                    Output Schema
                                </label>
                                <pre className="rounded-lg p-3 text-tiny font-mono overflow-x-auto max-h-60 overflow-y-auto border border-variant bg-surface-base text-muted-foreground">
                                    {JSON.stringify(tool.tool_output_schema, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === "config" && (
                    <div className="space-y-4">
                        <div>
                            <label className="block text-tiny font-bold uppercase tracking-widest mb-2 text-muted-foreground">
                                Tool Type
                            </label>
                            <div className="px-3 py-2 border border-variant rounded-lg bg-surface-base">
                                <span className="text-tiny font-mono text-muted-foreground">{tool.tool_type}</span>
                            </div>
                        </div>

                        {tool.tool_catalog_ref && (
                            <div>
                                <label className="block text-tiny font-bold uppercase tracking-widest mb-2 text-muted-foreground">
                                    🗄️ Linked Catalog
                                </label>
                                <div className="px-3 py-2 bg-sky-950/30 border border-sky-800/50 rounded-lg">
                                    <span className="text-sky-300 text-tiny font-mono">{tool.tool_catalog_ref}</span>
                                </div>
                                <p className="text-tiny mt-1 text-muted-foreground">This Tool references a database schema catalog for accurate SQL generation</p>
                            </div>
                        )}

                        <div>
                            <label className="block text-tiny font-bold uppercase tracking-widest mb-2 text-muted-foreground">
                                Configuration
                            </label>
                            <pre className="rounded-lg p-3 text-tiny font-mono overflow-x-auto max-h-80 overflow-y-auto border border-variant bg-surface-base text-muted-foreground">
                                {JSON.stringify(tool.tool_config, null, 2)}
                            </pre>
                        </div>

                        {tool.tags && Object.keys(tool.tags).length > 0 && (
                            <div>
                                <label className="block text-tiny font-bold uppercase tracking-widest mb-2 text-muted-foreground">
                                    Tags
                                </label>
                                <pre className="rounded-lg p-3 text-tiny font-mono overflow-x-auto border border-variant bg-surface-base text-muted-foreground">
                                    {JSON.stringify(tool.tags, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Footer Actions */}
            <div className="p-4 border-t border-variant space-y-3">
                {publishError && (
                    <div className="rounded-md border border-error/40 bg-error/10 px-3 py-2 text-tiny text-error">
                        {publishError}
                    </div>
                )}
                <div className="flex gap-3">
                    {tool.status === "draft" && (
                        <>
                            <button
                                onClick={handleDeleteDraft}
                                disabled={isDeleting || isPublishing}
                                className={cn(
                                    "flex-1 px-4 py-3 border rounded-xl transition-all font-bold text-tiny uppercase tracking-widest",
                                    isDeleting
                                        ? "bg-surface-elevated border-variant text-muted-foreground cursor-not-allowed opacity-70"
                                        : "bg-error/15 text-error border-error/40 hover:bg-error/25 hover:border-error"
                                )}
                            >
                                <span className="flex items-center justify-center gap-2">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                    </svg>
                                    {isDeleting ? "Deleting..." : "Delete Draft"}
                                </span>
                            </button>
                            <button
                                onClick={handlePublish}
                                disabled={isPublishing || isDeleting}
                                className={cn(
                                    "flex-1 px-4 py-3 border rounded-xl transition-all font-bold text-tiny uppercase tracking-widest",
                                    isPublishing
                                        ? "bg-surface-elevated border-variant text-muted-foreground cursor-not-allowed opacity-70"
                                        : "bg-success/15 text-success border-success/40 hover:bg-success/25 hover:border-success"
                                )}
                            >
                                <span className="flex items-center justify-center gap-2">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                    {isPublishing ? "Publishing..." : "Publish Tool"}
                                </span>
                            </button>
                        </>
                    )}
                    {tool.status === "published" && (
                        <button
                            onClick={handleUnpublish}
                            disabled={isUnpublishing}
                            className={cn(
                                "flex-1 px-4 py-3 border rounded-xl transition-all font-bold text-tiny uppercase tracking-widest",
                                isUnpublishing
                                    ? "bg-surface-elevated border-variant text-muted-foreground cursor-not-allowed opacity-70"
                                    : "bg-warning/15 text-warning border-warning/40 hover:bg-warning/25 hover:border-warning"
                            )}
                        >
                            <span className="flex items-center justify-center gap-2">
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 15l-3-3m0 0l3-3m-3 3h8M3 12a9 9 0 1118 0 9 9 0 01-18 0z" />
                                </svg>
                                {isUnpublishing ? "Rolling back..." : "Return to Draft"}
                            </span>
                        </button>
                    )}
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-3 border rounded-xl transition-all font-bold text-tiny uppercase tracking-widest bg-surface-base text-foreground border-variant hover:border-sky-600 hover:bg-sky-600 dark:bg-surface-base dark:text-muted-foreground dark:border-variant dark:hover:border-sky-500 dark:hover:bg-sky-600"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
        <ConfirmDialogComponent />
        </>
    );
}

/**
 * Generate default input values from JSON schema
 */
function generateDefaultInput(schema: Record<string, unknown>): Record<string, unknown> {
    if (!schema || schema.type !== "object" || !schema.properties) {
        return {};
    }

    const result: Record<string, unknown> = {};
    const properties = schema.properties as Record<string, Record<string, unknown>>;

    for (const [key, prop] of Object.entries(properties)) {
        if (prop.default !== undefined) {
            result[key] = prop.default;
        } else if (prop.type === "string") {
            result[key] = prop.example || "";
        } else if (prop.type === "integer" || prop.type === "number") {
            result[key] = prop.example || 0;
        } else if (prop.type === "boolean") {
            result[key] = prop.example || false;
        } else if (prop.type === "array") {
            result[key] = prop.example || [];
        } else if (prop.type === "object") {
            result[key] = prop.example || {};
        }
    }

    return result;
}
