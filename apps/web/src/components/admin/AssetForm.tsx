"use client";

import { useState } from "react";
import { Asset, fetchApi } from "../../lib/adminUtils";
import ValidationAlert from "./ValidationAlert";
import Toast from "./Toast";

interface AssetFormProps {
    asset: Asset;
    onSave: () => void;
}

export default function AssetForm({ asset, onSave }: AssetFormProps) {
    const [formData, setFormData] = useState({
        name: asset.name,
        description: asset.description || "",
        template: asset.template || "",
        input_schema: asset.input_schema ? JSON.stringify(asset.input_schema, null, 2) : "",
        output_contract: asset.output_contract ? JSON.stringify(asset.output_contract, null, 2) : "",
        content: asset.content ? JSON.stringify(asset.content, null, 2) : "",
        limits: asset.limits ? JSON.stringify(asset.limits, null, 2) : "",
        query_sql: asset.query_sql || "",
        query_params: asset.query_params ? JSON.stringify(asset.query_params, null, 2) : "",
        query_metadata: asset.query_metadata ? JSON.stringify(asset.query_metadata, null, 2) : "",
    });

    const [isSaving, setIsSaving] = useState(false);
    const [isPublishing, setIsPublishing] = useState(false);
    const [isRollingBack, setIsRollingBack] = useState(false);
    const [errors, setErrors] = useState<string[]>([]);
    const [toast, setToast] = useState<{ message: string; type: "success" | "error" | "warning" } | null>(null);
    const [showRollbackModal, setShowRollbackModal] = useState(false);
    const [rollbackVersion, setRollbackVersion] = useState("");

    const handleDelete = async () => {
        if (!confirm("Are you sure you want to delete this draft asset? This action cannot be undone.")) return;
        setIsSaving(true);
        try {
            await fetchApi(`/asset-registry/assets/${asset.asset_id}`, { method: "DELETE" });
            window.location.href = "/admin/assets";
        } catch (err: unknown) {
            setErrors([err.message || "Failed to delete asset"]);
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
            setErrors([err.message || "Failed to rollback to draft"]);
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
            const payload: unknown = {
                name: formData.name,
                description: formData.description || null,
            };

            // Add type-specific fields
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
                if (formData.query_params.trim()) {
                    payload.query_params = JSON.parse(formData.query_params);
                }
                if (formData.query_metadata.trim()) {
                    payload.query_metadata = JSON.parse(formData.query_metadata);
                }
            }

            await fetchApi(`/asset-registry/assets/${asset.asset_id}`, {
                method: "PUT",
                body: JSON.stringify(payload),
            });

            setToast({ message: "Draft saved successfully", type: "success" });
            onSave();
        } catch (err: unknown) {
            setErrors([err.message || "Failed to save draft"]);
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
            setErrors([err.message || "Failed to publish asset"]);
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
            setErrors([err.message || "Failed to rollback asset"]);
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
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Basic Info</h2>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Name</label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            disabled={!isDraft}
                            className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Description</label>
                        <textarea
                            value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            disabled={!isDraft}
                            rows={3}
                            className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                        />
                    </div>

                    <div className="grid grid-cols-3 gap-4">
                        <div>
                            <label className="block text-xs text-slate-500 uppercase tracking-wider mb-1">Type</label>
                            <p className="text-slate-300 capitalize">{asset.asset_type}</p>
                        </div>
                        <div>
                            <label className="block text-xs text-slate-500 uppercase tracking-wider mb-1">Status</label>
                            <p className={`capitalize ${asset.status === 'published' ? 'text-green-400' : 'text-slate-400'}`}>
                                {asset.status}
                            </p>
                        </div>
                        <div>
                            <label className="block text-xs text-slate-500 uppercase tracking-wider mb-1">Version</label>
                            <p className="text-slate-300 font-mono">v{asset.version}</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Type-specific Content */}
            <div className="bg-slate-900 rounded-lg border border-slate-800 p-6">
                <h2 className="text-lg font-semibold text-white mb-4">Content</h2>

                {asset.asset_type === "prompt" && (
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">Template</label>
                            <textarea
                                value={formData.template}
                                onChange={(e) => setFormData({ ...formData, template: e.target.value })}
                                disabled={!isDraft}
                                rows={6}
                                placeholder="Enter prompt template..."
                                className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Input Schema (JSON)</label>
                                <textarea
                                    value={formData.input_schema}
                                    onChange={(e) => setFormData({ ...formData, input_schema: e.target.value })}
                                    disabled={!isDraft}
                                    rows={6}
                                    placeholder="{}"
                                    className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Output Contract (JSON)</label>
                                <textarea
                                    value={formData.output_contract}
                                    onChange={(e) => setFormData({ ...formData, output_contract: e.target.value })}
                                    disabled={!isDraft}
                                    rows={6}
                                    placeholder="{}"
                                    className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                                />
                            </div>
                        </div>
                    </div>
                )}

                {asset.asset_type === "mapping" && (
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Content (JSON)</label>
                        <textarea
                            value={formData.content}
                            onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                            disabled={!isDraft}
                            rows={12}
                            placeholder="{}"
                            className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                        />
                    </div>
                )}

                {asset.asset_type === "policy" && (
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-2">Limits (JSON)</label>
                        <textarea
                            value={formData.limits}
                            onChange={(e) => setFormData({ ...formData, limits: e.target.value })}
                            disabled={!isDraft}
                            rows={12}
                            placeholder="{}"
                            className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                        />
                    </div>
                )}

                {asset.asset_type === "query" && (
                    <div className="space-y-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-300 mb-2">SQL Query (SELECT only)</label>
                            <textarea
                                value={formData.query_sql}
                                onChange={(e) => setFormData({ ...formData, query_sql: e.target.value })}
                                disabled={!isDraft}
                                rows={12}
                                placeholder="SELECT ..."
                                className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Query Parameters (JSON)</label>
                                <textarea
                                    value={formData.query_params}
                                    onChange={(e) => setFormData({ ...formData, query_params: e.target.value })}
                                    disabled={!isDraft}
                                    rows={6}
                                    placeholder="{}"
                                    className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-300 mb-2">Query Metadata (JSON)</label>
                                <textarea
                                    value={formData.query_metadata}
                                    onChange={(e) => setFormData({ ...formData, query_metadata: e.target.value })}
                                    disabled={!isDraft}
                                    rows={6}
                                    placeholder="{}"
                                    className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 font-mono text-sm disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:border-sky-500 transition-colors"
                                />
                            </div>
                        </div>
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
                            className="px-6 py-2 bg-slate-700 hover:bg-slate-600 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-lg transition-colors font-medium border border-slate-600"
                        >
                            {isSaving ? "Saving..." : "Save Draft"}
                        </button>
                        <button
                            onClick={handlePublish}
                            disabled={isPublishing}
                            className="px-6 py-2 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg transition-colors font-medium shadow-lg shadow-sky-900/20"
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
                            className="px-6 py-2 bg-slate-800 text-slate-300 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors font-medium"
                        >
                            Version Rollback...
                        </button>
                    </>
                )}
            </div>

            {/* Rollback Modal */}
            {showRollbackModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
                    <div className="bg-slate-900 rounded-lg border border-slate-800 max-w-md w-full p-6 shadow-2xl">
                        <h2 className="text-lg font-semibold text-white mb-2">Rollback Asset</h2>
                        <p className="text-slate-400 text-sm mb-6 leading-relaxed">
                            Enter the version number to rollback to. This will move the <strong>published status</strong> to the selected version and increment the version number.
                        </p>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-xs text-slate-500 uppercase tracking-wider mb-2">Version Number</label>
                                <input
                                    type="number"
                                    min="1"
                                    value={rollbackVersion}
                                    onChange={(e) => setRollbackVersion(e.target.value)}
                                    placeholder="e.g. 1"
                                    className="w-full px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-sky-500 transition-colors"
                                />
                            </div>
                            <div className="flex items-center justify-end gap-3 pt-2">
                                <button
                                    onClick={() => {
                                        setShowRollbackModal(false);
                                        setRollbackVersion("");
                                    }}
                                    className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleRollback}
                                    disabled={isRollingBack}
                                    className="px-6 py-2 bg-yellow-600 hover:bg-yellow-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg transition-colors font-medium"
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
                    onClose={() => setToast(null)}
                />
            )}
        </div>
    );
}
