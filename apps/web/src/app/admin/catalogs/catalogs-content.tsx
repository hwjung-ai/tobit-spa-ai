"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import CatalogTable from "@/components/admin/CatalogTable";
import CreateCatalogModal from "@/components/admin/CreateCatalogModal";
import CatalogScanPanel from "@/components/admin/CatalogScanPanel";
import CatalogViewerPanel from "@/components/admin/CatalogViewerPanel";
import StatusFilterButtons from "@/components/admin/StatusFilterButtons";
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
  const queryClient = useQueryClient();
  const [selectedCatalog, setSelectedCatalog] = useState<CatalogAsset | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "draft" | "published">("all");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [refreshNonce, setRefreshNonce] = useState(0);

  const {
    data: catalogsData,
    isLoading,
    isFetching,
  } = useQuery({
    queryKey: ["admin-catalogs", refreshNonce],
    queryFn: async () => {
      const response = await fetchApi<{ assets: CatalogAsset[] }>("/asset-registry/catalogs", { cache: "no-store" });
      return response.data?.assets || [];
    },
    staleTime: 5 * 60 * 1000,
  });

  const handleRefresh = () => {
    queryClient.removeQueries({ queryKey: ["admin-catalogs"] });
    setRefreshNonce((prev) => prev + 1);
  };

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
        <StatusFilterButtons
          value={statusFilter}
          onChange={(value) => setStatusFilter(value)}
        />
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => {
              void handleRefresh();
            }}
            disabled={isFetching}
            className="rounded-md border border-variant bg-surface-base px-3 py-2 text-label-sm transition hover:border-sky-500 hover:text-primary"
          >
            {isFetching ? "Refreshing..." : "Refresh"}
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
                onRefresh={handleRefresh}
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
                  void handleRefresh();
                }}
              />

              {/* Catalog Viewer */}
              <CatalogViewerPanel
                schema={selectedCatalog}
                onRefresh={() => {
                  void handleRefresh();
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
            void handleRefresh();
          }}
        />
      )}
    </div>
  );
}
