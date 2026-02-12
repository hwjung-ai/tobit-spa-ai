"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import CatalogTable from "@/components/admin/CatalogTable";
import CreateCatalogModal from "@/components/admin/CreateCatalogModal";
import CatalogScanPanel from "@/components/admin/CatalogScanPanel";
import CatalogViewerPanel from "@/components/admin/CatalogViewerPanel";
import { fetchApi } from "@/lib/adminUtils";

interface CatalogAsset {
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
    };
  };
  created_at?: string;
  updated_at?: string;
}

export default function CatalogsContent() {
  const [selectedCatalog, setSelectedCatalog] = useState<CatalogAsset | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);

  const { data: catalogsData, isLoading, refetch } = useQuery({
    queryKey: ["admin-catalogs"],
    queryFn: async () => {
      const response = await fetchApi<{ assets: CatalogAsset[] }>("/asset-registry/catalogs");
      return response.data?.assets || [];
    },
    staleTime: 5 * 60 * 1000,
  });

  const catalogs = catalogsData || [];

  // Demo data - 실제 환경에서는 제거
  const demoMode = catalogs.length === 0;
  const demoCatalogs: CatalogAsset[] = demoMode ? [
    {
      asset_id: "demo-postgres-schema",
      name: "PostgreSQL DB Schema",
      description: "Main PostgreSQL database table definitions and relationships",
      status: "published",
      version: 1,
      content: {
        source_ref: "primary_postgres",
        catalog: {
          tables: [
            { name: "users", columns: 8 },
            { name: "orders", columns: 6 },
            { name: "products", columns: 10 },
          ],
          scan_status: "completed",
          last_scanned_at: new Date().toISOString(),
        },
      },
      created_at: new Date().toISOString(),
    },
    {
      asset_id: "demo-neo4j-schema",
      name: "Neo4j Graph Schema",
      description: "Graph database nodes and relationships for knowledge graph",
      status: "published",
      version: 1,
      content: {
        source_ref: "primary_neo4j",
        catalog: {
          tables: [
            { name: "Equipment", columns: 5 },
            { name: "Maintenance", columns: 4 },
            { name: "Technician", columns: 6 },
          ],
          scan_status: "completed",
          last_scanned_at: new Date().toISOString(),
        },
      },
      created_at: new Date().toISOString(),
    },
  ] : [];

  const displayCatalogs = demoMode ? demoCatalogs : catalogs;

  return (
    <div className="space-y-4">
      {/* Info Banner */}
      <div className="border border-slate-200 rounded-lg bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
        <h3 className="mb-2 font-semibold text-slate-600 dark:text-slate-400">📊 Database Catalogs</h3>
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Database schema 정보를 자동으로 스캔하고 저장합니다.
          Tool이 SQL 쿼리를 생성할 때 schema 정보를 참고하여 정확한 테이블/컬럼명을 사용합니다.
          {demoMode && " (데모 데이터 표시 중)"}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      {/* Left Side: Catalog List */}
      <div className="lg:col-span-1">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-600 dark:text-slate-400">Catalogs</h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className="rounded-lg bg-sky-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-sky-500"
          >
            + New Catalog
          </button>
        </div>

        {isLoading ? (
          <div className="py-4 text-center text-slate-600 dark:text-slate-400">Loading...</div>
        ) : (
          <CatalogTable
            catalogs={displayCatalogs}
            selectedCatalog={selectedCatalog}
            onSelect={setSelectedCatalog}
            onRefresh={refetch}
          />
        )}
      </div>

      {/* Right Side: Schema Details */}
      <div className="space-y-4 lg:col-span-2">
        {selectedCatalog ? (
          <>
            {/* Catalog Info */}
            <div className="border border-slate-200 rounded-lg bg-white p-4 dark:border-slate-700 dark:bg-slate-900">
              <h3 className="mb-3 text-lg font-semibold text-slate-600 dark:text-slate-400">{selectedCatalog.name}</h3>
              {selectedCatalog.description && (
                <p className="mb-2 text-sm text-slate-600 dark:text-slate-400">{selectedCatalog.description}</p>
              )}
              <div className="space-y-1 text-sm text-slate-600 dark:text-slate-400">
                <div>
                  <span className="font-medium text-slate-600 dark:text-slate-400">ID:</span> <span className="font-mono text-slate-600 dark:text-slate-400">{selectedCatalog.asset_id}</span>
                </div>
                <div>
                  <span className="font-medium text-slate-600 dark:text-slate-400">Status:</span>{" "}
                  <span className={`inline-block rounded border px-2 py-1 text-xs font-medium ${
                    selectedCatalog.status === "published"
                      ? "border-green-800 bg-green-900/50 text-green-300"
                      : "border-slate-300 bg-slate-100/50 text-slate-500"
                  }`}>
                    {selectedCatalog.status}
                  </span>
                </div>
                <div>
                  <span className="font-medium text-slate-600 dark:text-slate-400">Source:</span>{" "}
                  <span className="text-slate-600 dark:text-slate-400">{selectedCatalog.content?.source_ref || "Not configured"}</span>
                </div>
              </div>
            </div>

            {/* Scan Panel */}
            <CatalogScanPanel schema={selectedCatalog} onScanComplete={() => { void refetch(); }} />

            {/* Catalog Viewer */}
            <CatalogViewerPanel schema={selectedCatalog} onRefresh={() => { void refetch(); }} />
          </>
        ) : (
          <div className="border border-slate-200 rounded-lg bg-white p-8 text-center dark:border-slate-700 dark:bg-slate-900">
            <p className="text-slate-600 dark:text-slate-400">Select a catalog to view details</p>
          </div>
        )}
      </div>
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <CreateCatalogModal
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
