"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchApi } from "@/lib/adminUtils";
import { useQuery } from "@tanstack/react-query";

// LLM Call Log interfaces
export interface LlmCallLog {
    id: string;
    trace_id: string | null;
    call_type: string;
    call_index: number;
    model_name: string;
    provider: string | null;
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    duration_ms: number;
    status: string;
    feature: string | null;
    ui_endpoint: string | null;
    request_time: string;
    response_time: string | null;
    created_at: string;
}

export interface LlmLogDetail extends LlmCallLog {
    system_prompt: string | null;
    user_prompt: string | null;
    raw_response: string | null;
    parsed_response: Record<string, unknown> | null;
    context: Record<string, unknown> | null;
    error_message: string | null;
    error_details: Record<string, unknown> | null;
    user_id: string | null;
    tags: Record<string, unknown> | null;
}

export interface LlmCallAnalytics {
    total_calls: number;
    successful_calls: number;
    failed_calls: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_tokens: number;
    avg_latency_ms: number;
    total_duration_ms: number;
    model_breakdown: Record<string, number>;
    feature_breakdown: Record<string, number>;
    call_type_breakdown: Record<string, number>;
}

type FilterStatus = "all" | "success" | "error";
type FilterCallType = "all" | "planner" | "output_parser" | "tool";
type FilterFeature = "all" | "ops" | "docs" | "cep";
type DateRangeOption = "1h" | "24h" | "7d" | "30d" | "all" | "custom";

export default function LlmLogsContent() {
    const llmLogsBasePath = "/admin/llm-logs";
    const [statusFilter, setStatusFilter] = useState<FilterStatus>("all");
    const [callTypeFilter, setCallTypeFilter] = useState<FilterCallType>("all");
    const [featureFilter, setFeatureFilter] = useState<FilterFeature>("all");
    const [dateRange, setDateRange] = useState<DateRangeOption>("24h");
    const [customFromDate, setCustomFromDate] = useState<string>("");
    const [customToDate, setCustomToDate] = useState<string>("");
    const [selectedLog, setSelectedLog] = useState<LlmCallLog | null>(null);
    const [logDetail, setLogDetail] = useState<LlmLogDetail | null>(null);
    const [showDetailModal, setShowDetailModal] = useState(false);
    const [analytics, setAnalytics] = useState<LlmCallAnalytics | null>(null);

    // Fetch logs
    const { data: logsResponse, isLoading, error, refetch } = useQuery({
        queryKey: ["llm-logs", statusFilter, callTypeFilter, featureFilter, dateRange, customFromDate, customToDate],
        queryFn: async () => {
            const params = new URLSearchParams();
            if (statusFilter !== "all") params.append("status", statusFilter);
            if (callTypeFilter !== "all") params.append("call_type", callTypeFilter);
            if (featureFilter !== "all") params.append("feature", featureFilter);

            // Date range filter
            const { fromDate, toDate } = getDateRangeFilter(dateRange, customFromDate, customToDate);
            if (fromDate) params.append("from", fromDate);
            if (toDate) params.append("to", toDate);

            params.append("limit", "100");

            const queryString = params.toString();
            const endpoint = `${llmLogsBasePath}${queryString ? `?${queryString}` : ""}`;
            return fetchApi<{ logs: LlmCallLog[]; total: number }>(endpoint);
        },
    });

    const logs = logsResponse?.data?.logs || [];
    const total = logsResponse?.data?.total || 0;

    // Fetch analytics
    const { data: analyticsResponse } = useQuery({
        queryKey: ["llm-analytics"],
        queryFn: async () => {
            return fetchApi<LlmCallAnalytics>(`${llmLogsBasePath}/analytics`);
        },
        refetchInterval: 60000,
    });

    useEffect(() => {
        if (analyticsResponse?.data) {
            setAnalytics(analyticsResponse.data);
        }
    }, [analyticsResponse]);

    const handleLogClick = async (log: LlmCallLog) => {
        setSelectedLog(log);
        setShowDetailModal(true);

        try {
            const response = await fetchApi<LlmLogDetail>(`${llmLogsBasePath}/${log.id}`);
            setLogDetail(response.data);
        } catch (err) {
            console.error("Failed to fetch log detail:", err);
        }
    };

    const handleCloseDetail = () => {
        setShowDetailModal(false);
        setSelectedLog(null);
        setLogDetail(null);
    };

    const getStatusBadgeClass = (status: string) => {
        switch (status) {
            case "success":
                return "bg-green-500/20 text-green-400 border-green-500/30";
            case "error":
                return "bg-rose-500/20 text-rose-400 border-rose-500/30";
            default:
                return "bg-slate-500/10 text-slate-300 border-slate-500/30";
        }
    };

    const getCallTypeBadgeClass = (callType: string) => {
        const colors: Record<string, string> = {
            planner: "bg-purple-500/20 text-purple-400 border-purple-500/30",
            output_parser: "bg-sky-500/20 text-sky-400 border-sky-500/30",
            tool: "bg-orange-500/20 text-orange-400 border-orange-500/30",
            default: "bg-slate-500/10 text-slate-300 border-slate-500/30",
        };
        return colors[callType] || colors.default;
    };

    const formatNumber = (num: number) => {
        return new Intl.NumberFormat().format(num);
    };

    const formatDuration = (ms: number) => {
        if (ms < 1000) return `${ms}ms`;
        return `${(ms / 1000).toFixed(2)}s`;
    };

    const formatTokens = (tokens: number) => {
        if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(1)}M`;
        if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`;
        return formatNumber(tokens);
    };

    const getDateRangeFilter = (
        range: DateRangeOption,
        customFrom: string,
        customTo: string
    ): { fromDate: string | null; toDate: string | null } => {
        const now = new Date();

        switch (range) {
            case "1h":
            case "24h":
            case "7d":
            case "30d":
                const fromDate = new Date(now);
                const toDate = new Date(now);

                switch (range) {
                    case "1h":
                        fromDate.setHours(fromDate.getHours() - 1);
                        break;
                    case "24h":
                        fromDate.setHours(fromDate.getHours() - 24);
                        break;
                    case "7d":
                        fromDate.setDate(fromDate.getDate() - 7);
                        break;
                    case "30d":
                        fromDate.setDate(fromDate.getDate() - 30);
                        break;
                }

                return {
                    fromDate: fromDate.toISOString(),
                    toDate: now.toISOString()
                };
            case "all":
                return { fromDate: null, toDate: null };
            case "custom":
                return {
                    fromDate: customFrom ? new Date(customFrom).toISOString() : null,
                    toDate: customTo ? new Date(customTo).toISOString() : null
                };
            default:
                return { fromDate: null, toDate: null };
        }
    };

    const formatDateForInput = (dateStr: string) => {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toISOString().slice(0, 16); // YYYY-MM-DDTHH:mm
    };

    const handleDateRangeChange = (newRange: DateRangeOption) => {
        setDateRange(newRange);
    };

    return (
        <div className="space-y-6">
            {/* Analytics Cards */}
            {analytics && (
                <div className="grid grid-cols-4 gap-4">
                    <div className="llm-stat-card">
                        <div className="llm-stat-label">Total Calls</div>
                        <div className="llm-stat-value">{formatNumber(analytics.total_calls)}</div>
                        <div className="llm-stat-secondary">
                            <span className="text-green-400">{formatNumber(analytics.successful_calls)} success</span>
                            <span className="text-rose-400">{formatNumber(analytics.failed_calls)} error</span>
                        </div>
                    </div>

                    <div className="llm-stat-card">
                        <div className="llm-stat-label">Total Tokens</div>
                        <div className="llm-stat-value">{formatTokens(analytics.total_tokens)}</div>
                        <div className="llm-stat-secondary">
                            <span>In: {formatTokens(analytics.total_input_tokens)}</span>
                            <span>Out: {formatTokens(analytics.total_output_tokens)}</span>
                        </div>
                    </div>

                    <div className="llm-stat-card">
                        <div className="llm-stat-label">Avg Latency</div>
                        <div className="llm-stat-value">{formatDuration(analytics.avg_latency_ms)}</div>
                        <div className="llm-stat-secondary">Total: {formatDuration(analytics.total_duration_ms)}</div>
                    </div>

                    <div className="llm-stat-card">
                        <div className="llm-stat-label">Top Model</div>
                        <div className="llm-stat-value text-lg truncate">
                            {Object.entries(analytics.model_breakdown).sort((a, b) => b[1] - a[1])[0]?.[0] || "N/A"}
                        </div>
                        <div className="llm-stat-secondary">
                            {Object.keys(analytics.model_breakdown).length} models used
                        </div>
                    </div>
                </div>
            )}

            {/* Filters */}
            <div className="llm-filter-bar">
                {/* Date Range Filter */}
                <div className="flex-1">
                    <label className="llm-filter-label">Date Range</label>
                    <select
                        value={dateRange}
                        onChange={(e) => setDateRange(e.target.value as DateRangeOption)}
                        className="api-select"
                    >
                        <option value="1h">Last 1 Hour</option>
                        <option value="24h">Last 24 Hours</option>
                        <option value="7d">Last 7 Days</option>
                        <option value="30d">Last 30 Days</option>
                        <option value="all">All Time</option>
                        <option value="custom">Custom Range</option>
                    </select>
                </div>

                {/* Custom Date Inputs (shown only when "custom" is selected) */}
                {dateRange === "custom" && (
                    <>
                        <div className="flex-1">
                            <label className="llm-filter-label">From</label>
                            <input
                                type="datetime-local"
                                value={formatDateForInput(customFromDate)}
                                onChange={(e) => setCustomFromDate(e.target.value)}
                                className="api-input"
                            />
                        </div>
                        <div className="flex-1">
                            <label className="llm-filter-label">To</label>
                            <input
                                type="datetime-local"
                                value={formatDateForInput(customToDate)}
                                onChange={(e) => setCustomToDate(e.target.value)}
                                className="api-input"
                            />
                        </div>
                    </>
                )}

                <div className="flex-1">
                    <label className="llm-filter-label">Status</label>
                    <select
                        value={statusFilter}
                        onChange={(e) => setStatusFilter(e.target.value as FilterStatus)}
                        className="api-select"
                    >
                        <option value="all">All Status</option>
                        <option value="success">Success</option>
                        <option value="error">Error</option>
                    </select>
                </div>

                <div className="flex-1">
                    <label className="llm-filter-label">Call Type</label>
                    <select
                        value={callTypeFilter}
                        onChange={(e) => setCallTypeFilter(e.target.value as FilterCallType)}
                        className="llm-filter-input w-full"
                    >
                        <option value="all">All Types</option>
                        <option value="planner">Planner</option>
                        <option value="output_parser">Output Parser</option>
                        <option value="tool">Tool Call</option>
                    </select>
                </div>

                <div className="flex-1">
                    <label className="llm-filter-label">Feature</label>
                    <select
                        value={featureFilter}
                        onChange={(e) => setFeatureFilter(e.target.value as FilterFeature)}
                        className="llm-filter-input w-full"
                    >
                        <option value="all">All Features</option>
                        <option value="ops">OPS</option>
                        <option value="docs">Documents</option>
                        <option value="cep">CEP</option>
                    </select>
                </div>
            </div>

            {/* Logs Table */}
            <div className="llm-stat-card rounded-xl border overflow-hidden">
                {isLoading ? (
                    <div className="flex items-center justify-center py-20">
                        <div className="w-8 h-8 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
                        <span className="ml-3 text-sm text-muted-standard">Loading logs...</span>
                    </div>
                ) : error ? (
                    <div className="text-center py-20">
                        <p className="text-rose-400 text-sm">Failed to load logs</p>
                        <button
                            onClick={() => refetch()}
                            className="mt-4 px-4 py-2  hover:  rounded-lg text-sm" style={{color: "var(--muted-foreground)", backgroundColor: "var(--surface-base)"}}
                        >
                            Try Again
                        </button>
                    </div>
                ) : logs.length === 0 ? (
                    <div className="text-center py-20">
                        <p className=" text-sm" style={{color: "var(--muted-foreground)"}}>No LLM call logs found</p>
                        <p className=" text-xs mt-2" style={{color: "var(--muted-foreground)"}}>LLM calls will appear here once you make queries through OPS</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full">
                            <thead className="/50" style={{backgroundColor: "var(--surface-base)"}}>
                                <tr>
                                    <th className="px-3 py-3 text-left text-xs font-bold  uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}>Time</th>
                                    <th className="px-3 py-3 text-left text-xs font-bold  uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}>Type</th>
                                    <th className="px-3 py-3 text-left text-xs font-bold  uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}>Model</th>
                                    <th className="px-3 py-3 text-right text-xs font-bold  uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}>In</th>
                                    <th className="px-3 py-3 text-right text-xs font-bold  uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}>Out</th>
                                    <th className="px-3 py-3 text-right text-xs font-bold  uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}>Total</th>
                                    <th className="px-3 py-3 text-right text-xs font-bold  uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}>Duration</th>
                                    <th className="px-3 py-3 text-center text-xs font-bold  uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}>Status</th>
                                    <th className="px-3 py-3 text-left text-xs font-bold  uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}>Feature</th>
                                    <th className="px-3 py-3 text-left text-xs font-bold  uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}>Provider</th>
                                    <th className="px-3 py-3 text-left text-xs font-bold  uppercase tracking-wider" style={{color: "var(--muted-foreground)"}}>Trace</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800">
                                {logs.map((log) => (
                                    <tr
                                        key={log.id}
                                        onClick={() => handleLogClick(log)}
                                        className="hover: cursor-pointer transition-colors" style={{backgroundColor: "var(--surface-elevated)"}}
                                    >
                                        <td className="px-3 py-3 text-sm  whitespace-nowrap" style={{color: "var(--muted-foreground)"}}>
                                            {new Date(log.created_at).toLocaleString()}
                                        </td>
                                        <td className="px-3 py-3">
                                            <span className={`px-2 py-1 rounded text-xs font-medium border ${getCallTypeBadgeClass(log.call_type)}`}>
                                                {log.call_type}
                                            </span>
                                        </td>
                                        <td className="px-3 py-3 text-sm  font-mono" style={{color: "var(--muted-foreground)"}}>
                                            {log.model_name}
                                        </td>
                                        <td className="px-3 py-3 text-sm  text-right font-mono" style={{color: "var(--muted-foreground)"}}>
                                            {formatTokens(log.input_tokens)}
                                        </td>
                                        <td className="px-3 py-3 text-sm  text-right font-mono" style={{color: "var(--muted-foreground)"}}>
                                            {formatTokens(log.output_tokens)}
                                        </td>
                                        <td className="px-3 py-3 text-sm  text-right font-mono" style={{color: "var(--muted-foreground)"}}>
                                            {formatTokens(log.total_tokens)}
                                        </td>
                                        <td className="px-3 py-3 text-sm  text-right font-mono" style={{color: "var(--muted-foreground)"}}>
                                            {formatDuration(log.duration_ms)}
                                        </td>
                                        <td className="px-3 py-3 text-center">
                                            <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusBadgeClass(log.status)}`}>
                                                {log.status}
                                            </span>
                                        </td>
                                        <td className="px-3 py-3 text-sm " style={{color: "var(--muted-foreground)"}}>
                                            {log.feature || "-"}
                                        </td>
                                        <td className="px-3 py-3 text-sm " style={{color: "var(--muted-foreground)"}}>
                                            {log.provider || "-"}
                                        </td>
                                        <td className="px-3 py-3 text-sm  font-mono" style={{color: "var(--muted-foreground)"}}>
                                            {log.trace_id ? log.trace_id.slice(0, 8) + "..." : "-"}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}

                {/* Pagination Note */}
                {total > 100 && (
                    <div className="px-4 py-3 border-t  flex items-center justify-between text-xs " style={{borderColor: "var(--border)", color: "var(--muted-foreground)"}}>
                        <span>Showing {Math.min(100, total)} of {formatNumber(total)} logs</span>
                        <span className="" style={{color: "var(--muted-foreground)"}}>Add pagination controls for more results</span>
                    </div>
                )}
            </div>

            {/* Detail Modal */}
            {showDetailModal && selectedLog && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
                    <div className=" rounded-xl border  max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
                        {/* Header */}
                        <div className="flex items-center justify-between p-6 border-b " style={{borderColor: "var(--border)"}}>
                            <div>
                                <h2 className="text-xl font-bold" style={{ color: "var(--foreground)" }}>LLM Call Details</h2>
                                <p className=" text-xs mt-1" style={{color: "var(--muted-foreground)"}}>
                                    {new Date(selectedLog.created_at).toLocaleString()}
                                </p>
                            </div>
                            <button
                                onClick={handleCloseDetail}
                                className="transition-colors hover:text-slate-200" style={{color: "var(--muted-foreground)"}}
                            >
                                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>

                        {/* Content */}
                        <div className="p-6 overflow-y-auto flex-1 space-y-6">
                            {logDetail ? (
                                <>
                                    {/* Summary */}
                                    <div className="grid grid-cols-4 gap-4">
                                        <div className=" rounded-lg p-3" style={{backgroundColor: "var(--surface-base)"}}>
                                            <div className="text-xs  mb-1" style={{color: "var(--muted-foreground)"}}>Model</div>
                                            <div className="text-sm font-mono " style={{color: "var(--muted-foreground)"}}>{logDetail.model_name}</div>
                                        </div>
                                        <div className=" rounded-lg p-3" style={{backgroundColor: "var(--surface-base)"}}>
                                            <div className="text-xs  mb-1" style={{color: "var(--muted-foreground)"}}>Tokens</div>
                                            <div className="text-sm font-mono " style={{color: "var(--muted-foreground)"}}>
                                                {formatTokens(logDetail.total_tokens)}
                                            </div>
                                        </div>
                                        <div className=" rounded-lg p-3" style={{backgroundColor: "var(--surface-base)"}}>
                                            <div className="text-xs  mb-1" style={{color: "var(--muted-foreground)"}}>Duration</div>
                                            <div className="text-sm font-mono " style={{color: "var(--muted-foreground)"}}>
                                                {formatDuration(logDetail.duration_ms)}
                                            </div>
                                        </div>
                                        <div className=" rounded-lg p-3" style={{backgroundColor: "var(--surface-base)"}}>
                                            <div className="text-xs  mb-1" style={{color: "var(--muted-foreground)"}}>Status</div>
                                            <span className={`px-2 py-1 rounded text-xs font-medium border ${getStatusBadgeClass(logDetail.status)}`}>
                                                {logDetail.status}
                                            </span>
                                        </div>
                                    </div>

                                    {/* User Prompt */}
                                    {logDetail.user_prompt && (
                                        <div>
                                            <h3 className="text-sm font-bold  mb-2" style={{color: "var(--muted-foreground)"}}>User Prompt</h3>
                                            <div className=" rounded-lg p-4 text-sm  whitespace-pre-wrap font-mono max-h-60 overflow-y-auto" style={{color: "var(--muted-foreground)", backgroundColor: "var(--surface-base)"}}>
                                                {logDetail.user_prompt}
                                            </div>
                                        </div>
                                    )}

                                    {/* System Prompt */}
                                    {logDetail.system_prompt && (
                                        <div>
                                            <h3 className="text-sm font-bold  mb-2" style={{color: "var(--muted-foreground)"}}>System Prompt</h3>
                                            <div className=" rounded-lg p-4 text-sm  whitespace-pre-wrap font-mono max-h-40 overflow-y-auto" style={{color: "var(--muted-foreground)", backgroundColor: "var(--surface-base)"}}>
                                                {logDetail.system_prompt}
                                            </div>
                                        </div>
                                    )}

                                    {/* Response */}
                                    {logDetail.raw_response && (
                                        <div>
                                            <h3 className="text-sm font-bold  mb-2" style={{color: "var(--muted-foreground)"}}>LLM Response</h3>
                                            <div className=" rounded-lg p-4 text-sm  whitespace-pre-wrap font-mono max-h-60 overflow-y-auto" style={{color: "var(--muted-foreground)", backgroundColor: "var(--surface-base)"}}>
                                                {logDetail.raw_response}
                                            </div>
                                        </div>
                                    )}

                                    {/* Context */}
                                    {logDetail.context && Object.keys(logDetail.context).length > 0 && (
                                        <div>
                                            <h3 className="text-sm font-bold  mb-2" style={{color: "var(--muted-foreground)"}}>Context</h3>
                                            <div className=" rounded-lg p-4 text-sm  font-mono max-h-40 overflow-y-auto" style={{color: "var(--muted-foreground)", backgroundColor: "var(--surface-base)"}}>
                                                <pre>{JSON.stringify(logDetail.context, null, 2)}</pre>
                                            </div>
                                        </div>
                                    )}

                                    {/* Error Details */}
                                    {logDetail.status === "error" && logDetail.error_message && (
                                        <div className="bg-rose-950/50 border border-rose-900/50 rounded-lg p-4">
                                            <h3 className="text-sm font-bold text-rose-400 mb-2">Error</h3>
                                            <p className="text-sm text-rose-300">{logDetail.error_message}</p>
                                            {logDetail.error_details && (
                                                <pre className="mt-2 text-xs text-rose-400">
                                                    {JSON.stringify(logDetail.error_details, null, 2)}
                                                </pre>
                                            )}
                                        </div>
                                    )}

                                    {/* Metadata */}
                                    <div className="grid grid-cols-2 gap-4 text-xs">
                                        <div className=" rounded-lg p-3" style={{backgroundColor: "var(--surface-base)"}}>
                                            <span className="" style={{color: "var(--muted-foreground)"}}>Trace ID: </span>
                                            <span className=" font-mono" style={{color: "var(--muted-foreground)"}}>{logDetail.trace_id || "N/A"}</span>
                                        </div>
                                        <div className=" rounded-lg p-3" style={{backgroundColor: "var(--surface-base)"}}>
                                            <span className="" style={{color: "var(--muted-foreground)"}}>UI Endpoint: </span>
                                            <span className=" font-mono" style={{color: "var(--muted-foreground)"}}>{logDetail.ui_endpoint || "N/A"}</span>
                                        </div>
                                        <div className=" rounded-lg p-3" style={{backgroundColor: "var(--surface-base)"}}>
                                            <span className="" style={{color: "var(--muted-foreground)"}}>Provider: </span>
                                            <span className="" style={{color: "var(--muted-foreground)"}}>{logDetail.provider || "N/A"}</span>
                                        </div>
                                        <div className=" rounded-lg p-3" style={{backgroundColor: "var(--surface-base)"}}>
                                            <span className="" style={{color: "var(--muted-foreground)"}}>Call Index: </span>
                                            <span className="" style={{color: "var(--muted-foreground)"}}>{logDetail.call_index}</span>
                                        </div>
                                    </div>
                                </>
                            ) : (
                                <div className="flex items-center justify-center py-20">
                                    <div className="w-6 h-6 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
                                    <span className="ml-3  text-sm" style={{color: "var(--muted-foreground)"}}>Loading details...</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
