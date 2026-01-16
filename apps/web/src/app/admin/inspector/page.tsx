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
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Search Console */}
            <div className="bg-slate-900/40 rounded-2xl border border-slate-800 p-6 backdrop-blur-sm shadow-2xl">
                <div className="flex flex-col gap-2">
                    <label className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] ml-1 mb-1">Audit Stream Lookup</label>
                    <div className="flex gap-4">
                        <div className="relative flex-1 group">
                            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                <svg className="h-4 w-4 text-slate-600 transition-colors group-focus-within:text-sky-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                </svg>
                            </div>
                            <input
                                type="text"
                                value={traceId}
                                onChange={(e) => setTraceId(e.target.value)}
                                onKeyDown={(e) => e.key === "Enter" && handleSearch(traceId)}
                                placeholder="UUID Trace Identifier (e.g. 550e8400-e29b-...)"
                                className="w-full pl-10 pr-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-700 text-sm focus:outline-none focus:border-sky-500/50 transition-all font-mono"
                            />
                        </div>
                        <button
                            onClick={() => handleSearch(traceId)}
                            disabled={isLoading}
                            className="px-8 py-3 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl transition-all font-bold text-xs uppercase tracking-[0.2em] shadow-lg shadow-sky-900/20 active:scale-95"
                        >
                            {isLoading ? "Tracing..." : "Search"}
                        </button>
                    </div>
                </div>
            </div>

            {error && (
                <div className="animate-in slide-in-from-top-2 duration-300">
                    <ValidationAlert errors={[error]} onClose={() => setError(null)} />
                </div>
            )}

            {isLoading ? (
                <div className="flex flex-col items-center justify-center py-20 gap-4">
                    <div className="w-10 h-10 border-2 border-sky-500/20 border-t-sky-500 rounded-full animate-spin"></div>
                    <p className="text-slate-500 text-[10px] font-bold uppercase tracking-[0.25em]">Scanning Distributed Logs...</p>
                </div>
            ) : logs.length > 0 ? (
                <div className="space-y-6">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800 flex flex-col justify-between">
                            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-3">Hierarchy Path</p>
                            <div className="space-y-2.5">
                                <div className="flex items-center gap-2">
                                    <span className="text-[9px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700/50 font-bold uppercase">Trace</span>
                                    <span className="text-slate-100 font-mono text-xs truncate">{logs[0].trace_id}</span>
                                </div>
                                {parentTraceId ? (
                                    <div className="flex items-center gap-2">
                                        <span className="text-[9px] text-sky-400 bg-sky-950/30 px-1.5 py-0.5 rounded border border-sky-900/30 font-bold uppercase">Parent</span>
                                        <span className="text-sky-300 font-mono text-xs truncate">{parentTraceId}</span>
                                        <button
                                            onClick={handleViewParent}
                                            className="text-[9px] text-sky-500 hover:text-white font-bold uppercase transition-colors ml-auto bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20 hover:bg-sky-500/20"
                                        >
                                            Up ↑
                                        </button>
                                    </div>
                                ) : (
                                    <div className="text-[10px] text-slate-600 italic px-1 opacity-50">Root Transaction Entry</div>
                                )}
                            </div>
                        </div>

                        <div className="bg-slate-900/60 p-5 rounded-xl border border-slate-800 flex flex-col items-center justify-center text-center">
                            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-bold mb-1">Captured Events</p>
                            <div className="text-3xl font-bold text-white tracking-tighter">{logs.length}</div>
                            <p className="text-[9px] text-slate-600 font-bold uppercase tracking-widest mt-1 opacity-50">Operations indexed</p>
                        </div>
                    </div>

                    <div className="bg-slate-900/40 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
                        <div className="p-3 bg-slate-950/20 border-b border-slate-800/50 flex items-center justify-between">
                            <h3 className="font-bold text-slate-300 text-[10px] uppercase tracking-widest px-2">Flow Reconstruction</h3>
                            <div className="text-[9px] text-slate-600 font-mono italic px-2">ORDERED DESC</div>
                        </div>
                        <AuditLogTable logs={logs} onViewDetails={setSelectedLog} />
                    </div>
                </div>
            ) : !error && (
                <div className="flex flex-col items-center justify-center py-32 text-slate-700">
                    <div className="w-16 h-16 rounded-3xl bg-slate-900 border border-slate-800 flex items-center justify-center mb-6 shadow-inner">
                        <svg className="w-8 h-8 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                    </div>
                    <p className="text-xs font-bold uppercase tracking-[0.2em] opacity-50">Awaiting Search Input</p>
                    <p className="text-[10px] opacity-30 mt-1 italic leading-relaxed text-center px-12">Search results will be displayed as a chronological stream of audited system events and state changes.</p>
                </div>
            )}

            {selectedLog && (
                <AuditLogDetailsModal log={selectedLog} onClose={() => setSelectedLog(null)} />
            )}
        </div>
    );
}
