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
  const [assetType, setAssetType] = useState<"prompt" | "mapping" | "policy" | "query" | "source" | "resolver">("prompt");
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
          created_by: "admin", // Default to admin user
        }),
      });

      onSuccess(response.data.asset.asset_id);
      onClose();
    } catch (err: unknown) {
      setErrors([err instanceof Error ? err.message : "Failed to create asset"]);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm px-4">
      <div className=" rounded-2xl border  max-w-lg w-full overflow-hidden shadow-2xl flex flex-col max-h-[90vh]" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
        <div className="flex items-center justify-between p-6 border-b " style={{borderColor: "var(--border)"}}>
          <h2 className="text-xl font-bold text-white">Initialize New Asset</h2>
          <button
            onClick={onClose}
            className=" hover:text-white transition-colors" style={{color: "var(--muted-foreground)"}}
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
              <label className="block text-xs font-bold  uppercase tracking-widest mb-2 ml-1" style={{color: "var(--muted-foreground)"}}>
                Asset Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. general-intent-classifier"
                className="w-full px-4 py-3  border  rounded-xl  placeholder-slate-600 focus:outline-none focus:border-sky-500 transition-all" style={{borderColor: "var(--border)", color: "var(--foreground)", backgroundColor: "var(--surface-base)"}}
                autoFocus
              />
            </div>

            <div>
              <label className="block text-xs font-bold  uppercase tracking-widest mb-2 ml-1" style={{color: "var(--muted-foreground)"}}>
                Asset Category
              </label>
              <div className="grid grid-cols-3 gap-3">
                {(["prompt", "mapping", "policy", "query", "source", "resolver"] as const).map((type) => (
                  <button
                    key={type}
                    onClick={() => setAssetType(type)}
                    className={`px-3 py-4 rounded-xl border text-sm font-bold capitalize transition-all ${
                      assetType === type
                        ? "bg-sky-600/20 border-sky-500 text-sky-400 shadow-lg shadow-sky-900/10"
                        : "  0 hover:"
                    }`} style={{backgroundColor: "var(--surface-base)", color: "var(--foreground)", borderColor: "var(--border)"}}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold  uppercase tracking-widest mb-2 ml-1" style={{color: "var(--muted-foreground)"}}>
                Description (Optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Briefly describe the purpose of this asset..."
                rows={3}
                className="w-full px-4 py-3  border  rounded-xl  placeholder-slate-600 focus:outline-none focus:border-sky-500 transition-all resize-none" style={{borderColor: "var(--border)", color: "var(--foreground)", backgroundColor: "var(--surface-base)"}}
              />
            </div>
          </div>
        </div>

        <div className="p-6 border-t  flex gap-3" style={{borderColor: "var(--border)"}}>
          <button
            onClick={onClose}
            className="flex-1 py-3  hover:text-white transition-colors font-bold uppercase tracking-widest text-xs" style={{color: "var(--muted-foreground)"}}
          >
            Discard
          </button>
          <button
            onClick={handleCreate}
            disabled={isCreating}
            className="flex-[2] py-3 bg-sky-600 hover:bg-sky-500 disabled: disabled: text-white rounded-xl transition-all font-bold shadow-lg shadow-sky-900/20 active:scale-95 dark:bg-sky-700 dark:hover:bg-sky-600" style={{color: "var(--muted-foreground)", backgroundColor: "var(--surface-elevated)"}}
          >
            {isCreating ? "Initializing..." : "Create Draft"}
          </button>
        </div>
      </div>
    </div>
  );
}
