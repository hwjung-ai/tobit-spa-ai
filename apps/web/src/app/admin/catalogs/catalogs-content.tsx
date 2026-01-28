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
      const response = await fetchApi("/asset-registry/catalogs");
      return response.data?.assets || [];
    },
    staleTime: 5 * 60 * 1000,
  });

  const catalogs = catalogsData || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left Side: Catalog List */}
      <div className="lg:col-span-1">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Catalogs</h2>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-3 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors"
          >
            + New Catalog
          </button>
        </div>

        {isLoading ? (
          <div className="text-center py-4 text-gray-500">Loading...</div>
        ) : (
          <CatalogTable
            catalogs={catalogs}
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
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold text-lg mb-3">{selectedCatalog.name}</h3>
              {selectedCatalog.description && (
                <p className="text-sm text-gray-600 mb-2">{selectedCatalog.description}</p>
              )}
              <div className="text-sm text-gray-500 space-y-1">
                <div>
                  <span className="font-medium">ID:</span> {selectedCatalog.asset_id}
                </div>
                <div>
                  <span className="font-medium">Status:</span>{" "}
                  <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                    selectedCatalog.status === "published"
                      ? "bg-green-100 text-green-800"
                      : "bg-gray-100 text-gray-800"
                  }`}>
                    {selectedCatalog.status}
                  </span>
                </div>
                <div>
                  <span className="font-medium">Source:</span>{" "}
                  {selectedCatalog.content?.source_ref || "Not configured"}
                </div>
              </div>
            </div>

            {/* Scan Panel */}
            <CatalogScanPanel schema={selectedCatalog} onScanComplete={refetch} />

            {/* Catalog Viewer */}
            <CatalogViewerPanel schema={selectedCatalog} onRefresh={refetch} />
          </>
        ) : (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-gray-500">Select a catalog to view details</p>
          </div>
        )}
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
