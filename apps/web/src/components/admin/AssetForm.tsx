"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Asset, fetchApi } from "../../lib/adminUtils";
import ValidationAlert from "./ValidationAlert";
import Toast from "./Toast";
import SourceAssetForm from "./SourceAssetForm";
import SchemaAssetForm from "./SchemaAssetForm";
import ResolverAssetForm from "./ResolverAssetForm";
import type { SourceAssetResponse, SchemaAssetResponse, ResolverAssetResponse, SourceType } from "../../types/asset-registry";
import { isSourceAsset, isSchemaAsset, isResolverAsset } from "../../types/asset-registry";

interface AssetFormProps {
    asset: Asset;
    onSave: () => void;
    onLoadVersion?: (version: number) => void;
}

export default function AssetForm({ asset, onSave, onLoadVersion }: AssetFormProps) {
    const [formData, setFormData] = useState({
        name: asset.name,
        description: asset.description || "",
        template: asset.template || "",
        input_schema: asset.input_schema ? JSON.stringify(asset.input_schema, null, 2) : "",
        output_contract: asset.output_contract ? JSON.stringify(asset.output_contract, null, 2) : "",
        content: asset.content ? JSON.stringify(asset.content, null, 2) : "",
        limits: asset.limits ? JSON.stringify(asset.limits, null, 2) : "",
        query_sql: asset.query_sql || "",
        query_cypher: (asset as Record<string, unknown>).query_cypher || "",
        query_http: (asset as Record<string, unknown>).query_http ? JSON.stringify((asset as Record<string, unknown>).query_http, null, 2) : "",
        query_params: asset.query_params ? JSON.stringify(asset.query_params, null, 2) : "",
        query_metadata: asset.query_metadata ? JSON.stringify(asset.query_metadata, null, 2) : '{"source_type":"postgresql","source_ref":"","tool_type":"","operation":""}',
        tags: asset.tags ? JSON.stringify(asset.tags, null, 2) : "",
    });

    const queryMetadata = useMemo(() => {
        try {
            return JSON.parse(formData.query_metadata || "{}");
        } catch {
            return { source_type: "postgresql" as SourceType, source_ref: "", tool_type: "", operation: "" };
        }
    }, [formData.query_metadata]);

    const [isSaving, setIsSaving] = useState(false);
    const [isPublishing, setIsPublishing] = useState(false);
    const [isRollingBack, setIsRollingBack] = useState(false);
    const [errors, setErrors] = useState<string[]>([]);
    const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "warning" } | null>(null);
    const [showRollbackModal, setShowRollbackModal] = useState(false);
    const [rollbackVersion, setRollbackVersion] = useState("");
    const [selectedVersion, setSelectedVersion] = useState<number>(asset.version);

    const handleDelete = async () => {
        if (!confirm("Are you sure you want to delete this draft asset? This action cannot be undone.")) return;
        setIsSaving(true);
        try {
            await fetchApi(`/asset-registry/assets/${asset.asset_id}`, { method: "DELETE" });
            window.location.href = "/admin/assets";
        } catch (err: unknown) {
            setErrors([err instanceof Error ? err.message : "Failed to delete asset"]);
        } finally {
            setIsSaving(false);
        }
    };

    const handleUnpublish = async () => {
        if (!confirm("Are you sure you want to rollback this asset to draft? It will no longer be active until re-published.")) return;
        setIsRollingBack(true);
        try {
            await fetchApi(`/asset-registry/assets/${asset.asset_id}/unpublish`, { method: "POST" });
            setToast({ message: "Asset returned to draft status", type: "success" });
            onSave();
        } catch (err: unknown) {
            setErrors([err instanceof Error ? err.message : "Failed to rollback to draft"]);
        } finally {
            setIsRollingBack(false);
        }
    };

    const isDraft = asset.status === "draft";

    const handleSaveDraft = async () => {
        if (!isDraft) {
            setErrors(["Cannot update published asset. Create new draft first."]);
            return;
        }

        setErrors([]);
        setIsSaving(true);

        try {
            const payload: Record<string, unknown> = {
                name: formData.name,
                description: formData.description || null,
            };

            if (asset.asset_type === "prompt") {
                payload.template = formData.template || null;
                if (formData.input_schema.trim()) {
                    payload.input_schema = JSON.parse(formData.input_schema);
                }
                if (formData.output_contract.trim()) {
                    payload.output_contract = JSON.parse(formData.output_contract);
                }
            } else if (asset.asset_type === "mapping") {
                if (formData.content.trim()) {
                    payload.content = JSON.parse(formData.content);
                }
            } else if (asset.asset_type === "policy") {
                if (formData.limits.trim()) {
                    payload.limits = JSON.parse(formData.limits);
                }
            } else if (asset.asset_type === "query") {
                payload.query_sql = formData.query_sql || null;
                payload.query_cypher = formData.query_cypher || null;
                if (formData.query_http.trim()) {
                    payload.query_http = JSON.parse(formData.query_http);
                }
                if (formData.query_params.trim()) {
                    payload.query_params = JSON.parse(formData.query_params);
                }
                if (formData.query_metadata.trim()) {
                    payload.query_metadata = JSON.parse(formData.query_metadata);
                }
            } else if (asset.asset_type === "screen") {
                if (formData.content.trim()) {
                    payload.content = JSON.parse(formData.content);
                    payload.screen_schema = payload.content;
                }
                if (formData.tags.trim()) {
                    payload.tags = JSON.parse(formData.tags);
                }
            }

            await fetchApi(`/asset-registry/assets/${asset.asset_id}`, {
                method: "PUT",
                body: JSON.stringify(payload),
            });

            setToast({ message: "Draft saved successfully", type: "success" });
            onSave();
        } catch (err: unknown) {
            setErrors([err instanceof Error ? err.message : "Failed to save draft"]);
        } finally {
            setIsSaving(false);
        }
    };

    const handlePublish = async () => {
        if (!isDraft) {
            setErrors(["Asset is already published"]);
            return;
        }

        setErrors([]);
        setIsPublishing(true);

        try {
            await fetchApi(`/asset-registry/assets/${asset.asset_id}/publish`, {
                method: "POST",
                body: JSON.stringify({ published_by: "admin" }),
            });

            setToast({ message: "Asset published successfully", type: "success" });
            onSave();
        } catch (err: unknown) {
            setErrors([err instanceof Error ? err.message : "Failed to publish asset"]);
        } finally {
            setIsPublishing(false);
        }
    };

    const handleRollback = async () => {
        if (isDraft) {
            setErrors(["Cannot rollback draft asset"]);
            return;
        }

        const version = parseInt(rollbackVersion, 10);
        if (isNaN(version) || version < 1) {
            setErrors(["Please enter a valid version number"]);
            return;
        }

        setErrors([]);
        setIsRollingBack(true);

        try {
            await fetchApi(
                `/asset-registry/assets/${asset.asset_id}/rollback?to_version=${version}&executed_by=admin`,
                { method: "POST" }
            );

            setToast({ message: `Rolled back to version ${version}`, type: "success" });
            setShowRollbackModal(false);
            setRollbackVersion("");
            onSave();
        } catch (err: unknown) {
            setErrors([err instanceof Error ? err.message : "Failed to rollback asset"]);
        } finally {
            setIsRollingBack(false);
        }
    };

    return (
        <div className="space-y-6">
            {errors.length > 0 && (
                <ValidationAlert errors={errors} onClose={() => setErrors([])} />
            )}

            {/* Basic Info */}
            <div className="rounded-lg border p-6 bg-surface-base border-variant">
                <h2 className="text-lg font-semibold mb-4 text-foreground">Basic Info</h2>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-2 text-foreground">Name</label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            disabled={!isDraft}
                            className="w-full px-4 py-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2 text-foreground">Description</label>
                        <textarea
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            disabled={!isDraft}
                            rows={3}
                            className="w-full px-4 py-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                        />
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                        <div>
                            <label className="block text-xs uppercase tracking-wider mb-1 text-muted-foreground">Type</label>
                            <p className="capitalize text-foreground">{asset.asset_type}</p>
                        </div>
                        <div>
                            <label className="block text-xs uppercase tracking-wider mb-1 text-muted-foreground">Status</label>
                            <p className={`capitalize ${asset.status === 'published' ? 'text-green-400' : 'text-muted-foreground'}`}
                            >
                                {asset.status}
                            </p>
                        </div>
                    <div>
                        <label className="block text-xs uppercase tracking-wider mb-1 text-muted-foreground">Version</label>
                        <div className="flex items-center gap-2">
                            <select
                                value={selectedVersion}
                                onChange={(e) => {
                                    const version = parseInt(e.target.value, 10);
                                    setSelectedVersion(version);
                                    if (onLoadVersion) {
                                        onLoadVersion(version);
                                    }
                                }}
                                className="px-3 py-1 border rounded-lg font-mono text-sm focus:outline-none focus:border-sky-500 bg-surface-base text-foreground border-variant"
                            >
                                <option value={asset.version}>v{asset.version} (current)</option>
                            </select>
                            <button
                                onClick={() => {
                                    setSelectedVersion(asset.version);
                                    if (onLoadVersion) {
                                        onLoadVersion(asset.version);
                                    }
                                }}
                                className="text-xs text-sky-400 hover:text-sky-300"
                                title="View all versions"
                            >
                                History...
                            </button>
                        </div>
                    </div>
                    </div>
                </div>
            </div>

            {/* Type-specific Content */}
            <div className="rounded-lg border p-6 bg-surface-base border-variant">
                <h2 className="text-lg font-semibold mb-4 text-foreground">Content</h2>

                {asset.asset_type === "source" && isSourceAsset(asset) && (
                    <SourceAssetForm asset={asset as SourceAssetResponse} onSave={onSave} />
                )}

                {asset.asset_type === "catalog" && isSchemaAsset(asset) && (
                    <SchemaAssetForm asset={asset as SchemaAssetResponse} onSave={onSave} />
                )}

                {asset.asset_type === "resolver" && isResolverAsset(asset) && (
                    <ResolverAssetForm asset={asset as ResolverAssetResponse} onSave={onSave} />
                )}

                {asset.asset_type === "prompt" && (
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium mb-2 text-foreground">Template</label>
                            <textarea
                                value={formData.template}
                                onChange={(e) => setFormData({ ...formData, template: e.target.value })}
                                disabled={!isDraft}
                                rows={6}
                                placeholder="Enter prompt template..."
                                className="w-full px-4 py-2 border rounded-lg font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-2 text-foreground">Input Schema (JSON)</label>
                                <textarea
                                    value={formData.input_schema}
                                    onChange={(e) => setFormData({ ...formData, input_schema: e.target.value })}
                                    disabled={!isDraft}
                                    rows={6}
                                    placeholder="{}"
                                    className="w-full px-4 py-2 border rounded-lg font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2 text-foreground">Output Contract (JSON)</label>
                                <textarea
                                    value={formData.output_contract}
                                    onChange={(e) => setFormData({ ...formData, output_contract: e.target.value })}
                                    disabled={!isDraft}
                                    rows={6}
                                    placeholder="{}"
                                    className="w-full px-4 py-2 border rounded-lg font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                                />
                            </div>
                        </div>
                    </div>
                )}

                {asset.asset_type === "mapping" && (
                    <div>
                        <label className="block text-sm font-medium mb-2 text-foreground">Content (JSON)</label>
                        <textarea
                            value={formData.content}
                            onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                            disabled={!isDraft}
                            rows={12}
                            placeholder="{}"
                            className="w-full px-4 py-2 border rounded-lg bg-surface-base text-foreground border-variant font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                        />
                    </div>
                )}

                {asset.asset_type === "policy" && (
                    <div>
                        <label className="block text-sm font-medium mb-2 text-foreground">Limits (JSON)</label>
                        <textarea
                            value={formData.limits}
                            onChange={(e) => setFormData({ ...formData, limits: e.target.value })}
                            disabled={!isDraft}
                            rows={12}
                            placeholder="{}"
                            className="w-full px-4 py-2 border rounded-lg bg-surface-base text-foreground border-variant font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                        />
                    </div>
                )}

                {asset.asset_type === "query" && (
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-2 text-foreground">Source Type</label>
                                <select
                                    value={queryMetadata.source_type || "postgresql"}
                                    onChange={(e) => {
                                        const newMetadata = { ...queryMetadata, source_type: e.target.value as SourceType };
                                        setFormData({ ...formData, query_metadata: JSON.stringify(newMetadata, null, 2) });
                                    }}
                                    disabled={!isDraft}
                                    className="w-full px-4 py-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                                >
                                    <option value="postgresql">PostgreSQL</option>
                                    <option value="mysql">MySQL</option>
                                    <option value="bigquery">Google BigQuery</option>
                                    <option value="snowflake">Snowflake</option>
                                    <option value="neo4j">Neo4j</option>
                                    <option value="rest_api">REST API</option>
                                    <option value="graphql_api">GraphQL API</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2 text-foreground">Source Asset Reference</label>
                                <input
                                    type="text"
                                    value={queryMetadata.source_ref || ""}
                                    onChange={(e) => {
                                        const newMetadata = { ...queryMetadata, source_ref: e.target.value };
                                        setFormData({ ...formData, query_metadata: JSON.stringify(newMetadata, null, 2) });
                                    }}
                                    disabled={!isDraft}
                                    placeholder="e.g., primary_postgres, neo4j_main"
                                    className="w-full px-4 py-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                                />
                            </div>
                        </div>

                        {(queryMetadata.source_type === "postgresql" || queryMetadata.source_type === "mysql" ||
                          queryMetadata.source_type === "bigquery" || queryMetadata.source_type === "snowflake") && (
                            <div>
                                <label className="block text-sm font-medium mb-2 text-foreground">SQL Query</label>
                                <textarea
                                    value={formData.query_sql}
                                    onChange={(e) => setFormData({ ...formData, query_sql: e.target.value })}
                                    disabled={!isDraft}
                                    rows={12}
                                    placeholder="SELECT ..."
                                    className="w-full px-4 py-2 border rounded-lg font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                                />
                            </div>
                        )}

                        {queryMetadata.source_type === "neo4j" && (
                            <div>
                                <label className="block text-sm font-medium mb-2 text-foreground">Cypher Query</label>
                                <textarea
                                    value={formData.query_cypher}
                                    onChange={(e) => setFormData({ ...formData, query_cypher: e.target.value })}
                                    disabled={!isDraft}
                                    rows={12}
                                    placeholder="MATCH (ci:CI) RETURN ci"
                                    className="w-full px-4 py-2 border rounded-lg font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                                />
                            </div>
                        )}

                        {(queryMetadata.source_type === "rest_api" || queryMetadata.source_type === "graphql_api") && (
                            <div className="space-y-4">
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm font-medium mb-2 text-foreground">HTTP Method</label>
                                        <select
                                            value={JSON.parse(formData.query_http || "{}").method || "GET"}
                                            onChange={(e) => {
                                                const httpConfig = JSON.parse(formData.query_http || "{}");
                                                setFormData({ ...formData, query_http: JSON.stringify({ ...httpConfig, method: e.target.value }, null, 2) });
                                            }}
                                            disabled={!isDraft}
                                            className="w-full px-4 py-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                                        >
                                            <option value="GET">GET</option>
                                            <option value="POST">POST</option>
                                            <option value="PUT">PUT</option>
                                            <option value="DELETE">DELETE</option>
                                            <option value="PATCH">PATCH</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-sm font-medium mb-2 text-foreground">Path</label>
                                        <input
                                            type="text"
                                            value={JSON.parse(formData.query_http || "{}").path || ""}
                                            onChange={(e) => {
                                                const httpConfig = JSON.parse(formData.query_http || "{}");
                                                setFormData({ ...formData, query_http: JSON.stringify({ ...httpConfig, path: e.target.value }, null, 2) });
                                            }}
                                            disabled={!isDraft}
                                            placeholder="/api/v1/servers"
                                            className="w-full px-4 py-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-2 text-foreground">Response Mapping (JSONPath)</label>
                                    <textarea
                                        value={formData.query_http}
                                        onChange={(e) => setFormData({ ...formData, query_http: e.target.value })}
                                        disabled={!isDraft}
                                        rows={6}
                                        placeholder='{"items": "$.data.servers[*]", "fields": {"id": "$.id", "name": "$.name"}}'
                                        className="w-full px-4 py-2 border rounded-lg font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                                    />
                                </div>
                            </div>
                        )}

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-2 text-foreground">Query Parameters (JSON)</label>
                                <textarea
                                    value={formData.query_params}
                                    onChange={(e) => setFormData({ ...formData, query_params: e.target.value })}
                                    disabled={!isDraft}
                                    rows={6}
                                    placeholder="{}"
                                    className="w-full px-4 py-2 border rounded-lg font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-2 text-foreground">Query Metadata (JSON)</label>
                                <textarea
                                    value={formData.query_metadata}
                                    onChange={(e) => setFormData({ ...formData, query_metadata: e.target.value })}
                                    disabled={!isDraft}
                                    rows={6}
                                    placeholder='{"source_type": "postgresql", "source_ref": "primary_postgres", "tool_type": "metric", "operation": "aggregate_by_ci"}'
                                    className="w-full px-4 py-2 border rounded-lg font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                                />
                            </div>
                        </div>
                    </div>
                )}

                {asset.asset_type === "screen" && (
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium mb-2 text-foreground">Screen ID</label>
                            <input
                                type="text"
                                value={asset.screen_id || ""}
                                disabled
                                className="w-full px-4 py-2 border rounded-lg disabled:opacity-50 disabled:cursor-not-allowed font-mono text-sm bg-surface-base text-foreground border-variant"
                            />
                            <p className="text-xs mt-1 text-muted-foreground">Stable identifier for screen (immutable)</p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2 text-foreground">Screen Schema (JSON)</label>
                            <textarea
                                value={formData.content}
                                onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                                disabled={!isDraft}
                                rows={16}
                                placeholder="{}"
                                className="w-full px-4 py-2 border rounded-lg bg-surface-base text-foreground border-variant font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none transition-colors"
                            />
                            <p className="text-xs mt-1 text-muted-foreground">UI definition following screen.schema.json format</p>
                        </div>

                        <div>
                            <label className="block text-sm font-medium mb-2 text-foreground">Tags (JSON)</label>
                            <textarea
                                value={formData.tags || ""}
                                onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
                                disabled={!isDraft}
                                rows={4}
                                placeholder="{}"
                                className="w-full px-4 py-2 border rounded-lg font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors bg-surface-base text-foreground border-variant"
                            />
                            <p className="text-xs mt-1 text-muted-foreground">Optional metadata tags (e.g., {`{"category": "maintenance"}`})</p>
                        </div>

                        <div className="flex items-center justify-between rounded-lg p-4 border bg-surface-base/50 border-variant"
                        >
                            <div className="space-y-1">
                                <p className="text-sm font-medium text-foreground">Screen Editor</p>
                                <p className="text-xs text-muted-foreground">Use the visual screen editor for better UX</p>
                            </div>
                            <Link
                                href={`/admin/screens/${asset.asset_id}`}
                                className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded-lg transition-colors font-medium text-sm dark:bg-sky-700 dark:hover:bg-sky-600"
                            >
                                Open Screen Editor →
                            </Link>
                        </div>
                    </div>
                )}

                {!["prompt", "mapping", "policy", "query", "source", "resolver"].includes(asset.asset_type) && (
                    <div className="space-y-3 text-sm text-muted-foreground">
                        <p>
                            이 Asset 타입은 현재 Admin Assets 화면에서 편집을 지원하지 않습니다.
                            전용 관리 UI 또는 API를 사용하세요.
                        </p>
                        {asset.content && (
                            <details
                                className="border rounded-xl p-3 bg-surface-base/60 border-variant"
                            >
                                <summary className="text-sm font-semibold cursor-pointer text-foreground">
                                    Raw Asset Content
                                </summary>
                                <pre className="mt-2 text-xs overflow-x-auto max-h-64 text-foreground">
                                    {JSON.stringify(asset.content, null, 2)}
                                </pre>
                            </details>
                        )}
                    </div>
                )}
            </div>

            {/* Actions */}
            <div className="flex items-center justify-end gap-3">
                {isDraft ? (
                    <>
                        <button
                            onClick={handleDelete}
                            disabled={isSaving}
                            className="px-6 py-2 bg-rose-950/20 text-rose-500 hover:bg-rose-950/40 border border-rose-800/50 rounded-lg transition-colors font-medium mr-auto"
                        >
                            Delete Draft
                        </button>
                        <button
                            onClick={handleSaveDraft}
                            disabled={isSaving}
                            className="px-6 py-2 rounded-lg transition-colors font-medium border text-foreground disabled:opacity-50 hover:opacity-80"

                        >
                            {isSaving ? "Saving..." : "Save Draft"}
                        </button>
                        <button
                            onClick={handlePublish}
                            disabled={isPublishing}
                            className="px-6 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg transition-colors font-medium shadow-lg shadow-sky-900/20"
                        >
                            {isPublishing ? "Publishing..." : "Publish"}
                        </button>
                    </>
                ) : (
                    <>
                        <button
                            onClick={handleUnpublish}
                            disabled={isRollingBack}
                            className="px-6 py-2 bg-amber-950/20 text-amber-500 hover:bg-amber-950/40 border border-amber-800/50 rounded-lg transition-colors font-medium"
                        >
                            {isRollingBack ? "Rolling back..." : "Rollback to Draft"}
                        </button>
                        <button
                            onClick={() => setShowRollbackModal(true)}
                            className="px-6 py-2 rounded-lg transition-colors font-medium border bg-surface-elevated text-foreground border-muted hover:bg-surface-elevated/80"
                        >
                            Version Rollback...
                        </button>
                    </>
                )}
            </div>

            {/* Rollback Modal */}
            {showRollbackModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
                    <div className="rounded-lg border max-w-md w-full p-6 shadow-2xl bg-surface-base border-variant"
                    >
                        <h2 className="text-lg font-semibold mb-2 text-foreground">Rollback Asset</h2>
                        <p className="text-sm mb-6 leading-relaxed text-muted-foreground">
                            Enter version number to rollback to. This will move the <strong>published status</strong> to the selected version and increment the version number.
                        </p>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-xs uppercase tracking-wider mb-2 text-muted-foreground">Version Number</label>
                                <input
                                    type="number"
                                    min="1"
                                    value={rollbackVersion}
                                    onChange={(e) => setRollbackVersion(e.target.value)}
                                    placeholder="e.g. 1"
                                    className="w-full px-4 py-2 border rounded-lg bg-surface-base text-foreground border-variant focus:outline-none focus:border-sky-500 transition-colors"
                                />
                            </div>
                            <div className="flex items-center justify-end gap-3 pt-2">
                                <button
                                    onClick={() => {
                                        setShowRollbackModal(false);
                                        setRollbackVersion("");
                                    }}
                                    className="px-4 py-2 hover:text-foreground transition-colors text-muted-foreground"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleRollback}
                                    disabled={isRollingBack}
                                    className="px-6 py-2 bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg transition-colors font-medium disabled:opacity-50"
                                >
                                    {isRollingBack ? "Rolling back..." : "Execute Rollback"}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Toast */}
            {toast && (
                <Toast
                    message={toast.message}
                    type={toast.type}
                    onDismiss={() => setToast(null)}
                />
            )}
        </div>
    );
}
