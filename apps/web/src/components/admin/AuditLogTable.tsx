"use client";


import { AuditLog, formatTimestamp } from "../../lib/adminUtils";

interface AuditLogTableProps {
    logs: AuditLog[];
    onViewDetails?: (log: AuditLog) => void;
}

export default function AuditLogTable({ logs, onViewDetails }: AuditLogTableProps) {
    if (logs.length === 0) {
        return (
            <div className="text-center py-8 text-slate-400">
                No audit logs found
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-slate-800">
                        <th className="text-left py-3 px-4 text-slate-500 font-medium">Time</th>
                        <th className="text-left py-3 px-4 text-slate-500 font-medium">Resource</th>
                        <th className="text-left py-3 px-4 text-slate-500 font-medium">Action</th>
                        <th className="text-left py-3 px-4 text-slate-500 font-medium">Actor</th>
                        <th className="text-left py-3 px-4 text-slate-500 font-medium">Changes</th>
                        <th className="text-left py-3 px-4 text-slate-500 font-medium">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {logs.map((log) => (
                        <tr
                            key={log.audit_id}
                            className="border-b border-slate-800 hover:bg-slate-900/50 transition-colors"
                        >
                            <td className="py-3 px-4 text-slate-300">
                                {formatTimestamp(log.created_at)}
                            </td>
                            <td className="py-3 px-4 text-slate-300">
                                <span className="font-mono text-xs">
                                    {log.resource_type}:{log.resource_id.substring(0, 8)}
                                </span>
                            </td>
                            <td className="py-3 px-4">
                                <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${log.action === "create" ? "bg-green-950/50 text-green-300" :
                                        log.action === "update" ? "bg-blue-950/50 text-blue-300" :
                                            log.action === "publish" ? "bg-purple-950/50 text-purple-300" :
                                                log.action === "rollback" ? "bg-yellow-950/50 text-yellow-300" :
                                                    "bg-slate-800 text-slate-300"
                                    }`}>
                                    {log.action}
                                </span>
                            </td>
                            <td className="py-3 px-4 text-slate-300">{log.actor}</td>
                            <td className="py-3 px-4 text-slate-400 text-xs">
                                {Object.keys(log.changes).length} field(s)
                            </td>
                            <td className="py-3 px-4">
                                {onViewDetails && (
                                    <button
                                        onClick={() => onViewDetails(log)}
                                        className="text-sky-400 hover:text-sky-300 text-xs transition-colors"
                                    >
                                        Details
                                    </button>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

interface AuditLogDetailsModalProps {
    log: AuditLog;
    onClose: () => void;
}

export function AuditLogDetailsModal({ log, onClose }: AuditLogDetailsModalProps) {
    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
            <div className="bg-slate-900 rounded-lg border border-slate-800 max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col">
                <div className="flex items-center justify-between p-4 border-b border-slate-800">
                    <h2 className="text-lg font-semibold text-white">Audit Log Details</h2>
                    <button
                        onClick={onClose}
                        className="text-slate-400 hover:text-white transition-colors"
                    >
                        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="p-4 overflow-y-auto custom-scrollbar">
                    <div className="space-y-4">
                        <div>
                            <label className="text-xs text-slate-500 uppercase tracking-wider">Audit ID</label>
                            <p className="text-slate-300 font-mono text-sm mt-1">{log.audit_id}</p>
                        </div>

                        <div>
                            <label className="text-xs text-slate-500 uppercase tracking-wider">Trace ID</label>
                            <p className="text-slate-300 font-mono text-sm mt-1">{log.trace_id}</p>
                        </div>

                        {log.parent_trace_id && (
                            <div>
                                <label className="text-xs text-slate-500 uppercase tracking-wider">Parent Trace ID</label>
                                <p className="text-slate-300 font-mono text-sm mt-1">{log.parent_trace_id}</p>
                            </div>
                        )}

                        <div>
                            <label className="text-xs text-slate-500 uppercase tracking-wider">Resource</label>
                            <p className="text-slate-300 text-sm mt-1">{log.resource_type}:{log.resource_id}</p>
                        </div>

                        <div>
                            <label className="text-xs text-slate-500 uppercase tracking-wider">Action</label>
                            <p className="text-slate-300 text-sm mt-1">{log.action}</p>
                        </div>

                        <div>
                            <label className="text-xs text-slate-500 uppercase tracking-wider">Actor</label>
                            <p className="text-slate-300 text-sm mt-1">{log.actor}</p>
                        </div>

                        <div>
                            <label className="text-xs text-slate-500 uppercase tracking-wider">Time</label>
                            <p className="text-slate-300 text-sm mt-1">{formatTimestamp(log.created_at)}</p>
                        </div>

                        <div>
                            <label className="text-xs text-slate-500 uppercase tracking-wider">Changes</label>
                            <pre className="mt-1 p-3 bg-slate-950 rounded border border-slate-800 text-xs text-slate-300 overflow-x-auto">
                                {JSON.stringify(log.changes, null, 2)}
                            </pre>
                        </div>

                        {log.old_values && (
                            <div>
                                <label className="text-xs text-slate-500 uppercase tracking-wider">Old Values</label>
                                <pre className="mt-1 p-3 bg-slate-950 rounded border border-slate-800 text-xs text-slate-300 overflow-x-auto">
                                    {JSON.stringify(log.old_values, null, 2)}
                                </pre>
                            </div>
                        )}

                        {log.new_values && (
                            <div>
                                <label className="text-xs text-slate-500 uppercase tracking-wider">New Values</label>
                                <pre className="mt-1 p-3 bg-slate-950 rounded border border-slate-800 text-xs text-slate-300 overflow-x-auto">
                                    {JSON.stringify(log.new_values, null, 2)}
                                </pre>
                            </div>
                        )}

                        {log.audit_metadata && (
                            <div>
                                <label className="text-xs text-slate-500 uppercase tracking-wider">Metadata</label>
                                <pre className="mt-1 p-3 bg-slate-950 rounded border border-slate-800 text-xs text-slate-300 overflow-x-auto">
                                    {JSON.stringify(log.audit_metadata, null, 2)}
                                </pre>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
