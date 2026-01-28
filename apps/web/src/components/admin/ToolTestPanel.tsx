"use client";

import { useState } from "react";
import { fetchApi } from "../../lib/adminUtils";

interface ToolAsset {
    asset_id: string;
    asset_type: string;
    name: string;
    description: string | null;
    version: number;
    status: string;
    tool_type: string;
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
    const [activeTab, setActiveTab] = useState<"test" | "schema" | "config">("test");

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
        try {
            await fetchApi(`/asset-registry/tools/${tool.asset_id}/publish`, {
                method: "POST",
            });
            onRefresh?.();
        } catch (err) {
            console.error("Publish failed:", err);
        } finally {
            setIsPublishing(false);
        }
    };

    return (
        <div className="bg-slate-900/80 rounded-2xl border border-slate-800 overflow-hidden shadow-2xl backdrop-blur-sm h-full flex flex-col">
            {/* Header */}
            <div className="p-4 border-b border-slate-800 flex items-start justify-between">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${
                            tool.status === "published"
                                ? "bg-emerald-950/50 text-emerald-300 border border-emerald-800/50"
                                : "bg-slate-800/50 text-slate-400 border border-slate-700/50"
                        }`}>
                            {tool.status}
                        </span>
                        <span className="text-slate-600 text-xs font-mono">v{tool.version}</span>
                    </div>
                    <h3 className="text-white font-bold text-lg mt-1 truncate">{tool.name}</h3>
                    <p className="text-slate-500 text-xs mt-0.5 line-clamp-2">{tool.description || "No description"}</p>
                </div>
                <button
                    onClick={onClose}
                    className="text-slate-500 hover:text-white transition-colors p-1"
                >
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-slate-800">
                {[
                    { key: "test", label: "Test" },
                    { key: "schema", label: "Schema" },
                    { key: "config", label: "Config" },
                ].map((tab) => (
                    <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key as "test" | "schema" | "config")}
                        className={`flex-1 px-4 py-2.5 text-[10px] font-bold uppercase tracking-widest transition-all ${
                            activeTab === tab.key
                                ? "text-sky-400 border-b-2 border-sky-400 bg-sky-400/5"
                                : "text-slate-500 hover:text-slate-300"
                        }`}
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
                            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                                Test Input (JSON)
                            </label>
                            <textarea
                                value={testInput}
                                onChange={(e) => setTestInput(e.target.value)}
                                rows={6}
                                className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono text-xs focus:outline-none focus:border-sky-500 transition-all resize-none"
                            />
                        </div>

                        <button
                            onClick={handleTest}
                            disabled={isExecuting}
                            className="w-full py-2.5 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-lg transition-all font-bold text-xs uppercase tracking-widest shadow-lg shadow-sky-900/20"
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
                            <div className={`rounded-lg border p-4 ${
                                testResult.success
                                    ? "bg-emerald-950/30 border-emerald-800/50"
                                    : "bg-red-950/30 border-red-800/50"
                            }`}>
                                <div className="flex items-center gap-2 mb-2">
                                    {testResult.success ? (
                                        <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                    ) : (
                                        <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                        </svg>
                                    )}
                                    <span className={`text-sm font-bold ${
                                        testResult.success ? "text-emerald-300" : "text-red-300"
                                    }`}>
                                        {testResult.success ? "Success" : "Failed"}
                                    </span>
                                </div>

                                {testResult.error && (
                                    <div className="text-red-300 text-xs mb-2">
                                        {testResult.error}
                                    </div>
                                )}

                                {testResult.data && (
                                    <div className="mt-2">
                                        <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">
                                            Output
                                        </label>
                                        <pre className="bg-slate-950 rounded-lg p-3 text-xs text-slate-300 font-mono overflow-x-auto max-h-60 overflow-y-auto">
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
                            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                                Input Schema
                            </label>
                            <pre className="bg-slate-950 rounded-lg p-3 text-xs text-slate-300 font-mono overflow-x-auto max-h-60 overflow-y-auto border border-slate-800">
                                {JSON.stringify(tool.tool_input_schema, null, 2)}
                            </pre>
                        </div>

                        {tool.tool_output_schema && (
                            <div>
                                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                                    Output Schema
                                </label>
                                <pre className="bg-slate-950 rounded-lg p-3 text-xs text-slate-300 font-mono overflow-x-auto max-h-60 overflow-y-auto border border-slate-800">
                                    {JSON.stringify(tool.tool_output_schema, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === "config" && (
                    <div className="space-y-4">
                        <div>
                            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                                Tool Type
                            </label>
                            <div className="px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg">
                                <span className="text-slate-200 text-sm font-mono">{tool.tool_type}</span>
                            </div>
                        </div>

                        <div>
                            <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                                Configuration
                            </label>
                            <pre className="bg-slate-950 rounded-lg p-3 text-xs text-slate-300 font-mono overflow-x-auto max-h-80 overflow-y-auto border border-slate-800">
                                {JSON.stringify(tool.tool_config, null, 2)}
                            </pre>
                        </div>

                        {tool.tags && Object.keys(tool.tags).length > 0 && (
                            <div>
                                <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2">
                                    Tags
                                </label>
                                <pre className="bg-slate-950 rounded-lg p-3 text-xs text-slate-300 font-mono overflow-x-auto border border-slate-800">
                                    {JSON.stringify(tool.tags, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Footer Actions */}
            <div className="p-4 border-t border-slate-800 flex gap-3">
                {tool.status === "draft" && (
                    <button
                        onClick={handlePublish}
                        disabled={isPublishing}
                        className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-lg transition-all font-bold text-xs uppercase tracking-widest"
                    >
                        {isPublishing ? "Publishing..." : "Publish Tool"}
                    </button>
                )}
                <button
                    onClick={onClose}
                    className="flex-1 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-all font-bold text-xs uppercase tracking-widest"
                >
                    Close
                </button>
            </div>
        </div>
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
