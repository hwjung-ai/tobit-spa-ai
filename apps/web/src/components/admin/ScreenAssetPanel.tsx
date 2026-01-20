"use client";

import { useState, useEffect } from "react";
import { Asset, fetchApi } from "../../lib/adminUtils";
import ValidationAlert from "./ValidationAlert";
import Toast from "./Toast";
import Link from "next/link";
import {
  SCREEN_TEMPLATES,
  createMinimalScreen,
  getTemplateById,
} from "@/lib/ui-screen/screen-templates";

interface ScreenAssetPanelProps {
  onScreenUpdate?: () => void;
}

export default function ScreenAssetPanel({ onScreenUpdate }: ScreenAssetPanelProps) {
  const [screens, setScreens] = useState<Asset[]>([]);
  const [filteredScreens, setFilteredScreens] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState<"all" | "draft" | "published">("all");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "warning" } | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [newScreenData, setNewScreenData] = useState({
    screen_id: "",
    name: "",
    description: "",
    tags: "",
  });
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  useEffect(() => {
    fetchScreens();
  }, [refreshTrigger]);

  useEffect(() => {
    let filtered = screens;

    // Filter by status
    if (filterStatus !== "all") {
      filtered = filtered.filter(s => s.status === filterStatus);
    }

    // Filter by search term
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(s =>
        s.screen_id?.toLowerCase().includes(term) ||
        s.name?.toLowerCase().includes(term)
      );
    }

    setFilteredScreens(filtered);
  }, [screens, filterStatus, searchTerm]);

  const fetchScreens = async () => {
    setLoading(true);
    try {
      // Fetch from asset-registry (source of truth for editor)
      const response = await fetchApi("/asset-registry/assets?asset_type=screen");
      setScreens(response.data?.assets || []);
      setErrors([]);
    } catch (error: any) {
      setErrors([error.message || "Failed to fetch screens from asset-registry"]);
      setScreens([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateScreen = async () => {
    setErrors([]);

    // Validation
    if (!newScreenData.screen_id.trim()) {
      setErrors(["Screen ID is required"]);
      return;
    }

    if (!newScreenData.name.trim()) {
      setErrors(["Screen name is required"]);
      return;
    }

    try {
      // Generate screen schema based on selected template
      let schema;
      if (selectedTemplate) {
        const template = getTemplateById(selectedTemplate);
        if (template) {
          schema = template.generate({
            screen_id: newScreenData.screen_id,
            name: newScreenData.name,
          });
        } else {
          schema = createMinimalScreen(newScreenData.screen_id, newScreenData.name);
        }
      } else {
        schema = createMinimalScreen(newScreenData.screen_id, newScreenData.name);
      }

      let parsedTags = null;
      if (newScreenData.tags.trim()) {
        try {
          parsedTags = JSON.parse(newScreenData.tags);
        } catch (tagError: any) {
          setErrors([`Invalid tags JSON: ${tagError.message || "syntax error"}`]);
          return;
        }
      }

      const response = await fetchApi("/asset-registry/assets", {
        method: "POST",
        body: JSON.stringify({
          asset_type: "screen",
          screen_id: newScreenData.screen_id,
          name: newScreenData.name,
          description: newScreenData.description || null,
          tags: parsedTags,
          schema_json: schema,
        }),
      });

      setToast({ message: "Screen created successfully", type: "success" });
      setShowCreateModal(false);
      setNewScreenData({ screen_id: "", name: "", description: "", tags: "" });
      setSelectedTemplate(null);
      await fetchScreens();
      onScreenUpdate?.();
    } catch (error: any) {
      const message = error.message || "Failed to create screen";
      if (message.includes("403") || message.includes("Permission")) {
        setErrors(["You don't have permission to create screens"]);
      } else {
        setErrors([message]);
      }
    }
  };

  return (
    <div className="space-y-4">
      {/* Header with Create Button */}
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold text-slate-100">Screen Assets</h2>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg transition-colors text-sm font-medium"
          data-testid="btn-create-screen"
        >
          + Create Screen
        </button>
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <ValidationAlert errors={errors} onDismiss={() => setErrors([])} />
      )}

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
          onClick={() => setShowCreateModal(false)}
        >
          <div
            className="bg-slate-900 border border-slate-700 rounded-lg p-6 w-full max-w-md"
            onClick={e => e.stopPropagation()}
            data-testid="modal-create-screen"
          >
            <h3 className="text-lg font-semibold text-slate-100 mb-4">Create New Screen</h3>

            <div className="space-y-4 max-h-96 overflow-y-auto">
              <div>
                <label className="block text-sm text-slate-300 mb-2">Choose Template (Optional)</label>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {/* Blank Option */}
                  <button
                    onClick={() => setSelectedTemplate(null)}
                    className={`p-3 rounded border transition-all text-sm font-medium ${
                      selectedTemplate === null
                        ? "bg-sky-900/50 border-sky-500 text-sky-300"
                        : "bg-slate-800/50 border-slate-700 text-slate-300 hover:border-slate-600"
                    }`}
                    data-testid="template-blank"
                  >
                    <div className="font-semibold">Blank</div>
                    <div className="text-xs text-slate-400 mt-1">Start from scratch</div>
                  </button>

                  {/* Template Options */}
                  {SCREEN_TEMPLATES.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => setSelectedTemplate(template.id)}
                      className={`p-3 rounded border transition-all text-sm font-medium ${
                        selectedTemplate === template.id
                          ? "bg-sky-900/50 border-sky-500 text-sky-300"
                          : "bg-slate-800/50 border-slate-700 text-slate-300 hover:border-slate-600"
                      }`}
                      data-testid={`template-${template.id}`}
                    >
                      <div className="font-semibold">{template.name}</div>
                      <div className="text-xs text-slate-400 mt-1 line-clamp-2">
                        {template.description}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm text-slate-300 mb-2">Screen ID *</label>
                <input
                  type="text"
                  value={newScreenData.screen_id}
                  onChange={e => setNewScreenData({ ...newScreenData, screen_id: e.target.value })}
                  placeholder="e.g., dashboard_main"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-slate-100 text-sm focus:outline-none focus:border-sky-500"
                  data-testid="input-screen-id"
                />
              </div>

              <div>
                <label className="block text-sm text-slate-300 mb-2">Screen Name *</label>
                <input
                  type="text"
                  value={newScreenData.name}
                  onChange={e => setNewScreenData({ ...newScreenData, name: e.target.value })}
                  placeholder="e.g., Main Dashboard"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-slate-100 text-sm focus:outline-none focus:border-sky-500"
                  data-testid="input-screen-name"
                />
              </div>

              <div>
                <label className="block text-sm text-slate-300 mb-2">Description (Optional)</label>
                <textarea
                  value={newScreenData.description}
                  onChange={e => setNewScreenData({ ...newScreenData, description: e.target.value })}
                  placeholder="e.g., Main dashboard for user overview"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-slate-100 text-sm focus:outline-none focus:border-sky-500 resize-none"
                  rows={3}
                  data-testid="input-screen-description"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-300 mb-2">Tags (Optional JSON)</label>
                <textarea
                  value={newScreenData.tags}
                  onChange={e => setNewScreenData({ ...newScreenData, tags: e.target.value })}
                  placeholder='e.g., {"team":"ops","audience":"mobile"}'
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-slate-100 text-sm focus:outline-none focus:border-sky-500 resize-none"
                  rows={2}
                  data-testid="input-screen-tags"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-100 rounded-lg transition-colors text-sm font-medium"
                data-testid="btn-cancel-create"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateScreen}
                className="flex-1 px-4 py-2 bg-sky-600 hover:bg-sky-700 text-white rounded-lg transition-colors text-sm font-medium"
                data-testid="btn-confirm-create"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search and Filter */}
      <div className="flex gap-4">
        <input
          type="text"
          placeholder="Search by ID or name..."
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="flex-1 px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-sky-500"
          data-testid="input-search-screens"
        />

        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value as any)}
          className="px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-100 text-sm focus:outline-none focus:border-sky-500"
          data-testid="select-filter-status"
        >
          <option value="all">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
        </select>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin">
            <svg className="w-8 h-8 text-sky-500" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          </div>
        </div>
      )}

      {/* Screens List */}
      {!loading && filteredScreens.length === 0 && (
        <div className="text-center py-12 bg-slate-900/40 rounded-lg border border-slate-800">
          <svg className="w-12 h-12 text-slate-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 6H5a2 2 0 00-2 2v10a2 2 0 002 2h5M16 6h5a2 2 0 012 2v10a2 2 0 01-2 2h-5m-4-6h4" />
          </svg>
          <p className="text-slate-400 text-sm">No screens found</p>
        </div>
      )}

      {!loading && filteredScreens.length > 0 && (
        <div className="grid gap-3">
          {filteredScreens.map((screen) => (
            <div
              key={screen.asset_id}
              className="bg-slate-900/40 border border-slate-800 rounded-lg p-4 hover:border-slate-700 transition-colors"
              data-testid={`screen-asset-${screen.asset_id}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <Link
                      href={`/admin/screens/${screen.asset_id}`}
                      className="text-sky-400 hover:text-sky-300 font-semibold text-base transition-colors"
                      data-testid={`link-screen-${screen.asset_id}`}
                    >
                      {screen.name}
                    </Link>
                    <span
                      className={`inline-flex px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        screen.status === "published"
                          ? "bg-emerald-950/50 text-emerald-300 border border-emerald-800/50"
                          : "bg-slate-800/50 text-slate-400 border border-slate-700/50"
                      }`}
                      data-testid={`status-badge-${screen.asset_id}`}
                    >
                      {screen.status}
                    </span>
                  </div>
                  <p className="text-slate-500 text-sm mb-2">{screen.screen_id}</p>
                  {screen.description && (
                    <p className="text-slate-400 text-xs">{screen.description}</p>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-slate-500 text-xs font-mono">v{screen.version}</p>
                  <p className="text-slate-600 text-xs">
                    {new Date(screen.updated_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              <div className="mt-3 flex gap-2">
                <Link
                  href={`/admin/screens/${screen.asset_id}`}
                  className="flex-1 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-100 rounded text-xs font-medium transition-colors text-center"
                  data-testid={`btn-edit-${screen.asset_id}`}
                >
                  Edit
                </Link>
                {screen.status === "draft" && (
                  <button
                    onClick={() => {
                      // Publish functionality
                      handlePublishScreen(screen.asset_id);
                    }}
                    className="flex-1 px-3 py-1.5 bg-sky-700 hover:bg-sky-600 text-white rounded text-xs font-medium transition-colors"
                    data-testid={`btn-publish-${screen.asset_id}`}
                  >
                    Publish
                  </button>
                )}
                {screen.status === "published" && (
                  <button
                    onClick={() => {
                      // Rollback functionality
                      handleRollbackScreen(screen.asset_id);
                    }}
                    className="flex-1 px-3 py-1.5 bg-orange-700 hover:bg-orange-600 text-white rounded text-xs font-medium transition-colors"
                    data-testid={`btn-rollback-${screen.asset_id}`}
                  >
                    Rollback
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );

  async function handlePublishScreen(assetId: string) {
    try {
      setErrors([]);
      await fetchApi(`/asset-registry/assets/${assetId}/publish`, {
        method: "POST",
        body: JSON.stringify({ published_by: "admin" }),
      });
      setToast({ message: "Screen published successfully", type: "success" });
      await fetchScreens();
      onScreenUpdate?.();
    } catch (error: any) {
      setErrors([error.message || "Failed to publish screen"]);
    }
  }

  async function handleRollbackScreen(assetId: string) {
    if (!confirm("Are you sure you want to rollback this screen to draft?")) return;

    try {
      setErrors([]);
      await fetchApi(`/asset-registry/assets/${assetId}/unpublish`, { method: "POST" });
      setToast({ message: "Screen rolled back to draft", type: "success" });
      await fetchScreens();
      onScreenUpdate?.();
    } catch (error: any) {
      setErrors([error.message || "Failed to rollback screen"]);
    }
  }
}
