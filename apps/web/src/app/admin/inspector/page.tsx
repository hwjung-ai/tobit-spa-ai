"use client";

import { useState } from "react";
import { AuditLog, fetchApi } from "../../../lib/adminUtils";
import AuditLogTable, { AuditLogDetailsModal } from "../../../components/admin/AuditLogTable";
import ValidationAlert from "../../../components/admin/ValidationAlert";

export default function InspectorPage() {
    const [traceId, setTraceId] = useState("");
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [parentTraceId, setParentTraceId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

    const handleSearch = async (searchTraceId: string) => {
        if (!searchTraceId.trim()) {
            setError("Please provide a Trace ID to begin the search.");
            return;
        }

        setIsLoading(true);
        setError(null);
        setLogs([]);
        setParentTraceId(null);

        try {
            const response = await fetchApi<{
                trace_id: string;
                audit_logs: AuditLog[];
                count: number;
            }>(`/audit-log/by-trace/${encodeURIComponent(searchTraceId)}`);

            if (response.data.audit_logs.length === 0) {
                setError(`No audit records found for Trace ID: ${searchTraceId}`);
            } else {
                setLogs(response.data.audit_logs);
                // Extract parent trace if any record has it
                const firstParent = response.data.audit_logs.find(log => log.parent_trace_id);
                if (firstParent) {
                    setParentTraceId(firstParent.parent_trace_id);
                }
            }
        } catch (err: any) {
            setError(err.message || "An unexpected error occurred while fetching audit logs.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleViewParent = () => {
        if (parentTraceId) {
            setTraceId(parentTraceId);
            handleSearch(parentTraceId);
        }
    };

    return (
        <div className="p-6">
            <div className="max-w-7xl mx-auto">
                <div className="mb-8">
                    <h1 className="text-3xl font-bold text-white mb-2 tracking-tight">Trace Inspector</h1>
                    <p className="text-slate-400 text-sm max-w-2xl leading-relaxed">
                        Audit logs provide high-fidelity traceability for all system operations.
                        Enter a <strong>Trace ID</strong> to reconstruct a specific operation flow.
                    </p>
                </div>

                {/* Search Panel */}
                <div className="bg-slate-900/40 rounded-2xl border border-slate-800 p-8 mb-8 backdrop-blur-sm shadow-2xl">
                    <div className="flex flex-col gap-2 mb-6">
                        <label className="text-xs font-bold text-slate-500 uppercase tracking-[0.2em] ml-1">Lookup Source</label>
                        <div className="flex gap-4">
                            <div className="relative flex-1 group">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <svg className="h-5 w-5 text-slate-600 transition-colors group-focus-within:text-sky-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                    </svg>
                                </div>
                                <input
                                    type="text"
                                    value={traceId}
                                    onChange={(e) => setTraceId(e.target.value)}
                                    onKeyDown={(e) => e.key === "Enter" && handleSearch(traceId)}
                                    placeholder="Enter UUID Trace ID (e.g. 550e8400-e29b-...)"
                                    className="w-full pl-11 pr-4 py-3 bg-slate-950 border border-slate-700/50 rounded-xl text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500/50 focus:ring-4 focus:ring-sky-500/5 transition-all"
                                />
                            </div>
                            <button
                                onClick={() => handleSearch(traceId)}
                                disabled={isLoading}
                                className="px-8 py-3 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl transition-all font-bold shadow-lg shadow-sky-900/20 active:scale-95"
                            >
                                {isLoading ? "Analyzing..." : "Trace Now"}
                            </button>
                        </div>
                    </div>

                    <div className="flex gap-2 text-xs text-slate-500">
                        <span className="px-2 py-1 bg-slate-800/50 rounded flex items-center gap-1 border border-slate-700/30">
                            <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                            Real-time indexing active
                        </span>
                        <span className="px-2 py-1 bg-slate-800/50 rounded border border-slate-700/30">
                            Retention: 90 Days
                        </span>
                    </div>
                </div>

                {/* Feedback Area */}
                {error && (
                    <div className="mb-8 animate-in slide-in-from-top-2 duration-300">
                        <ValidationAlert errors={[error]} onClose={() => setError(null)} />
                    </div>
                )}

                {/* Results Area */}
                {isLoading ? (
                    <div className="flex flex-col items-center justify-center py-20 gap-4 opacity-50">
                        <div className="w-12 h-12 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
                        <p className="text-slate-500 font-medium">Reconstructing operation sequence...</p>
                    </div>
                ) : logs.length > 0 ? (
                    <div className="space-y-8 animate-in fade-in duration-500">
                        {/* Trace Summary Board */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div className="bg-slate-900/60 p-6 rounded-xl border border-slate-800">
                                <p className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-3">Trace Hierarchy</p>
                                <div className="space-y-3">
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded">ID</span>
                                        <span className="text-slate-100 font-mono text-sm truncate">{logs[0].trace_id}</span>
                                    </div>
                                    {parentTraceId ? (
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs text-sky-400/50 bg-sky-950/30 px-2 py-0.5 rounded border border-sky-900/30">Parent</span>
                                            <span className="text-sky-300 font-mono text-sm truncate">{parentTraceId}</span>
                                            <button
                                                onClick={handleViewParent}
                                                className="text-[10px] text-sky-500 hover:text-sky-300 font-bold uppercase transition-colors ml-auto"
                                            >
                                                Navigate Up →
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="text-xs text-slate-600 italic px-2">Root Operation (No Parent)</div>
                                    )}
                                </div>
                            </div>

                            <div className="bg-slate-900/60 p-6 rounded-xl border border-slate-800 flex flex-col justify-center text-center">
                                <p className="text-xs text-slate-500 uppercase tracking-widest font-bold mb-2">Events Captured</p>
                                <div className="text-4xl font-bold text-white mb-1">{logs.length}</div>
                                <p className="text-[10px] text-slate-600 font-medium">Chronological sequence</p>
                            </div>
                        </div>

                        {/* Audit Logs Table Panel */}
                        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
                            <div className="p-4 border-b border-slate-800 bg-slate-900/50 flex items-center justify-between">
                                <h3 className="font-bold text-white text-sm px-2">Operation Timeline</h3>
                                <div className="text-[10px] text-slate-500 font-mono italic">Sorted by chronological entry DESC</div>
                            </div>
                            <AuditLogTable logs={logs} onViewDetails={setSelectedLog} />
                        </div>
                    </div>
                ) : !error && (
                    <div className="flex flex-col items-center justify-center py-32 text-slate-600">
                        <div className="w-16 h-16 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center mb-6">
                            <svg className="w-8 h-8 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                            </svg>
                        </div>
                        <p className="text-sm font-medium">Ready for investigation</p>
                        <p className="text-xs opacity-60 mt-1 italic">Scan a trace ID to populate this dashboard</p>
                    </div>
                )}
            </div>

            {/* Details Modal (Drilled down view) */}
            {selectedLog && (
                <AuditLogDetailsModal log={selectedLog} onClose={() => setSelectedLog(null)} />
            )}
        </div>
    );
}
