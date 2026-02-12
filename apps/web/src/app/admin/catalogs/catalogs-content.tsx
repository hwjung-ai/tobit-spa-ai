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
      <div className=" border  rounded-lg p-4" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
        <h3 className="font-semibold  mb-2" style={{color: "var(--foreground-secondary)"}}>📊 Database Catalogs</h3>
        <p className="text-sm " style={{color: "var(--muted-foreground)"}}>
          Database schema 정보를 자동으로 스캔하고 저장합니다.
          Tool이 SQL 쿼리를 생성할 때 schema 정보를 참고하여 정확한 테이블/컬럼명을 사용합니다.
          {demoMode && " (데모 데이터 표시 중)"}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left Side: Catalog List */}
      <div className="lg:col-span-1">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold " style={{color: "var(--foreground-secondary)"}}>Catalogs</h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3 py-2 bg-sky-600 hover:bg-sky-500 text-white text-sm rounded-lg transition-colors font-medium"
          >
            + New Catalog
          </button>
        </div>

        {isLoading ? (
          <div className="text-center py-4 " style={{color: "var(--muted-foreground)"}}>Loading...</div>
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
      <div className="lg:col-span-2 space-y-4">
        {selectedCatalog ? (
          <>
            {/* Catalog Info */}
            <div className=" border  rounded-lg p-4" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
              <h3 className="font-semibold text-lg mb-3 " style={{color: "var(--foreground-secondary)"}}>{selectedCatalog.name}</h3>
              {selectedCatalog.description && (
                <p className="text-sm  mb-2" style={{color: "var(--muted-foreground)"}}>{selectedCatalog.description}</p>
              )}
              <div className="text-sm  space-y-1" style={{color: "var(--muted-foreground)"}}>
                <div>
                  <span className="font-medium " style={{color: "var(--foreground-secondary)"}}>ID:</span> <span className=" font-mono" style={{color: "var(--muted-foreground)"}}>{selectedCatalog.asset_id}</span>
                </div>
                <div>
                  <span className="font-medium " style={{color: "var(--foreground-secondary)"}}>Status:</span>{" "}
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                    selectedCatalog.status === "published"
                      ? "bg-green-900/50 text-green-300 border border-green-800"
                      : "bg-[var(--surface-elevated)]/50 text-[var(--foreground-secondary)] border border-[var(--border)]"
                  }`}>
                    {selectedCatalog.status}
                  </span>
                </div>
                <div>
                  <span className="font-medium " style={{color: "var(--foreground-secondary)"}}>Source:</span>{" "}
                  <span className="" style={{color: "var(--muted-foreground)"}}>{selectedCatalog.content?.source_ref || "Not configured"}</span>
                </div>
              </div>
            </div>

            {/* Scan Panel */}
            <CatalogScanPanel schema={selectedCatalog} onScanComplete={() => { void refetch(); }} />

            {/* Catalog Viewer */}
            <CatalogViewerPanel schema={selectedCatalog} onRefresh={() => { void refetch(); }} />
          </>
        ) : (
          <div className=" border  rounded-lg p-8 text-center" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
            <p className="" style={{color: "var(--muted-foreground)"}}>Select a catalog to view details</p>
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
