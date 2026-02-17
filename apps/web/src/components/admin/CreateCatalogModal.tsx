"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/adminUtils";

interface CreateSchemaModalProps {
  onClose: () => void;
  onSave: () => void;
}

interface SourceItem {
  asset_id: string;
  name: string;
  status: string;
}

export default function CreateSchemaModal({ onClose, onSave }: CreateSchemaModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [sourceRef, setSourceRef] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Fetch available sources
  const {
    data: sourcesData = [],
    isLoading: sourcesLoading,
    error: sourcesError,
  } = useQuery<SourceItem[]>({
    queryKey: ["admin-sources"],
    queryFn: async () => {
      const response = await fetchApi<{ assets: SourceItem[] }>("/asset-registry/sources");
      return response.data?.assets || [];
    },
  });
  const publishedSources = sourcesData.filter((source) => source.status === "published");

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
        source_ref: sourceRef,
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-md overflow-hidden rounded-2xl border border-variant bg-surface-base shadow-2xl">
        <div className="border-b border-variant p-6">
          <h2 className="mb-1 text-xl font-bold text-foreground">Create Catalog Asset</h2>
          <p className="text-xs text-muted-foreground">Scan database schema and store metadata</p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Name */}
          <div>
            <label className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Catalog Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={loading}
              className="w-full rounded-xl border border-variant bg-surface-base px-4 py-3 text-foreground placeholder:text-muted-foreground transition-all focus:border-sky-500/50 focus:outline-none disabled:opacity-50"
              placeholder="e.g., factory_postgres"
            />
          </div>

          {/* Description */}
          <div>
            <label className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={loading}
              className="w-full resize-none rounded-xl border border-variant bg-surface-base px-4 py-3 text-foreground placeholder:text-muted-foreground transition-all focus:border-sky-500/50 focus:outline-none disabled:opacity-50"
              placeholder="Describe this catalog..."
              rows={3}
            />
          </div>

          {/* Source */}
          <div>
            <label className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Database Source <span className="text-red-500">*</span>
            </label>
            <select
              value={sourceRef}
              onChange={(e) => setSourceRef(e.target.value)}
              disabled={loading || sourcesLoading}
              className="w-full rounded-xl border border-variant bg-surface-base px-4 py-3 text-foreground transition-all focus:border-sky-500/50 focus:outline-none disabled:opacity-50"
            >
              <option value="" className="bg-surface-elevated text-foreground">
                {sourcesLoading ? "Loading sources..." : "Select a source..."}
              </option>
              {publishedSources.map((source) => (
                <option key={source.asset_id} value={source.name} className="bg-surface-elevated text-foreground">
                  {source.name}
                </option>
              ))}
            </select>
            {sourcesError && (
              <p className="mt-2 text-xs text-red-400">
                Failed to load sources: {sourcesError instanceof Error ? sourcesError.message : "Unknown error"}
              </p>
            )}
            {!sourcesLoading && !sourcesError && publishedSources.length === 0 && (
              <p className="mt-2 text-xs text-yellow-300">
                No published sources found. Publish a source first in Admin assets.
              </p>
            )}
            <p className="mt-2 text-xs text-muted-foreground">
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
          <div className="flex gap-3 border-t border-variant pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 rounded-xl px-4 py-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:bg-surface-elevated hover:text-foreground disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-xl bg-sky-600 px-4 py-3 text-sm font-semibold uppercase tracking-wide text-white shadow-lg shadow-sky-900/20 transition-all hover:bg-sky-500 disabled:opacity-50 dark:bg-sky-700 dark:hover:bg-sky-600"
            >
              {loading ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
