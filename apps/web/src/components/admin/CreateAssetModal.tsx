"use client";

import { useState } from "react";
import { fetchApi } from "../../lib/adminUtils";
import ValidationAlert from "./ValidationAlert";

interface CreateAssetModalProps {
  onClose: () => void;
  onSuccess: (assetId: string) => void;
}

export default function CreateAssetModal({ onClose, onSuccess }: CreateAssetModalProps) {
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState<"prompt" | "mapping" | "policy" | "query">("prompt");
  const [description, setDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const handleCreate = async () => {
    if (!name.trim()) {
      setErrors(["Asset name is required"]);
      return;
    }

    setIsCreating(true);
    setErrors([]);

    try {
      const response = await fetchApi<{ asset: { asset_id: string } }>("/asset-registry/assets", {
        method: "POST",
        body: JSON.stringify({
          name,
          asset_type: assetType,
          description: description || null,
        }),
      });

      onSuccess(response.data.asset.asset_id);
      onClose();
    } catch (err: any) {
      setErrors([err.message || "Failed to create asset"]);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
      <div className="bg-slate-900 rounded-2xl border border-slate-800 max-w-lg w-full overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between p-6 border-b border-slate-800">
          <h2 className="text-xl font-bold text-white">Initialize New Asset</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
          >
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 overflow-y-auto flex-1">
          {errors.length > 0 && (
            <ValidationAlert errors={errors} onClose={() => setErrors([])} />
          )}

          <div className="space-y-6">
            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 ml-1">
                Asset Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. general-intent-classifier"
                className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500 transition-all"
                autoFocus
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 ml-1">
                Asset Category
              </label>
              <div className="grid grid-cols-4 gap-3">
                {(["prompt", "mapping", "policy", "query"] as const).map((type) => (
                  <button
                    key={type}
                    onClick={() => setAssetType(type)}
                    className={`px-3 py-4 rounded-xl border text-sm font-bold capitalize transition-all ${
                      assetType === type
                        ? "bg-sky-600/20 border-sky-500 text-sky-400 shadow-lg shadow-sky-900/10"
                        : "bg-slate-950 border-slate-800 text-slate-500 hover:border-slate-700"
                    }`}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2 ml-1">
                Description (Optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Briefly describe the purpose of this asset..."
                rows={3}
                className="w-full px-4 py-3 bg-slate-950 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-600 focus:outline-none focus:border-sky-500 transition-all resize-none"
              />
            </div>
          </div>
        </div>

        <div className="p-6 border-t border-slate-800 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-3 text-slate-400 hover:text-white transition-colors font-bold uppercase tracking-widest text-xs"
          >
            Discard
          </button>
          <button
            onClick={handleCreate}
            disabled={isCreating}
            className="flex-[2] py-3 bg-sky-600 hover:bg-sky-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl transition-all font-bold shadow-lg shadow-sky-900/20 active:scale-95"
          >
            {isCreating ? "Initializing..." : "Create Draft"}
          </button>
        </div>
      </div>
    </div>
  );
}
