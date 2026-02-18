"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import CatalogTable from "@/components/admin/CatalogTable";
import CatalogScanPanel from "@/components/admin/CatalogScanPanel";
import CatalogViewerPanel from "@/components/admin/CatalogViewerPanel";
import CreateCatalogModal from "@/components/admin/CreateCatalogModal";
import CreateSourceModal from "@/components/admin/CreateSourceModal";
import StatusBadge from "@/components/admin/StatusBadge";
import StatusFilterButtons from "@/components/admin/StatusFilterButtons";
import Toast from "@/components/admin/Toast";
import { fetchApi } from "@/lib/adminUtils";
import { cn } from "@/lib/utils";

interface CatalogAsset {
  asset_id: string;
  name: string;
  description?: string;
  status: string;
  version: number;
  catalog?: {
    source_ref?: string;
    tables?: Record<string, unknown>[];
    scan_status?: string;
    last_scanned_at?: string;
  };
  content?: {
    source_ref?: string;
    catalog?: {
      tables?: Record<string, unknown>[];
      scan_status?: string;
      last_scanned_at?: string;
    };
  };
}

interface SourceAsset {
  asset_id: string;
  name: string;
  description?: string;
  status: string;
  source_type: string;
  connection?: {
    host?: string | null;
    port?: number | null;
    username?: string | null;
    database?: string | null;
  };
  updated_at?: string;
}

type CatalogTab = "catalogs" | "sources";

export default function CatalogsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [selectedCatalog, setSelectedCatalog] = useState<CatalogAsset | null>(null);
  const [selectedSource, setSelectedSource] = useState<SourceAsset | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "draft" | "published">("all");
  const [showCreateCatalogModal, setShowCreateCatalogModal] = useState(false);
  const [showCreateSourceModal, setShowCreateSourceModal] = useState(false);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [testingSourceId, setTestingSourceId] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(
    null,
  );

  const tabFromUrl = searchParams.get("tab");
  const activeTab: CatalogTab = tabFromUrl === "sources" ? "sources" : "catalogs";

  const setActiveTab = (tab: CatalogTab) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("tab", tab);
    router.replace(`/admin/catalogs?${params.toString()}`);
  };

  useEffect(() => {
    setSelectedCatalog(null);
    setSelectedSource(null);
  }, [activeTab]);

  const {
    data: catalogsData,
    isLoading: catalogsLoading,
    isFetching: catalogsFetching,
    error: catalogsError,
  } = useQuery({
    queryKey: ["admin-catalogs", refreshNonce],
    queryFn: async () => {
      const response = await fetchApi<{ assets: CatalogAsset[] }>("/asset-registry/catalogs", {
        cache: "no-store",
      });
      const assets = response.data?.assets || [];
      return assets.map((asset) => ({
        ...asset,
        content: {
          source_ref: asset.catalog?.source_ref,
          catalog: {
            tables: asset.catalog?.tables,
            scan_status: asset.catalog?.scan_status,
            last_scanned_at: asset.catalog?.last_scanned_at,
          },
        },
      }));
    },
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: sourcesData,
    isLoading: sourcesLoading,
    isFetching: sourcesFetching,
    error: sourcesError,
  } = useQuery({
    queryKey: ["admin-sources", refreshNonce],
    queryFn: async () => {
      const response = await fetchApi<{ assets: SourceAsset[] }>("/asset-registry/sources", {
        cache: "no-store",
      });
      return response.data?.assets || [];
    },
    staleTime: 5 * 60 * 1000,
  });

  const handleRefresh = () => {
    queryClient.removeQueries({ queryKey: ["admin-catalogs"] });
    queryClient.removeQueries({ queryKey: ["admin-sources"] });
    setRefreshNonce((prev) => prev + 1);
  };

  const filteredCatalogs = useMemo(() => {
    const catalogs = catalogsData || [];
    if (statusFilter === "all") return catalogs;
    return catalogs.filter((catalog) => catalog.status === statusFilter);
  }, [catalogsData, statusFilter]);

  const filteredSources = useMemo(() => {
    const sources = sourcesData || [];
    if (statusFilter === "all") return sources;
    return sources.filter((source) => source.status === statusFilter);
  }, [sourcesData, statusFilter]);

  const handleTestSource = async (source: SourceAsset) => {
    setTestingSourceId(source.asset_id);
    try {
      const response = await fetchApi<{ success?: boolean; message?: string }>(
        `/asset-registry/sources/${source.asset_id}/test`,
        { method: "POST" },
      );
      const passed = Boolean(response.data?.success);
      setToast({
        type: passed ? "success" : "error",
        message: response.data?.message || (passed ? "Connection test passed" : "Connection test failed"),
      });
    } catch (error) {
      setToast({
        type: "error",
        message: error instanceof Error ? error.message : "Connection test failed",
      });
    } finally {
      setTestingSourceId(null);
    }
  };

  const isFetching = activeTab === "catalogs" ? catalogsFetching : sourcesFetching;
  const isLoading = activeTab === "catalogs" ? catalogsLoading : sourcesLoading;
  const hasError = activeTab === "catalogs" ? catalogsError : sourcesError;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-border bg-surface-elevated p-4 backdrop-blur-sm">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex h-12 items-center rounded-xl border border-border bg-surface-base px-3">
              <div className="inline-flex rounded-xl border border-border bg-surface-elevated p-1">
                <button
                  type="button"
                  onClick={() => setActiveTab("catalogs")}
                  className={cn(
                    "rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition",
                    activeTab === "catalogs"
                      ? "bg-sky-600 text-white dark:bg-sky-700"
                      : "bg-transparent text-foreground hover:bg-surface-elevated",
                  )}
                >
                  Catalogs
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("sources")}
                  className={cn(
                    "rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition",
                    activeTab === "sources"
                      ? "bg-sky-600 text-white dark:bg-sky-700"
                      : "bg-transparent text-foreground hover:bg-surface-elevated",
                  )}
                >
                  Sources
                </button>
              </div>
            </div>

            <div className="flex h-12 items-center rounded-xl border border-border bg-surface-base px-3">
              <StatusFilterButtons value={statusFilter} onChange={setStatusFilter} />
            </div>
          </div>

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
            <button
              onClick={() =>
                activeTab === "catalogs"
                  ? setShowCreateCatalogModal(true)
                  : setShowCreateSourceModal(true)
              }
              className="btn-primary"
            >
              {activeTab === "catalogs" ? "+ New Catalog" : "+ New Source"}
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          {isLoading ? (
            <div className="py-4 text-center text-muted-standard">Loading...</div>
          ) : hasError ? (
            <div className="rounded-lg border border-red-800/50 bg-red-900/20 p-4 text-sm text-red-300">
              Failed to load {activeTab}: {hasError instanceof Error ? hasError.message : "Unknown error"}
            </div>
          ) : activeTab === "catalogs" ? (
            <CatalogTable
              catalogs={filteredCatalogs}
              selectedCatalog={selectedCatalog}
              onSelect={setSelectedCatalog}
              onRefresh={handleRefresh}
            />
          ) : (
            <div className="space-y-2">
              {filteredSources.length === 0 ? (
                <div className="rounded-lg border border-variant bg-surface-overlay py-8 text-center text-muted-foreground">
                  No sources created yet
                </div>
              ) : (
                filteredSources.map((source) => (
                  <button
                    key={source.asset_id}
                    type="button"
                    onClick={() => setSelectedSource(source)}
                    className={cn(
                      "w-full rounded-lg border border-variant bg-surface-overlay p-3 text-left transition-colors hover:bg-surface-elevated",
                      selectedSource?.asset_id === source.asset_id &&
                        "border-sky-500/50 bg-sky-900/40",
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <h4 className="truncate text-sm font-medium text-foreground">{source.name}</h4>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {source.source_type} · {source.connection?.host || "host not set"}
                        </p>
                      </div>
                      <StatusBadge status={source.status} />
                    </div>
                  </button>
                ))
              )}
            </div>
          )}
        </div>

        <div className="space-y-4 lg:col-span-2">
          {activeTab === "catalogs" ? (
            selectedCatalog ? (
              <>
                <div className="ui-subbox">
                  <h3 className="mb-3 text-lg font-semibold text-foreground">{selectedCatalog.name}</h3>
                  {selectedCatalog.description ? (
                    <p className="mb-2 text-sm text-muted-standard">{selectedCatalog.description}</p>
                  ) : null}
                  <div className="space-y-1 text-sm text-muted-standard">
                    <div>
                      <span className="font-medium">ID:</span>{" "}
                      <span className="font-mono">{selectedCatalog.asset_id}</span>
                    </div>
                    <div>
                      <span className="font-medium">Status:</span>{" "}
                      <StatusBadge status={selectedCatalog.status} />
                    </div>
                    <div>
                      <span className="font-medium">Source:</span>{" "}
                      <span>{selectedCatalog.content?.source_ref || "Not configured"}</span>
                    </div>
                  </div>
                </div>

                <CatalogScanPanel
                  schema={selectedCatalog}
                  onScanComplete={() => {
                    void handleRefresh();
                  }}
                />

                <CatalogViewerPanel
                  schema={selectedCatalog as unknown as Record<string, unknown>}
                  onRefresh={() => {
                    void handleRefresh();
                  }}
                />
              </>
            ) : (
              <div className="ui-subbox p-8 text-center">
                <p className="text-muted-standard">Select a catalog to view details</p>
              </div>
            )
          ) : selectedSource ? (
            <div className="ui-subbox space-y-4">
              <div>
                <h3 className="text-lg font-semibold text-foreground">{selectedSource.name}</h3>
                {selectedSource.description ? (
                  <p className="mt-1 text-sm text-muted-standard">{selectedSource.description}</p>
                ) : null}
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-muted-foreground">Type</span>
                  <p className="font-mono text-foreground">{selectedSource.source_type}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Host</span>
                  <p className="font-mono text-foreground">{selectedSource.connection?.host || "-"}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Port</span>
                  <p className="font-mono text-foreground">{selectedSource.connection?.port || "-"}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Database</span>
                  <p className="font-mono text-foreground">{selectedSource.connection?.database || "-"}</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2 border-t border-variant pt-4">
                <button
                  type="button"
                  onClick={() => {
                    void handleTestSource(selectedSource);
                  }}
                  disabled={testingSourceId === selectedSource.asset_id}
                  className="rounded-md border border-variant bg-surface-base px-3 py-2 text-label-sm transition hover:border-sky-500 hover:text-primary disabled:opacity-60"
                >
                  {testingSourceId === selectedSource.asset_id ? "Testing..." : "Test Connection"}
                </button>
                <Link
                  href={`/admin/assets/${selectedSource.asset_id}`}
                  className="rounded-md border border-variant bg-surface-base px-3 py-2 text-label-sm transition hover:border-sky-500 hover:text-primary"
                >
                  Open Detail
                </Link>
              </div>
            </div>
          ) : (
            <div className="ui-subbox p-8 text-center">
              <p className="text-muted-standard">Select a source to manage connection details</p>
            </div>
          )}
        </div>
      </div>

      {showCreateCatalogModal ? (
        <CreateCatalogModal
          onClose={() => setShowCreateCatalogModal(false)}
          onSave={() => {
            setShowCreateCatalogModal(false);
            void handleRefresh();
          }}
        />
      ) : null}

      {showCreateSourceModal ? (
        <CreateSourceModal
          onClose={() => setShowCreateSourceModal(false)}
          onSave={() => {
            setShowCreateSourceModal(false);
            void handleRefresh();
          }}
        />
      ) : null}

      {toast ? (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => {
            setToast(null);
          }}
        />
      ) : null}
    </div>
  );
}
