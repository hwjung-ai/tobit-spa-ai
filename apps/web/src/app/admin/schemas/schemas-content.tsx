"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import SchemaTable from "@/components/admin/SchemaTable";
import CreateSchemaModal from "@/components/admin/CreateSchemaModal";
import SchemaScanPanel from "@/components/admin/SchemaScanPanel";
import SchemaViewerPanel from "@/components/admin/SchemaViewerPanel";
import { fetchApi } from "@/lib/adminUtils";

interface SchemaAsset {
    asset_id: string;
    name: string;
    description?: string;
    status: string;
    version: number;
    content?: {
        source_ref?: string;
        catalog?: {
            tables?: any[];
            scan_status?: string;
            last_scanned_at?: string;
            database_type?: string;
        };
    };
    created_at?: string;
    updated_at?: string;
}

export default function SchemasContent() {
    const [selectedSchema, setSelectedSchema] = useState<SchemaAsset | null>(null);
    const [showCreateModal, setShowCreateModal] = useState(false);

    const { data: schemasData, isLoading, refetch } = useQuery({
        queryKey: ["admin-schemas"],
        queryFn: async () => {
            const response = await fetchApi("/asset-registry/catalogs");
            return response.data?.assets || [];
        },
        staleTime: 5 * 60 * 1000,
    });

    const schemas = schemasData || [];

    return (
        <div className="space-y-4">
            {/* Info Banner */}
            <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-4">
                <h3 className="font-semibold text-slate-200 mb-2">🔍 Database Schemas</h3>
                <p className="text-sm text-slate-400">
                    자동으로 데이터베이스 스키마를 스캔하여 메타데이터를 저장합니다.
                    Tool이 정확한 SQL 쿼리를 생성할 때 스키마 정보(테이블, 컬럼, 타입)를 참고합니다.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Left Side: Schema List */}
                <div className="lg:col-span-1">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold text-slate-200">Schemas</h2>
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="px-3 py-2 bg-sky-600 hover:bg-sky-500 text-white text-sm rounded-lg transition-colors font-medium"
                        >
                            + New Schema
                        </button>
                    </div>

                    {isLoading ? (
                        <div className="text-center py-4 text-slate-500">Loading...</div>
                    ) : (
                        <SchemaTable
                            schemas={schemas}
                            selectedSchema={selectedSchema}
                            onSelect={setSelectedSchema}
                            onRefresh={refetch}
                        />
                    )}
                </div>

                {/* Right Side: Schema Details */}
                <div className="lg:col-span-2 space-y-4">
                    {selectedSchema ? (
                        <>
                            {/* Schema Info */}
                            <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-4">
                                <h3 className="font-semibold text-lg mb-3 text-slate-200">{selectedSchema.name}</h3>
                                {selectedSchema.description && (
                                    <p className="text-sm text-slate-400 mb-2">{selectedSchema.description}</p>
                                )}
                                <div className="text-sm text-slate-400 space-y-1">
                                    <div>
                                        <span className="font-medium text-slate-300">ID:</span>{" "}
                                        <span className="text-slate-500 font-mono text-xs">{selectedSchema.asset_id}</span>
                                    </div>
                                    <div>
                                        <span className="font-medium text-slate-300">Status:</span>{" "}
                                        <span
                                            className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                                                selectedSchema.status === "published"
                                                    ? "bg-green-900/50 text-green-300 border border-green-800"
                                                    : "bg-slate-800/50 text-slate-300 border border-slate-700"
                                            }`}
                                        >
                                            {selectedSchema.status}
                                        </span>
                                    </div>
                                    <div>
                                        <span className="font-medium text-slate-300">Source:</span>{" "}
                                        <span className="text-slate-400">{selectedSchema.content?.source_ref || "Not configured"}</span>
                                    </div>
                                    {selectedSchema.content?.catalog?.database_type && (
                                        <div>
                                            <span className="font-medium text-slate-300">Database Type:</span>{" "}
                                            <span className="text-slate-400 capitalize">{selectedSchema.content.catalog.database_type}</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Scan Panel */}
                            <SchemaScanPanel schema={selectedSchema} onScanComplete={refetch} />

                            {/* Schema Viewer */}
                            <SchemaViewerPanel schema={selectedSchema} onRefresh={refetch} />
                        </>
                    ) : (
                        <div className="bg-slate-900/40 border border-slate-800 rounded-lg p-8 text-center">
                            <p className="text-slate-400">Select a schema to view details</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Create Modal */}
            {showCreateModal && (
                <CreateSchemaModal
                    onClose={() => setShowCreateModal(false)}
                    onSave={() => {
                        setShowCreateModal(false);
                        refetch();
                    }}
                />
            )}
        </div>
    );
}
