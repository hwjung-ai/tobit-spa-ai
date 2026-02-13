import { useState, useEffect } from "react";
import { Asset, fetchApi } from "../../lib/adminUtils";
import ValidationAlert from "./ValidationAlert";
import Toast from "./Toast";
import Link from "next/link";
import { useConfirm } from "@/hooks/use-confirm";
import { useSearchParams } from "next/navigation";
import {
  SCREEN_TEMPLATES,
  createMinimalScreen,
  getTemplateById,
} from "@/lib/ui-screen/screen-templates";

interface ScreenAssetPanelProps {
  onScreenUpdate?: () => void;
}

export default function ScreenAssetPanel({ onScreenUpdate }: ScreenAssetPanelProps) {
  const searchParams = useSearchParams();
  const [screens, setScreens] = useState<Asset[]>([]);
  const [filteredScreens, setFilteredScreens] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);

  // Initialize filter state from URL params
  const [searchTerm, setSearchTerm] = useState(searchParams.get("search") || "");
  const [filterStatus, setFilterStatus] = useState<"all" | "draft" | "published">(
    (searchParams.get("status") as "all" | "draft" | "published") || "all",
  );
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error" | "warning";
  } | null>(null);
  const [errors, setErrors] = useState<string[]>([]);
  const [newScreenData, setNewScreenData] = useState({
    screen_id: "",
    name: "",
    description: "",
    tags: "",
  });
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [refreshTrigger] = useState(0);
  const [confirm, ConfirmDialogComponent] = useConfirm();

  // Fetch screens when URL params change
  useEffect(() => {
    fetchScreens();
  }, [searchParams]);

  // Update URL with current filter state
  const updateUrlParams = (search: string, status: "all" | "draft" | "published") => {
    const params = new URLSearchParams(searchParams.toString());

    if (search) {
      params.set("search", search);
    } else {
      params.delete("search");
    }

    if (status !== "all") {
      params.set("status", status);
    } else {
      params.delete("status");
    }

    const newUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
    window.history.replaceState({}, "", newUrl);
  };

  useEffect(() => {
    let filtered = screens;

    // Filter by status
    if (filterStatus !== "all") {
      filtered = filtered.filter((s) => s.status === filterStatus);
    }

    // Filter by search term
    if (searchTerm.trim()) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (s) => s.screen_id?.toLowerCase().includes(term) || s.name?.toLowerCase().includes(term),
      );
    }

    setFilteredScreens(filtered);
  }, [screens, filterStatus, searchTerm]);

  const fetchScreens = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      // Fetch from asset-registry (source of truth for editor)
      const response = await fetchApi<{ assets: Asset[] }>(
        "/asset-registry/assets?asset_type=screen",
      );
      setScreens(response.data?.assets || []);
      setErrors([]);
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to fetch screens from asset-registry";
      setErrors([message]);
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
        } catch (tagError: unknown) {
          const message = tagError instanceof Error ? tagError.message : "syntax error";
          setErrors([`Invalid tags JSON: ${message}`]);
          return;
        }
      }

      await fetchApi("/asset-registry/assets", {
        method: "POST",
        body: JSON.stringify({
          asset_type: "screen",
          screen_id: newScreenData.screen_id,
          name: newScreenData.name,
          description: newScreenData.description || null,
          tags: parsedTags,
          schema_json: schema,
          created_by: "admin", // Default to admin user
        }),
      });

      setToast({ message: "Screen created successfully", type: "success" });
      setShowCreateModal(false);
      setNewScreenData({ screen_id: "", name: "", description: "", tags: "" });
      setSelectedTemplate(null);
      await fetchScreens();
      onScreenUpdate?.();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to create screen";
      if (message.includes("403") || message.includes("Permission")) {
        setErrors(["You don't have permission to create screens"]);
      } else {
        setErrors([message]);
      }
    }
  };

  const handleDeleteScreen = async (assetId: string) => {
    const ok = await confirm({
      title: "Delete Screen",
      description: "Are you sure you want to delete this screen? This action cannot be undone.",
      confirmLabel: "Delete",
    });
    if (!ok) return;

    try {
      setErrors([]);
      await fetchApi(`/asset-registry/assets/${assetId}`, {
        method: "DELETE",
      });
      setToast({ message: "Screen deleted successfully", type: "success" });

      // Optimistically update local state to prevent UI jump
      setScreens((prev) => prev.filter((s) => s.asset_id !== assetId));

      // Silently sync with server
      await fetchScreens(true);
      onScreenUpdate?.();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Failed to delete screen";
      setErrors([message]);
    }
  };

  const handlePublishScreen = async (assetId: string) => {
    try {
      setErrors([]);
      await fetchApi(`/asset-registry/assets/${assetId}/publish`, {
        method: "POST",
        body: JSON.stringify({ published_by: "admin" }),
      });
      setToast({ message: "Screen published successfully", type: "success" });
      await fetchScreens(true);
      onScreenUpdate?.();
    } catch (error: unknown) {
      setErrors([error instanceof Error ? error.message : "Failed to publish screen"]);
    }
  };

  const handleRollbackScreen = async (assetId: string) => {
    const ok = await confirm({
      title: "Rollback to Draft",
      description: "Are you sure you want to rollback this screen to draft?",
      confirmLabel: "Rollback",
    });
    if (!ok) return;

    try {
      setErrors([]);
      await fetchApi(`/asset-registry/assets/${assetId}/unpublish`, { method: "POST" });
      setToast({ message: "Screen rolled back to draft", type: "success" });
      await fetchScreens(true);
      onScreenUpdate?.();
    } catch (error: unknown) {
      setErrors([error instanceof Error ? error.message : "Failed to rollback screen"]);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center rounded-2xl border bg-surface-elevated border-border p-4 backdrop-blur-sm">
        <div className="min-w-[180px]">
          <label className="form-field-label">Status</label>
          <select
            value={filterStatus}
            onChange={(e) => {
              const value = e.target.value as "all" | "draft" | "published";
              setFilterStatus(value);
              updateUrlParams(searchTerm, value);
            }}
            className="input-container"
            data-testid="select-filter-status"
          >
            <option value="all">Any Status</option>
            <option value="draft">Draft Only</option>
            <option value="published">Published Only</option>
          </select>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={() => {
              void fetchScreens();
            }}
            className="text-label-sm font-bold uppercase tracking-widest text-muted-standard hover:text-primary"
          >
            Refresh
          </button>
          <div className="w-px h-6 bg-border" />
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary"
            data-testid="btn-create-screen"
          >
            + New Screen
          </button>
        </div>
      </div>

      {/* Errors */}
      {errors.length > 0 && <ValidationAlert errors={errors} onClose={() => setErrors([])} />}

      {/* Toast */}
      {toast && (
        <Toast message={toast.message} type={toast.type} onDismiss={() => setToast(null)} />
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50"
          onClick={() => setShowCreateModal(false)}
        >
          <div
            className=" border  rounded-lg p-6 w-full max-w-md"

            onClick={(e) => e.stopPropagation()}
            data-testid="modal-create-screen"
          >
            <h3 className="text-lg font-semibold  mb-4">
              Create New Screen
            </h3>

            <div className="space-y-4 max-h-96 overflow-y-auto">
              <div>
                <label
                  className="block text-sm  mb-2"

                >
                  Choose Template (Optional)
                </label>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {/* Blank Option */}
                  <button
                    onClick={() => setSelectedTemplate(null)}
                    className={`p-3 rounded border transition-all text-sm font-medium bg-surface-overlay text-foreground-secondary border-variant ${
                      selectedTemplate === null
                        ? "ring-2 ring-sky-500"
                        : "hover:opacity-75"
                    }`}
                    data-testid="template-blank"
                  >
                    <div className="font-semibold">Blank</div>
                    <div
                      className={`text-xs mt-1 ${selectedTemplate === null ? "text-sky-100" : ""}`}

                    >
                      Start from scratch
                    </div>
                  </button>

                  {/* Template Options */}
                  {SCREEN_TEMPLATES.map((template) => (
                    <button
                      key={template.id}
                      onClick={() => setSelectedTemplate(template.id)}
                      className={`p-3 rounded border transition-all text-sm font-medium bg-surface-overlay text-foreground-secondary border-variant ${
                        selectedTemplate === template.id
                          ? "ring-2 ring-sky-500"
                          : "hover:opacity-75"
                      }`}
                      data-testid={`template-${template.id}`}
                    >
                      <div className="font-semibold">{template.name}</div>
                      <div
                        className={`text-xs mt-1 line-clamp-2 ${selectedTemplate === template.id ? "text-sky-100" : ""}`}

                      >
                        {template.description}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label
                  className="block text-sm  mb-2"

                >
                  Screen ID *
                </label>
                <input
                  type="text"
                  value={newScreenData.screen_id}
                  onChange={(e) =>
                    setNewScreenData({ ...newScreenData, screen_id: e.target.value })
                  }
                  placeholder="e.g., dashboard_main"
                  className="w-full px-3 py-2 border rounded text-sm text-foreground bg-surface-elevated border-variant focus:outline-none focus:border-sky-500"
                  data-testid="input-screen-id"
                />
              </div>

              <div>
                <label
                  className="block text-sm  mb-2"

                >
                  Screen Name *
                </label>
                <input
                  type="text"
                  value={newScreenData.name}
                  onChange={(e) => setNewScreenData({ ...newScreenData, name: e.target.value })}
                  placeholder="e.g., Main Dashboard"
                  className="w-full px-3 py-2  border  rounded  text-sm focus:outline-none focus:border-sky-500"
                  style={{
                    borderColor: "var(--border)",
                    color: "var(--foreground)",
                    backgroundColor: "var(--surface-elevated)",
                  }}
                  data-testid="input-screen-name"
                />
              </div>

              <div>
                <label
                  className="block text-sm  mb-2"

                >
                  Description (Optional)
                </label>
                <textarea
                  value={newScreenData.description}
                  onChange={(e) =>
                    setNewScreenData({ ...newScreenData, description: e.target.value })
                  }
                  placeholder="e.g., Main dashboard for user overview"
                  className="w-full px-3 py-2 border rounded text-sm text-foreground bg-surface-elevated border-variant focus:outline-none focus:border-sky-500 resize-none"
                  rows={3}
                  data-testid="input-screen-description"
                />
              </div>
              <div>
                <label
                  className="block text-sm  mb-2"

                >
                  Tags (Optional JSON)
                </label>
                <textarea
                  value={newScreenData.tags}
                  onChange={(e) => setNewScreenData({ ...newScreenData, tags: e.target.value })}
                  placeholder='e.g., {"team":"ops","audience":"mobile"}'
                  className="w-full px-3 py-2 border rounded text-sm text-foreground bg-surface-elevated border-variant focus:outline-none focus:border-sky-500 resize-none"
                  rows={2}
                  data-testid="input-screen-tags"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="flex-1 px-4 py-2  hover:  rounded-lg transition-colors text-sm font-medium"

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

      {/* Search */}
      <div className="flex gap-4">
        <input
          type="text"
          placeholder="Search by ID or name..."
          value={searchTerm}
          onChange={(e) => {
            setSearchTerm(e.target.value);
            updateUrlParams(e.target.value, filterStatus);
          }}
          className="flex-1 px-4 py-2 border rounded-lg text-sm text-foreground bg-surface-elevated border-variant focus:outline-none focus:border-sky-500"
        />
      </div>

      {/* Loading State */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin">
            <svg className="w-8 h-8 text-sky-500" fill="none" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
          </div>
        </div>
      )}

      {/* Screens List */}
      {!loading && filteredScreens.length === 0 && (
        <div className="ui-subbox py-12 text-center">
          <svg
            className="w-12 h-12  mx-auto mb-3"

            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M10 6H5a2 2 0 00-2 2v10a2 2 0 002 2h5M16 6h5a2 2 0 012 2v10a2 2 0 01-2 2h-5m-4-6h4"
            />
          </svg>
          <p className=" text-sm">
            No screens found
          </p>
        </div>
      )}

      {!loading && filteredScreens.length > 0 && (
        <div className="grid gap-3">
          {filteredScreens.map((screen) => (
            <div
              key={screen.asset_id}
              className="ui-subbox transition-colors"
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
                      className={`inline-flex px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${
                        screen.status === "published"
                          ? "bg-emerald-950/50 text-emerald-300 border border-emerald-800/50"
                          : "  border /50"
                      }`}
                      style={{
                        backgroundColor: "var(--surface-overlay)",
                        color: "var(--muted-foreground)",
                        borderColor: "var(--border)",
                      }}
                      data-testid={`status-badge-${screen.asset_id}`}
                    >
                      {screen.status}
                    </span>
                  </div>
                  <p className=" text-sm mb-2">
                    {screen.screen_id}
                  </p>
                  {screen.description && (
                    <p className=" text-xs">
                      {screen.description}
                    </p>
                  )}
                </div>
                <div className="text-right flex flex-col items-end">
                  <p className=" text-xs font-mono">
                    v{screen.version}
                  </p>
                  <p className=" text-xs mb-3">
                    {new Date(screen.updated_at).toLocaleDateString()}
                  </p>
                  <div className="flex gap-2 justify-end">
                    <Link
                      href={`/admin/screens/${screen.asset_id}`}
                      className="px-3 py-1.5  hover:  rounded text-xs font-medium transition-colors text-center"
                      style={{
                        color: "var(--foreground-secondary)",
                        backgroundColor: "var(--surface-elevated)",
                      }}
                      data-testid={`btn-edit-${screen.asset_id}`}
                    >
                      Edit
                    </Link>
                    {screen.status === "draft" && (
                      <button
                        onClick={() => {
                          handleDeleteScreen(screen.asset_id);
                        }}
                        className="px-3 py-1.5 bg-rose-700 hover:bg-rose-600 text-white rounded text-xs font-medium transition-colors text-center"
                        data-testid={`btn-delete-${screen.asset_id}`}
                      >
                        Delete
                      </button>
                    )}
                    {screen.status === "draft" && (
                      <button
                        onClick={() => {
                          handlePublishScreen(screen.asset_id);
                        }}
                        className="px-3 py-1.5 bg-sky-700 hover:bg-sky-600 text-white rounded text-xs font-medium transition-colors text-center"
                        data-testid={`btn-publish-${screen.asset_id}`}
                      >
                        Publish
                      </button>
                    )}
                    {screen.status === "published" && (
                      <button
                        onClick={() => {
                          handleRollbackScreen(screen.asset_id);
                        }}
                        className="px-3 py-1.5 bg-orange-700 hover:bg-orange-600 text-white rounded text-xs font-medium transition-colors text-center"
                        data-testid={`btn-rollback-${screen.asset_id}`}
                      >
                        Rollback
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      <ConfirmDialogComponent />
    </div>
  );
}
