"use client";


import { AuditLog, formatTimestamp } from "../../lib/adminUtils";

interface AuditLogTableProps {
    logs: AuditLog[];
    onViewDetails?: (log: AuditLog) => void;
}

export default function AuditLogTable({ logs, onViewDetails }: AuditLogTableProps) {
    if (logs.length === 0) {
        return (
            <div className="text-center py-8 text-muted-foreground">
                No audit logs found
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-variant">
                        <th className="text-left py-3 px-4 font-medium min-w-[180px] text-muted-foreground">Time</th>
                        <th className="text-left py-3 px-4 font-medium text-muted-foreground">Resource</th>
                        <th className="text-left py-3 px-4 font-medium text-muted-foreground">Action</th>
                        <th className="text-left py-3 px-4 font-medium text-muted-foreground">Actor</th>
                        <th className="text-left py-3 px-4 font-medium text-muted-foreground">Changes</th>
                        <th className="text-left py-3 px-4 font-medium text-muted-foreground">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {logs.map((log) => (
                        <tr
                            key={log.audit_id}
                            className="border-b border-variant hover:bg-surface-overlay transition-colors"
                        >
                            <td className="py-3 px-4 whitespace-nowrap min-w-[180px] text-foreground">
                                {formatTimestamp(log.created_at)}
                            </td>
                            <td className="py-3 px-4 text-foreground">
                                <span className="font-mono text-xs">
                                    {log.resource_type}:{log.resource_id.substring(0, 8)}
                                </span>
                            </td>
                            <td className="py-3 px-4">
                                <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                                    log.action === "create" ? "bg-green-950/50 text-green-300" :
                                    log.action === "update" ? "bg-sky-950/50 text-sky-300" :
                                    log.action === "publish" ? "bg-purple-950/50 text-purple-300" :
                                    log.action === "rollback" ? "bg-yellow-950/50 text-yellow-300" :
                                        " "
                                } bg-surface-elevated text-foreground`}>
                                    {log.action}
                                </span>
                            </td>
                            <td className="py-3 px-4 text-foreground">{log.actor}</td>
                            <td className="py-3 px-4 text-xs text-muted-foreground">
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
            <div className="rounded-lg border max-w-3xl w-full max-h-[80vh] overflow-hidden flex flex-col border-variant bg-surface-base">
                <div className="flex items-center justify-between p-4 border-b border-variant">
                    <h2 className="text-lg font-semibold text-foreground">Audit Log Details</h2>
                    <button
                        onClick={onClose}
                        className="hover:text-foreground transition-colors text-muted-foreground"
                    >
                        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="p-4 overflow-y-auto custom-scrollbar">
                    <div className="space-y-4">
                        <div>
                            <label className="text-xs uppercase tracking-wider text-muted-foreground">Audit ID</label>
                            <p className="font-mono text-sm mt-1 text-foreground">{log.audit_id}</p>
                        </div>

                        <div>
                            <label className="text-xs uppercase tracking-wider text-muted-foreground">Trace ID</label>
                            <p className="font-mono text-sm mt-1 text-foreground">{log.trace_id}</p>
                        </div>

                        {log.parent_trace_id && (
                            <div>
                                <label className="text-xs uppercase tracking-wider text-muted-foreground">Parent Trace ID</label>
                                <p className="font-mono text-sm mt-1 text-foreground">{log.parent_trace_id}</p>
                            </div>
                        )}

                        <div>
                            <label className="text-xs uppercase tracking-wider text-muted-foreground">Resource</label>
                            <p className="text-sm mt-1 text-foreground">{log.resource_type}:{log.resource_id}</p>
                        </div>

                        <div>
                            <label className="text-xs uppercase tracking-wider text-muted-foreground">Action</label>
                            <p className="text-sm mt-1 text-foreground">{log.action}</p>
                        </div>

                        <div>
                            <label className="text-xs uppercase tracking-wider text-muted-foreground">Actor</label>
                            <p className="text-sm mt-1 text-foreground">{log.actor}</p>
                        </div>

                        <div>
                            <label className="text-xs uppercase tracking-wider text-muted-foreground">Time</label>
                            <p className="text-sm mt-1 text-foreground">{formatTimestamp(log.created_at)}</p>
                        </div>

                        <div>
                            <label className="text-xs uppercase tracking-wider text-muted-foreground">Changes</label>
                            <pre className="mt-1 p-3 rounded border text-xs overflow-x-auto border-variant text-foreground bg-surface-base">
                                {JSON.stringify(log.changes, null, 2)}
                            </pre>
                        </div>

                        {log.old_values && (
                            <div>
                                <label className="text-xs uppercase tracking-wider text-muted-foreground">Old Values</label>
                                <pre className="mt-1 p-3 rounded border text-xs overflow-x-auto border-variant text-foreground bg-surface-base">
                                    {JSON.stringify(log.old_values, null, 2)}
                                </pre>
                            </div>
                        )}

                        {log.new_values && (
                            <div>
                                <label className="text-xs uppercase tracking-wider text-muted-foreground">New Values</label>
                                <pre className="mt-1 p-3 rounded border text-xs overflow-x-auto border-variant text-foreground bg-surface-base">
                                    {JSON.stringify(log.new_values, null, 2)}
                                </pre>
                            </div>
                        )}

                        {log.audit_metadata && (
                            <div>
                                <label className="text-xs uppercase tracking-wider text-muted-foreground">Metadata</label>
                                <pre className="mt-1 p-3 rounded border text-xs overflow-x-auto border-variant text-foreground bg-surface-base">
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
