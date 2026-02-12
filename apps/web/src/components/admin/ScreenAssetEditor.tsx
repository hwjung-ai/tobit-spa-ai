"use client";

import { useState, useEffect, useCallback } from "react";
import { Asset, fetchApi } from "../../lib/adminUtils";
import ValidationAlert from "./ValidationAlert";
import Toast from "./Toast";
import Link from "next/link";

// Minimal JSON schema validator for screen schema
function validateScreenSchema(schema: unknown): string[] {
  const errors: string[] = [];

  // Type guard
  if (typeof schema !== "object" || schema === null) {
    errors.push("Schema must be an object");
    return errors;
  }

  const screenSchema = schema as Record<string, unknown>;

  // Required fields
  if (!screenSchema.screen_id) errors.push("screen_id is required");
  if (!screenSchema.layout) errors.push("layout is required");
  if (!screenSchema.components) errors.push("components is required");
  if (!screenSchema.state) errors.push("state is required");
  if (!screenSchema.bindings) errors.push("bindings is required");

  // Layout validation
  if (screenSchema.layout && typeof screenSchema.layout === "object") {
    const layout = screenSchema.layout as Record<string, unknown>;
    if (!layout.type) {
      errors.push("layout.type is required");
    } else if (typeof layout.type === "string" && !["grid", "form", "modal", "list", "dashboard", "stack"].includes(layout.type)) {
      errors.push(`layout.type must be one of: grid, form, modal, list, dashboard, stack (got: ${layout.type})`);
    }
  }

  // Components array validation
  if (screenSchema.components && Array.isArray(screenSchema.components)) {
    screenSchema.components.forEach((comp: unknown, idx: number) => {
      if (typeof comp === "object" && comp !== null) {
        const component = comp as Record<string, unknown>;
        if (!component.id) errors.push(`components[${idx}]: id is required`);
        if (!component.type) errors.push(`components[${idx}]: type is required`);
        if (typeof component.type === "string") {
          const validTypes = ["text", "markdown", "button", "input", "table", "chart", "badge", "tabs", "modal", "keyvalue", "divider"];
          if (!validTypes.includes(component.type)) {
            errors.push(`components[${idx}]: type must be one of: ${validTypes.join(", ")} (got: ${component.type})`);
          }
        }
      }
    });
  }

  return errors;
}

function parseTagsInput(value: string): Record<string, unknown> | null {
  if (!value.trim()) return null;
  try {
    const parsed = JSON.parse(value);
    if (typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error("Tags must be a JSON object");
    }
    return parsed;
  } catch (error: unknown) {
    const errMsg = error instanceof Error ? error.message : "Invalid JSON for tags";
    throw new Error(errMsg);
  }
}

interface ScreenAssetEditorProps {
  assetId: string;
}

export default function ScreenAssetEditor({ assetId }: ScreenAssetEditorProps) {
  const [asset, setAsset] = useState<Asset | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "warning" } | null>(null);

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    schema_json: "",
    tags: "",
  });

  const [schemaErrors, setSchemaErrors] = useState<string[]>([]);

  const fetchScreenAsset = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetchApi(`/asset-registry/assets/${assetId}`);
      const assetData = response.data as Asset;
      setAsset(assetData);
      setFormData({
        name: assetData.name || "",
        description: assetData.description || "",
        schema_json: JSON.stringify(assetData.schema_json || assetData.screen_schema || {}, null, 2),
        tags: assetData.tags ? JSON.stringify(assetData.tags, null, 2) : "",
      });
      setErrors([]);
      setSchemaErrors([]);
    } catch (error: unknown) {
      const errMsg = error instanceof Error ? error.message : "Failed to fetch screen asset";
      setErrors([errMsg]);
    } finally {
      setLoading(false);
    }
  }, [assetId]);

  useEffect(() => {
    fetchScreenAsset();
  }, [fetchScreenAsset]);

  const handleSaveDraft = async () => {
    if (!asset) return;

    setSaving(true);
    setErrors([]);
    setSchemaErrors([]);

    try {
      // Parse and validate schema
      let schema;
      try {
        schema = JSON.parse(formData.schema_json);
      } catch (e: unknown) {
        const errMsg = e instanceof Error ? e.message : "Invalid JSON in schema";
        setSchemaErrors(["Invalid JSON in schema: " + errMsg]);
        setSaving(false);
        return;
      }

      // Validate schema structure
      const validationErrors = validateScreenSchema(schema);
      if (validationErrors.length > 0) {
        setSchemaErrors(validationErrors);
        setSaving(false);
        return;
      }

      // Save
      let parsedTags = null;
      try {
        parsedTags = parseTagsInput(formData.tags);
      } catch (tagError: unknown) {
        const errMsg = tagError instanceof Error ? tagError.message : "Invalid tags JSON";
        setErrors([errMsg]);
        setSaving(false);
        return;
      }

      await fetchApi(`/asset-registry/assets/${assetId}`, {
        method: "PUT",
        body: JSON.stringify({
          name: formData.name,
          description: formData.description || null,
          schema_json: schema,
          tags: parsedTags,
        }),
      });

      setToast({ message: "Screen draft saved successfully", type: "success" });
      await fetchScreenAsset();
    } catch (error: unknown) {
      const errMsg = error instanceof Error ? error.message : "Failed to save screen";
      setErrors([errMsg]);
    } finally {
      setSaving(false);
    }
  };

  const handlePublish = async () => {
    if (!asset) return;

    // First validate and save current schema
    try {
      const schema = JSON.parse(formData.schema_json);
      const validationErrors = validateScreenSchema(schema);
      if (validationErrors.length > 0) {
        setSchemaErrors(validationErrors);
        return;
      }
    } catch (e: unknown) {
      const errMsg = e instanceof Error ? e.message : "Invalid JSON in schema";
      setSchemaErrors(["Invalid JSON in schema: " + errMsg]);
      return;
    }

    setPublishing(true);
    setErrors([]);

    try {
      // First save the draft
      const updatedSchema = JSON.parse(formData.schema_json);
      const validationErrors = validateScreenSchema(updatedSchema);
      if (validationErrors.length > 0) {
        setSchemaErrors(validationErrors);
        return;
      }
      let parsedTags = null;
      try {
        parsedTags = parseTagsInput(formData.tags);
      } catch (tagError: unknown) {
        const errMsg = tagError instanceof Error ? tagError.message : "Invalid tags JSON";
        setErrors([errMsg]);
        return;
      }
      await fetchApi(`/asset-registry/assets/${assetId}`, {
        method: "PUT",
        body: JSON.stringify({
          name: formData.name,
          description: formData.description || null,
          schema_json: updatedSchema,
          tags: parsedTags,
        }),
      });

      // Then publish
      await fetchApi(`/asset-registry/assets/${assetId}/publish`, {
        method: "POST",
      });

      setToast({ message: "Screen published successfully", type: "success" });
      setSchemaErrors([]);
      await fetchScreenAsset();
    } catch (error: unknown) {
      const errMsg = error instanceof Error ? error.message : "Failed to publish screen";
      setErrors([errMsg]);
    } finally {
      setPublishing(false);
    }
  };

  const handleRollback = async () => {
    if (!asset) return;
    if (!confirm("Are you sure you want to rollback this screen to draft?")) return;

    try {
      setErrors([]);
      await fetchApi(`/asset-registry/assets/${assetId}/unpublish`, {
        method: "POST",
      });

      setToast({ message: "Screen rolled back to draft", type: "success" });
      await fetchScreenAsset();
    } catch (error: unknown) {
      const errMsg = error instanceof Error ? error.message : "Failed to rollback screen";
      setErrors([errMsg]);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="inline-block animate-spin">
          <svg className="w-8 h-8 text-sky-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="text-center py-12">
        <p className="mb-4" style={{ color: "var(--muted-foreground)" }}>Screen not found</p>
        <Link href="/admin/screens" className="text-sky-400 hover:text-sky-300">
          Back to Screens
        </Link>
      </div>
    );
  }

  const isDraft = asset.status === "draft";

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link href="/admin/screens" className="text-sky-400 hover:text-sky-300 text-sm mb-2 block">
            ← Back to Screens
          </Link>
          <h1 className="text-2xl font-bold" style={{ color: "var(--foreground)" }}>{asset.name}</h1>
          <p className="text-sm" style={{ color: "var(--muted-foreground)" }}>{asset.screen_id}</p>
        </div>
        <div>
          <span className={`inline-flex px-3 py-1 rounded text-xs font-bold uppercase tracking-wider border ${
            asset.status === "published"
              ? "bg-emerald-950/50 text-emerald-300 border-emerald-800/50"
              : ""
          }`}
          style={asset.status !== "published" ? { backgroundColor: "rgba(30, 41, 59, 0.5)", color: "var(--muted-foreground)", borderColor: "rgba(51, 65, 85, 0.5)" } : undefined}>
            {asset.status} (v{asset.version})
          </span>
        </div>
      </div>

      {/* Errors */}
      {errors.length > 0 && (
        <ValidationAlert errors={errors} onClose={() => setErrors([])} />
      )}

      {/* Schema Validation Errors */}
      {schemaErrors.length > 0 && (
        <ValidationAlert
          errors={schemaErrors}
          onClose={() => setSchemaErrors([])}
        />
      )}

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}

      {/* Form */}
      <div className="grid grid-cols-2 gap-4">
        {/* Left: Metadata */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: "var(--foreground)" }}>
              Screen Name
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={e => setFormData({ ...formData, name: e.target.value })}
              disabled={!isDraft}
              className="w-full px-3 py-2 border rounded text-sm focus:outline-none focus:border-sky-500 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: "var(--surface-elevated)", borderColor: "var(--border-muted)", color: "var(--foreground)" }}
              data-testid="input-screen-name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: "var(--foreground)" }}>
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={e => setFormData({ ...formData, description: e.target.value })}
              disabled={!isDraft}
              className="w-full px-3 py-2 border rounded text-sm focus:outline-none focus:border-sky-500 disabled:opacity-50 disabled:cursor-not-allowed resize-none"
              style={{ backgroundColor: "var(--surface-elevated)", borderColor: "var(--border-muted)", color: "var(--foreground)" }}
              rows={6}
              data-testid="textarea-screen-description"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: "var(--foreground)" }}>
              Tags (JSON)
            </label>
            <textarea
              value={formData.tags}
              onChange={e => setFormData({ ...formData, tags: e.target.value })}
              disabled={!isDraft}
              className="w-full px-3 py-2 border rounded text-sm focus:outline-none focus:border-sky-500 disabled:opacity-50 disabled:cursor-not-allowed resize-none"
              style={{ backgroundColor: "var(--surface-elevated)", borderColor: "var(--border-muted)", color: "var(--foreground)" }}
              rows={2}
              placeholder='{"team":"ops","audience":"mobile"}'
              data-testid="textarea-screen-tags"
            />
          </div>

          <div className="rounded-lg p-4 border" style={{ backgroundColor: "rgba(2, 6, 23, 0.4)", borderColor: "var(--border)" }}>
            <h3 className="text-sm font-semibold mb-3" style={{ color: "var(--foreground)" }}>Metadata</h3>
            <div className="space-y-2 text-xs" style={{ color: "var(--muted-foreground)" }}>
              <div><strong>Asset ID:</strong> {asset.asset_id}</div>
              <div><strong>Type:</strong> screen</div>
              <div><strong>Version:</strong> {asset.version}</div>
              <div><strong>Created:</strong> {new Date(asset.created_at).toLocaleString()}</div>
              <div><strong>Updated:</strong> {new Date(asset.updated_at).toLocaleString()}</div>
              {asset.published_at && (
                <div><strong>Published:</strong> {new Date(asset.published_at).toLocaleString()}</div>
              )}
              {asset.tags && Object.keys(asset.tags).length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {Object.entries(asset.tags).map(([key, value]) => (
                    <span
                      key={key}
                      className="rounded-full border px-2 py-0.5 text-[10px]"
                      style={{ borderColor: "var(--border-muted)", color: "var(--foreground)" }}
                    >
                      {key}: {String(value)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right: Schema Editor */}
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2" style={{ color: "var(--foreground)" }}>
              Schema JSON (Read-only validation)
            </label>
            <textarea
              value={formData.schema_json}
              onChange={e => setFormData({ ...formData, schema_json: e.target.value })}
              disabled={!isDraft}
              className="w-full px-3 py-2 border rounded text-xs focus:outline-none font-mono resize-none disabled:opacity-50 disabled:cursor-not-allowed"
              style={{
                backgroundColor: "var(--surface-elevated)",
                color: "var(--foreground)",
                borderColor: schemaErrors.length > 0 ? "#dc2626" : "var(--border-muted)"
              }}
              rows={16}
              data-testid="textarea-schema-json"
            />
          </div>

          {schemaErrors.length > 0 && (
            <div className="bg-red-950/50 border border-red-800/50 rounded p-3">
              <p className="text-xs font-semibold text-red-300 mb-2">Schema Validation Errors:</p>
              <ul className="space-y-1 text-xs text-red-400">
                {schemaErrors.map((err, idx) => (
                  <li key={idx}>• {err}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-4">
        {isDraft && (
          <>
            <button
              onClick={handleSaveDraft}
              disabled={saving}
              className="px-4 py-2 rounded-lg transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-80"
              style={{ backgroundColor: "#334155", color: "var(--foreground)" }}
              data-testid="btn-save-draft"
            >
              {saving ? "Saving..." : "Save Draft"}
            </button>
            <button
              onClick={handlePublish}
              disabled={publishing || schemaErrors.length > 0}
              className="px-4 py-2 bg-sky-600 hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors text-sm font-medium"
              data-testid="btn-publish-screen"
            >
              {publishing ? "Publishing..." : "Publish"}
            </button>
          </>
        )}

        {asset.status === "published" && (
          <button
            onClick={handleRollback}
            className="px-4 py-2 bg-orange-700 hover:bg-orange-600 text-white rounded-lg transition-colors text-sm font-medium"
            data-testid="btn-rollback-screen"
          >
            Rollback to Draft
          </button>
        )}

        <Link
          href="/admin/screens"
          className="ml-auto px-4 py-2 rounded-lg transition-colors text-sm font-medium inline-block hover:opacity-80"
          style={{ backgroundColor: "#334155", color: "var(--foreground)" }}
        >
          Back
        </Link>
      </div>
    </div>
  );
}
