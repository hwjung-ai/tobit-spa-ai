"use client";

import { useState, useEffect } from "react";
import {
  Search,
  CheckCircle,
  AlertTriangle,
  X,
  Eye,
  RefreshCw,
  Play,
  Filter,
  X as CloseIcon,
  Clock,
  Check,
  Star,
  Trash2,
  Copy,
  Plus
} from "lucide-react";
import { cn } from "@/lib/utils";

interface AssetVersion {
  id: string;
  asset_id: string;
  version: string;
  name: string;
  description?: string;
  created_at: string;
  status: "published" | "draft" | "archived";
  author: string;
  size: number;
  metadata?: Record<string, unknown>;
}

interface AssetOverride {
  asset_type: string;
  asset_name: string;
  version: string;
  reason: string;
}

interface AssetOverrideModalProps {
  isOpen: boolean;
  onClose: () => void;
  traceId?: string;
  baselineTraceId?: string;
  availableAssets?: Record<string, AssetVersion[]>;
  onTestRun?: (overrides: AssetOverride[]) => void;
  currentOverrides?: AssetOverride[];
}

interface AssetTypeConfig {
  label: string;
  icon: React.ComponentType<unknown>;
  color: string;
}

const ASSET_TYPES: Record<string, AssetTypeConfig> = {
  prompt: {
    label: "Prompt",
    icon: Star,
    color: "bg-blue-500/10 border-blue-400/30 text-blue-400",
  },
  policy: {
    label: "Policy",
    icon: CheckCircle,
    color: "bg-emerald-500/10 border-emerald-400/30 text-emerald-400",
  },
  query: {
    label: "Query",
    icon: Search,
    color: "bg-purple-500/10 border-purple-400/30 text-purple-400",
  },
  mapping: {
    label: "Mapping",
    icon: Copy,
    color: "bg-amber-500/10 border-amber-400/30 text-amber-400",
  },
  screen: {
    label: "Screen",
    icon: Eye,
    color: "bg-rose-500/10 border-rose-400/30 text-rose-400",
  },
};

export default function AssetOverrideModal({
  isOpen,
  onClose,
  traceId,
  baselineTraceId,
  availableAssets = {},
  onTestRun,
  currentOverrides = [],
}: AssetOverrideModalProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedAssetType, setSelectedAssetType] = useState<string | null>(null);
  const [overrides, setOverrides] = useState<AssetOverride[]>(currentOverrides);
  const [isRunning, setIsRunning] = useState(false);
  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set());

  const assetTypes = Object.keys(availableAssets);

  useEffect(() => {
    if (isOpen) {
      setSelectedAssets(new Set());
      setSearchTerm("");
      setSelectedAssetType(null);
    }
  }, [isOpen]);

  const filteredAssets = selectedAssetType
    ? availableAssets[selectedAssetType]?.filter(asset =>
        asset.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        asset.asset_id.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : [];

  const handleAssetSelect = (assetType: string, asset: AssetVersion) => {
    const assetKey = `${assetType}:${asset.asset_id}`;
    const newSelected = new Set(selectedAssets);

    if (newSelected.has(assetKey)) {
      newSelected.delete(assetKey);
    } else {
      newSelected.add(assetKey);
    }

    setSelectedAssets(newSelected);
  };

  const addOverride = (assetType: string, asset: AssetVersion) => {
    if (!overrides.find(o => o.asset_type === assetType && o.asset_name === asset.asset_id)) {
      setOverrides([
        ...overrides,
        {
          asset_type: assetType,
          asset_name: asset.asset_id,
          version: asset.version,
          reason: `Testing version ${asset.version} for ${assetType}`,
        }
      ]);
    }
  };

  const removeOverride = (index: number) => {
    setOverrides(overrides.filter((_, i) => i !== index));
  };

  const clearOverrides = () => {
    setOverrides([]);
  };

  const handleTestRun = async () => {
    if (overrides.length === 0) return;

    setIsRunning(true);
    try {
      await onTestRun?.(overrides);
    } finally {
      setIsRunning(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const AssetItem = ({ asset, isSelected }: { asset: AssetVersion; isSelected: boolean }) => {
    const assetType = ASSET_TYPES[asset.asset_id.split(":")[0]] || ASSET_TYPES.prompt;
    const Icon = assetType.icon;

    return (
      <div
        className={cn(
          "p-3 rounded-lg border cursor-pointer transition-all hover:border-slate-600",
          isSelected
            ? "ring-2 ring-blue-400 border-blue-400/30"
            : "border-slate-700 hover:border-slate-600",
          assetType.color
        )}
        onClick={() => handleAssetSelect(asset.asset_id.split(":")[0], asset)}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-3">
            <div className={cn("p-1.5 rounded", assetType.color)}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-medium text-white">{asset.name}</h4>
              <p className="text-xs text-slate-400 mt-1">
                {asset.asset_id} • v{asset.version}
              </p>
              {asset.description && (
                <p className="text-xs text-slate-500 mt-1 line-clamp-1">
                  {asset.description}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={cn(
              "text-xs px-2 py-1 rounded-full",
              asset.status === "published" ? "bg-emerald-500/10 text-emerald-400" :
              asset.status === "draft" ? "bg-amber-500/10 text-amber-400" :
              "bg-slate-500/10 text-slate-400"
            )}>
              {asset.status}
            </span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                addOverride(asset.asset_id.split(":")[0], asset);
              }}
              className="p-1 rounded hover:bg-slate-700 transition"
              title="Add to overrides"
            >
              <Plus className="h-3 w-3" />
            </button>
          </div>
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-6xl h-[90vh] bg-slate-950 rounded-2xl border border-slate-800 shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-slate-800">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-white">Asset Override Test</h2>
              <p className="text-sm text-slate-400 mt-1">
                Test different asset versions to compare with baseline
                {traceId && (
                  <span className="ml-2 text-xs bg-slate-800 px-2 py-1 rounded">
                    Trace: {traceId.slice(0, 8)}...
                  </span>
                )}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-slate-800 transition"
            >
              <X className="h-5 w-5 text-slate-400" />
            </button>
          </div>
        </div>

        <div className="flex h-[calc(90vh-8rem)]">
          {/* Left Panel - Asset Selection */}
          <div className="w-1/2 border-r border-slate-800 flex flex-col">
            {/* Asset Type Filter */}
            <div className="p-4 border-b border-slate-800">
              <div className="flex items-center gap-2 mb-3">
                <Filter className="h-4 w-4 text-slate-400" />
                <h3 className="text-sm font-medium text-white">Asset Types</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {assetTypes.map((type) => {
                  const config = ASSET_TYPES[type];
                  const Icon = config.icon;
                  const hasAssets = availableAssets[type]?.length > 0;
                  const count = availableAssets[type]?.length || 0;

                  return (
                    <button
                      key={type}
                      onClick={() => setSelectedAssetType(
                        selectedAssetType === type ? null : type
                      )}
                      className={cn(
                        "flex items-center gap-2 px-3 py-1.5 rounded text-xs transition",
                        selectedAssetType === type
                          ? config.color
                          : hasAssets
                          ? "bg-slate-800 text-slate-300 hover:bg-slate-700"
                          : "bg-slate-800/50 text-slate-500 cursor-not-allowed"
                      )}
                      disabled={!hasAssets}
                    >
                      <Icon className="h-3 w-3" />
                      {config.label}
                      {count > 0 && (
                        <span className="px-1.5 py-0.5 rounded bg-slate-700">
                          {count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Search */}
            <div className="p-4 border-b border-slate-800">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search assets..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-slate-600"
                />
              </div>
            </div>

            {/* Asset List */}
            <div className="flex-1 overflow-auto p-4">
              {filteredAssets.length === 0 ? (
                <div className="flex items-center justify-center h-full text-slate-500">
                  <div className="text-center">
                    {selectedAssetType ? (
                      <>
                        <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
                        <p>No assets found for {selectedAssetType}</p>
                      </>
                    ) : (
                      <>
                        <Search className="h-8 w-8 mx-auto mb-2" />
                        <p>Select an asset type to view assets</p>
                      </>
                    )}
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredAssets.map((asset) => {
                    const isSelected = selectedAssets.has(
                      `${asset.asset_id.split(":")[0]}:${asset.asset_id}`
                    );
                    return (
                      <AssetItem key={asset.id} asset={asset} isSelected={isSelected} />
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Right Panel - Overrides & Test Run */}
          <div className="w-1/2 flex flex-col">
            {/* Current Overrides */}
            <div className="p-4 border-b border-slate-800">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-white">Active Overrides</h3>
                {overrides.length > 0 && (
                  <button
                    onClick={clearOverrides}
                    className="text-xs text-slate-400 hover:text-slate-300"
                  >
                    Clear All
                  </button>
                )}
              </div>

              {overrides.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <p>No overrides selected</p>
                  <p className="text-xs mt-1">Select assets from the left panel</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {overrides.map((override, index) => {
                    const assetType = ASSET_TYPES[override.asset_type] || ASSET_TYPES.prompt;
                    const Icon = assetType.icon;

                    return (
                      <div
                        key={index}
                        className={cn(
                          "p-3 rounded-lg border",
                          assetType.color
                        )}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                            <div className={cn("p-1.5 rounded", assetType.color)}>
                              <Icon className="h-4 w-4" />
                            </div>
                            <div className="flex-1">
                              <h4 className="text-sm font-medium text-white">
                                {override.asset_name}
                              </h4>
                              <p className="text-xs text-slate-400">
                                v{override.version}
                              </p>
                              <p className="text-xs text-slate-500 mt-1">
                                {override.reason}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => removeOverride(index)}
                            className="p-1 rounded hover:bg-slate-700 transition"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Baseline Comparison */}
            {baselineTraceId && (
              <div className="p-4 border-b border-slate-800">
                <h3 className="text-sm font-medium text-white mb-2">Baseline Comparison</h3>
                <div className="bg-slate-800/50 rounded-lg p-3 text-xs">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <CheckCircle className="h-4 w-4" />
                    <span>Baseline: {baselineTraceId.slice(0, 8)}...</span>
                  </div>
                  <p className="text-slate-400 mt-1">
                    Test results will be compared against this trace
                  </p>
                </div>
              </div>
            )}

            {/* Test Run Controls */}
            <div className="p-4 border-b border-slate-800">
              <button
                onClick={handleTestRun}
                disabled={overrides.length === 0 || isRunning}
                className={cn(
                  "w-full py-3 px-4 rounded-lg font-medium transition flex items-center justify-center gap-2",
                  overrides.length === 0 || isRunning
                    ? "bg-slate-800 text-slate-500 cursor-not-allowed"
                    : "bg-emerald-500 hover:bg-emerald-600 text-white"
                )}
              >
                {isRunning ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Running Test...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    Run Test with {overrides.length} Override{overrides.length !== 1 ? "s" : ""}
                  </>
                )}
              </button>

              {overrides.length > 0 && (
                <div className="mt-3 text-xs text-slate-400">
                  <p>• Test will run with selected asset overrides</p>
                  <p>• Results will be compared against baseline</p>
                  <p>• Performance metrics will be collected</p>
                </div>
              )}
            </div>

            {/* Expected Changes */}
            <div className="flex-1 p-4 overflow-auto">
              <h3 className="text-sm font-medium text-white mb-3">Expected Changes</h3>
              <div className="space-y-2 text-xs text-slate-400">
                <div className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5"></div>
                  <p>Asset versions will be temporarily overridden during test</p>
                </div>
                <div className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5"></div>
                  <p>Stage execution metrics will be collected and compared</p>
                </div>
                <div className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5"></div>
                  <p>Baseline vs test run comparison will be available</p>
                </div>
                <div className="flex items-start gap-2">
                  <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5"></div>
                  <p>Original trace will not be modified</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}