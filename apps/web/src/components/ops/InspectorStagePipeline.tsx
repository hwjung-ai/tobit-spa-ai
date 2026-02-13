"use client";

import React, { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle, Clock, Star, FileText, Shield, Map, Database, Layers, Sliders, Search, X, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import type { StageStatus as StageStatusType, StageSnapshot as StageSnapshotType } from "@/lib/apiClientTypes";

export type StageStatus = StageStatusType;

interface AppliedAssets {
  prompt?: string | null;
  policy?: string | null;
  mapping?: string | null;
  source?: string | null;
  schema?: string | null;
  resolver?: string | null;
  query?: string | null;
  [key: string]: string | null | undefined;
}

interface AssetDetail {
  id: string;
  type: string;
  name: string;
  version: string;
  fullId: string;
}

interface StagePipelineProps {
  className?: string;
  traceId?: string;
  stages: StageSnapshotType[];
  onStageSelect?: (stage: StageSnapshotType) => void;
  showAssets?: boolean;  // asset 카드 표시 여부 (OPS: false, INSPECTOR: true)
  // asset 레지스트리에서 조회한 이름 정보 (선택 사항)
  assetNames?: Record<string, { name: string; version?: string }>;
}

const STATUS_STYLES: Record<StageStatusType, { badge: string; icon: React.ReactElement }> = {
  pending: { badge: "bg-surface-elevated text-muted-foreground", icon: <Clock className="h-3 w-3 text-muted-foreground" /> },
  ok: { badge: "bg-emerald-500/10 text-emerald-400", icon: <CheckCircle className="h-3 w-3" /> },
  warning: { badge: "bg-amber-500/10 text-amber-400", icon: <AlertTriangle className="h-3 w-3" /> },
  error: { badge: "bg-rose-500/10 text-rose-400", icon: <AlertTriangle className="h-3 w-3" /> },
  skipped: { badge: "bg-surface-elevated text-muted-foreground", icon: <Clock className="h-3 w-3 text-muted-foreground" /> },
};

const STAGE_STYLES: Record<string, string> = {
  route_plan: "border-sky-400/50 bg-sky-500/10",
  validate: "border-emerald-400/50 bg-emerald-500/10",
  execute: "border-amber-400/50 bg-amber-500/10",
  compose: "border-purple-400/50 bg-purple-500/10",
  present: "border-rose-400/50 bg-rose-500/10",
};

const ASSET_CONFIG: Record<string, { icon: React.ReactElement; color: string; label: string }> = {
  prompt: { icon: <Star className="h-3 w-3" />, color: "text-sky-400", label: "Prompt" },
  policy: { icon: <Shield className="h-3 w-3" />, color: "text-emerald-400", label: "Policy" },
  query: { icon: <Search className="h-3 w-3" />, color: "text-purple-400", label: "Query" },
  mapping: { icon: <Map className="h-3 w-3" />, color: "text-amber-400", label: "Mapping" },
  source: { icon: <Database className="h-3 w-3" />, color: "text-foreground", label: "Source" },
  schema: { icon: <Layers className="h-3 w-3" />, color: "text-fuchsia-300", label: "Schema" },
  resolver: { icon: <Sliders className="h-3 w-3" />, color: "text-orange-300", label: "Resolver" },
};

const prettyJson = (value: unknown) => JSON.stringify(value, null, 2);

// Asset 이름 가져오기 (UUID -> 이름)
function getAssetName(assetId: string, assetNames?: Record<string, { name: string; version?: string }>): string {
  const baseId = assetId.replace(/:v\d+$/, '').replace(/@[^:]+$/, '');
  const assetInfo = assetNames?.[baseId];
  if (assetInfo?.name) {
    return assetInfo.name;
  }
  // 이름이 없으면 UUID의 앞부분 표시
  return baseId.slice(0, 8);
}

// Asset 버전 추출
function getAssetVersion(value: string): string | null {
  const versionMatch = value.match(/:v(\d+)|@([^:]+)/);
  return versionMatch ? (versionMatch[1] || versionMatch[2]) : null;
}

// Asset Card Component (세로 표시, 클릭 가능)
interface AssetCardProps {
  type: string;
  value: string;
  assetNames?: Record<string, { name: string; version?: string }>;
  onClick: (detail: AssetDetail) => void;
}

function AssetCard({ type, value, assetNames, onClick }: AssetCardProps) {
  const config = ASSET_CONFIG[type] || { icon: <FileText className="h-3 w-3" />, color: "text-muted-foreground", label: type };
  const displayName = getAssetName(value, assetNames);
  const version = getAssetVersion(value);
  const baseId = value.replace(/:v\d+$/, '').replace(/@[^:]+$/, '');

  const handleClick = () => {
    onClick({
      id: baseId,
      type,
      name: displayName,
      version: version || "unknown",
      fullId: value,
    });
  };

  return (
    <div
      onClick={handleClick}
      className={cn(
        "w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left cursor-pointer transition-all group",
        "bg-surface-overlay border-variant"
      )}
      title={`${config.label}: ${value}`}
    >
      <span className={config.color}>{config.icon}</span>
      <span className="text-tiny capitalize min-w-[50px] text-muted-foreground">{config.label}:</span>
      <span className="text-tiny font-medium truncate flex-1 text-foreground">{displayName}</span>
      <span className="text-[8px] text-muted-foreground">{version ? `v${version}` : ""}</span>
      <Info className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground" />
    </div>
  );
}

// Applied Assets List Component (세로 표시)
interface AppliedAssetsListProps {
  appliedAssets: AppliedAssets | null | undefined;
  assetNames?: Record<string, { name: string; version?: string }>;
  onAssetClick: (detail: AssetDetail) => void;
}

function AppliedAssetsList({ appliedAssets, assetNames, onAssetClick }: AppliedAssetsListProps) {
  if (!appliedAssets) return null;

  const assets = Object.entries(appliedAssets).filter(([_, value]) => value != null);

  if (assets.length === 0) return null;

  return (
    <div className="mt-2 pt-2 border-t border-variant space-y-1">
      {assets.map(([type, value]) => (
        <AssetCard
          key={type}
          type={type}
          value={value as string}
          assetNames={assetNames}
          onClick={onAssetClick}
        />
      ))}
    </div>
  );
}

// Asset Legend
function AssetLegend() {
  return (
    <div className="flex items-center gap-3 flex-wrap">
      {Object.entries(ASSET_CONFIG).map(([type, config]) => (
        <div key={type} className="flex items-center gap-1.5">
          <span className={config.color}>{config.icon}</span>
          <span className="text-[9px] text-muted-foreground">{config.label}</span>
        </div>
      ))}
    </div>
  );
}

// Asset Detail Modal
interface AssetDetailModalProps {
  asset: AssetDetail | null;
  onClose: () => void;
}

function AssetDetailModal({ asset, onClose }: AssetDetailModalProps) {
  if (!asset) return null;

  const config = ASSET_CONFIG[asset.type] || { icon: <FileText className="h-4 w-4" />, color: "text-muted-foreground", label: asset.type };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-2xl border border-variant bg-surface-base shadow-2xl p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-surface-base">
              {config.icon}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                {asset.name} <span className="text-muted-foreground">({asset.id})</span>
              </h3>
              <p className="text-xs text-muted-foreground">{config.label}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-surface-elevated transition"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>

        <div className="space-y-3">
          <div className="rounded-lg p-3 bg-surface-overlay">
            <p className="text-[9px] uppercase tracking-wider mb-1 text-slate-500 dark:text-slate-400">Asset ID</p>
            <p className="text-xs font-mono break-all text-foreground">{asset.id}</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg p-3 bg-surface-overlay">
              <p className="text-[9px] uppercase tracking-wider mb-1 text-slate-500 dark:text-slate-400">Type</p>
              <p className="text-xs capitalize text-foreground">{asset.type}</p>
            </div>
            <div className="rounded-lg p-3 bg-surface-overlay">
              <p className="text-[9px] uppercase tracking-wider mb-1 text-slate-500 dark:text-slate-400">Version</p>
              <p className="text-xs text-foreground">v{asset.version}</p>
            </div>
          </div>

          <div className="rounded-lg p-3 bg-surface-overlay">
            <p className="text-[9px] uppercase tracking-wider mb-1 text-slate-500 dark:text-slate-400">Full Identifier</p>
            <p className="text-xs font-mono break-all text-muted-foreground">{asset.fullId}</p>
          </div>

          <div className="bg-sky-500/5 border border-sky-400/20 rounded-lg p-3">
            <p className="text-[9px] uppercase tracking-wider text-sky-400 mb-1">Asset Registry</p>
            <p className="text-xs text-foreground">
              상세 정보는 Asset Registry 페이지에서 확인할 수 있습니다.
            </p>
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 hover:bg-surface-elevated text-foreground text-xs rounded-lg transition bg-surface-elevated"
          >
            닫기
          </button>
        </div>
      </div>
    </div>
  );
}

export default function InspectorStagePipeline({
  className,
  traceId,
  stages,
  onStageSelect,
  showAssets = false,
  assetNames,
}: StagePipelineProps) {
  const [selectedStage, setSelectedStage] = useState<StageSnapshotType | null>(null);
  const [selectedAsset, setSelectedAsset] = useState<AssetDetail | null>(null);
  const orderedStages = useMemo(() => (stages as StageSnapshotType[]) ?? [], [stages]);

  const handleStageClick = (stage: StageSnapshotType) => {
    setSelectedStage(stage);
    onStageSelect?.(stage);
  };

  const handleAssetClick = (detail: AssetDetail) => {
    setSelectedAsset(detail);
  };

  return (
    <>
      <div className="flex flex-col rounded-2xl border border-variant bg-surface-overlay">
        <div className="p-4 border-b border-variant">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Stage Pipeline</h2>
              {traceId && (
                <p className="text-xs mt-1 break-all text-muted-foreground">Trace ID: {traceId}</p>
              )}
            </div>
            <div className="text-tiny uppercase tracking-wider text-muted-foreground">
              {orderedStages.length} stages
            </div>
          </div>

          {/* Asset Legend */}
          {showAssets && (
            <div className="mt-3 pt-3 border-t border-variant">
              <AssetLegend />
            </div>
          )}
        </div>

        <div className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            {orderedStages.map((stage, index) => {
              const statusStyle = STATUS_STYLES[stage.status];
              const isSelected = selectedStage?.name === stage.name;
              const appliedAssets = (stage.input as { applied_assets?: AppliedAssets })?.applied_assets;

              return (
                <div key={stage.name} className="flex items-center gap-3">
                  <button
                    onClick={() => handleStageClick(stage)}
                    className={cn(
                      "min-w-[160px] rounded-xl border px-3 py-2 text-left transition-all",
                      isSelected ? "border-primary bg-surface-elevated ring-2 ring-primary" : "border-variant bg-surface-overlay"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <span className={cn(
                        "text-xs uppercase tracking-wider",
                        isSelected ? "text-foreground" : "text-muted-foreground"
                      )}>
                        {stage.label}
                      </span>
                      <span className={cn("px-2 py-0.5 rounded-full text-tiny flex items-center gap-1", statusStyle.badge)}>
                        {statusStyle.icon}
                        {stage.status}
                      </span>
                    </div>
                    <div className={cn(
                      "mt-2 flex items-center justify-between text-xs",
                      isSelected ? "text-foreground" : "text-muted-foreground"
                    )}>
                      <span className="font-mono">{stage.name}</span>
                      <span>{stage.duration_ms ? `${stage.duration_ms}ms` : "-"}</span>
                    </div>

                    {/* Applied Assets List - 세로 표시 */}
                    {showAssets && (
                      <AppliedAssetsList
                        appliedAssets={appliedAssets}
                        assetNames={assetNames}
                        onAssetClick={handleAssetClick}
                      />
                    )}
                  </button>
                  {index < orderedStages.length - 1 && (
                    <div className="h-px w-6 bg-surface-elevated" />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {selectedStage && (
          <div className="border-t border-variant bg-surface-overlay p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-foreground">{selectedStage.label} Details</h3>
              <div className={cn("text-xs px-2 py-1 rounded-full", STATUS_STYLES[selectedStage.status].badge)}>
                {selectedStage.status}
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <details className="border border-variant bg-surface-overlay rounded-xl p-3" open>
                <summary className="text-tiny uppercase tracking-wider cursor-pointer text-slate-500 dark:text-slate-400">
                  Stage Input
                </summary>
                <pre className="mt-2 text-xs text-foreground overflow-auto max-h-56">
                  {selectedStage.input ? prettyJson(selectedStage.input) : "No input captured"}
                </pre>
              </details>
              <details className="border border-variant bg-surface-overlay rounded-xl p-3">
                <summary className="text-tiny uppercase tracking-wider cursor-pointer text-slate-500 dark:text-slate-400">
                  Stage Output
                </summary>
                <pre className="mt-2 text-xs text-foreground overflow-auto max-h-56">
                  {selectedStage.output ? prettyJson(selectedStage.output) : "No output captured"}
                </pre>
              </details>
            </div>
            {(selectedStage.diagnostics?.warnings?.length || selectedStage.diagnostics?.errors?.length) && (
              <div className="grid gap-3 md:grid-cols-2">
                {selectedStage.diagnostics?.warnings?.length ? (
                  <div className="bg-amber-500/5 border border-amber-400/30 rounded-xl p-3">
                    <p className="text-xs text-amber-300 font-semibold">Warnings</p>
                    <ul className="mt-2 text-xs text-amber-200 space-y-1">
                      {selectedStage.diagnostics.warnings.map((warning, index) => (
                        <li key={`${warning}-${index}`}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {selectedStage.diagnostics?.errors?.length ? (
                  <div className="bg-rose-500/5 border border-rose-400/30 rounded-xl p-3">
                    <p className="text-xs text-rose-300 font-semibold">Errors</p>
                    <ul className="mt-2 text-xs text-rose-200 space-y-1">
                      {selectedStage.diagnostics.errors.map((error, index) => (
                        <li key={`${error}-${index}`}>{error}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Asset Detail Modal */}
      <AssetDetailModal asset={selectedAsset} onClose={() => setSelectedAsset(null)} />
    </>
  );
}
