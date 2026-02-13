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
  const [statusFilter, setStatusFilter] = useState<"all" | "draft" | "published">("all");
  const [showCreateModal, setShowCreateModal] = useState(false);

  const {
    data: catalogsData,
    isLoading,
    refetch,
  } = useQuery({
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
  const demoCatalogs: CatalogAsset[] = demoMode
    ? [
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
      ]
    : [];

  const displayCatalogs = demoMode ? demoCatalogs : catalogs;
  const filteredCatalogs =
    statusFilter === "all"
      ? displayCatalogs
      : displayCatalogs.filter((catalog) => catalog.status === statusFilter);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between rounded-2xl border border-border bg-surface-elevated p-4 backdrop-blur-sm">
        <div className="min-w-[180px]">
          <label className="form-field-label">Status</label>
          <select
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(event.target.value as "all" | "draft" | "published")
            }
            className="input-container"
          >
            <option value="all">Any Status</option>
            <option value="draft">Draft Only</option>
            <option value="published">Published Only</option>
          </select>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => refetch()}
            className="text-label-sm font-bold uppercase tracking-widest text-muted-standard hover:text-primary"
          >
            Refresh
          </button>
          <div className="h-6 w-px bg-border" />
          <button onClick={() => setShowCreateModal(true)} className="btn-primary">
            + New Catalog
          </button>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left Side: Catalog List */}
        <div className="lg:col-span-1">
          {isLoading ? (
            <div className="py-4 text-center text-muted-standard">Loading...</div>
          ) : (
            <CatalogTable
              catalogs={filteredCatalogs}
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
              <div className="ui-subbox">
                <h3 className="mb-3 text-lg font-semibold text-foreground">
                  {selectedCatalog.name}
                </h3>
                {selectedCatalog.description && (
                  <p className="mb-2 text-sm text-muted-standard">{selectedCatalog.description}</p>
                )}
                <div className="space-y-1 text-sm text-muted-standard">
                  <div>
                    <span className="font-medium">ID:</span>{" "}
                    <span className="font-mono">{selectedCatalog.asset_id}</span>
                  </div>
                  <div>
                    <span className="font-medium">Status:</span>{" "}
                    <span
                      className={`inline-block rounded border px-2 py-1 text-xs font-medium ${
                        selectedCatalog.status === "published"
                          ? "border-green-800 bg-green-900/50 text-green-300"
                          : "border-border bg-surface-base text-muted-standard"
                      }`}
                    >
                      {selectedCatalog.status}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium">Source:</span>{" "}
                    <span>{selectedCatalog.content?.source_ref || "Not configured"}</span>
                  </div>
                </div>
              </div>

              {/* Scan Panel */}
              <CatalogScanPanel
                schema={selectedCatalog}
                onScanComplete={() => {
                  void refetch();
                }}
              />

              {/* Catalog Viewer */}
              <CatalogViewerPanel
                schema={selectedCatalog}
                onRefresh={() => {
                  void refetch();
                }}
              />
            </>
          ) : (
            <div className="ui-subbox p-8 text-center">
              <p className="text-muted-standard">Select a catalog to view details</p>
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
