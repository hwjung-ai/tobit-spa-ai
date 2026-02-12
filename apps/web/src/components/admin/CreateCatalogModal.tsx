"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/adminUtils";

interface CreateSchemaModalProps {
  onClose: () => void;
  onSave: () => void;
}

export default function CreateSchemaModal({ onClose, onSave }: CreateSchemaModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [sourceRef, setSourceRef] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Fetch available sources
  const { data: sourcesData } = useQuery({
    queryKey: ["admin-sources"],
    queryFn: async () => {
      const response = await fetchApi("/asset-registry/sources?status=published");
      return response.data?.assets || [];
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    if (!name.trim()) {
      setError("Name is required");
      setLoading(false);
      return;
    }

    if (!sourceRef) {
      setError("Source is required");
      setLoading(false);
      return;
    }

    try {
      const payload = {
        name: name.trim(),
        description: description.trim() || null,
        content: {
          source_ref: sourceRef,
          catalog: {
            scan_status: "pending",
          },
        },
      };

      const response = await fetchApi("/asset-registry/catalogs", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (response.success) {
        onSave();
        onClose();
      } else {
        setError(response.message || "Failed to create schema asset");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
      <div className=" border  rounded-2xl shadow-2xl max-w-md w-full mx-4" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
        <div className="p-6 border-b " style={{borderColor: "var(--border)"}}>
          <h2 className="text-xl font-bold  mb-1" style={{color: "var(--foreground)"}}>Create Catalog Asset</h2>
          <p className="text-xs " style={{color: "var(--muted-foreground)"}}>Scan database schema and store metadata</p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Name */}
          <div>
            <label className="block text-xs font-bold  uppercase tracking-wider mb-2" style={{color: "var(--muted-foreground)"}}>
              Catalog Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={loading}
              className="w-full px-4 py-3  border  rounded-lg  placeholder-slate-600 focus:outline-none focus:border-sky-500/50 transition-all disabled:opacity-50" style={{borderColor: "var(--border)", color: "var(--foreground)", backgroundColor: "var(--surface-base)"}}
              placeholder="e.g., factory_postgres"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-bold  uppercase tracking-wider mb-2" style={{color: "var(--muted-foreground)"}}>
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={loading}
              className="w-full px-4 py-3  border  rounded-lg  placeholder-slate-600 focus:outline-none focus:border-sky-500/50 transition-all disabled:opacity-50" style={{borderColor: "var(--border)", color: "var(--foreground)", backgroundColor: "var(--surface-base)"}}
              placeholder="Describe this catalog..."
              rows={3}
            />
          </div>

          {/* Source */}
          <div>
            <label className="block text-xs font-bold  uppercase tracking-wider mb-2" style={{color: "var(--muted-foreground)"}}>
              Database Source <span className="text-red-500">*</span>
            </label>
            <select
              value={sourceRef}
              onChange={(e) => setSourceRef(e.target.value)}
              disabled={loading}
              className="w-full px-4 py-3  border  rounded-lg  focus:outline-none focus:border-sky-500/50 transition-all disabled:opacity-50" style={{borderColor: "var(--border)", color: "var(--foreground)", backgroundColor: "var(--surface-base)"}}
            >
              <option value="" className="" style={{backgroundColor: "var(--surface-base)"}}>Select a source...</option>
              {sourcesData?.map((source: any) => (
                <option key={source.asset_id} value={source.name} className="" style={{backgroundColor: "var(--surface-base)"}}>
                  {source.name}
                </option>
              ))}
            </select>
            <p className="mt-2 text-xs " style={{color: "var(--muted-foreground)"}}>
              💡 Source must be published before creating catalog
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-900/30 border border-red-800/50 rounded-lg">
              <p className="text-sm text-red-400">{error}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3 pt-4 border-t " style={{borderColor: "var(--border)"}}>
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 px-4 py-3  hover: rounded-lg transition-colors font-medium text-sm disabled:opacity-50 uppercase tracking-wide" style={{color: "var(--foreground-secondary)"}}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-4 py-3 bg-sky-600 hover:bg-sky-500 disabled: text-white rounded-lg shadow-lg font-medium text-sm disabled:opacity-50 uppercase tracking-wide transition-all" style={{backgroundColor: "var(--surface-elevated)"}}
            >
              {loading ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
