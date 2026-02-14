"use client";

import { useEffect, useMemo, useState } from "react";
import { fetchApi, formatTimestamp } from "@/lib/adminUtils";
import UIScreenRenderer from "@/components/answer/UIScreenRenderer";
import { ScreenSchemaV1 } from "@/lib/ui-screen/screen.schema";

type ScreenAssetResponse = {
  asset: {
    asset_id: string;
    screen_id: string;
    name: string;
    description: string | null;
    version: number;
    status: string;
    schema_json: Record<string, unknown>;
    tags?: Record<string, unknown> | null;
    created_at: string;
    updated_at: string;
    published_at: string | null;
  };
};

interface PublishedScreenDetailProps {
  assetId: string;
}

export default function PublishedScreenDetail({ assetId }: PublishedScreenDetailProps) {
  const [asset, setAsset] = useState<ScreenAssetResponse["asset"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const envelope = await fetchApi<ScreenAssetResponse>(`/asset-registry/assets/${assetId}?stage=published`);
        if (!cancelled) {
          if (envelope.data?.asset) {
            setAsset(envelope.data.asset);
          } else {
            setError("Asset data not found in response");
            console.error("[PublishedScreenDetail] No asset in response:", envelope);
          }
        }
      } catch (err: unknown) {
        if (!cancelled) {
          console.error("[PublishedScreenDetail] Error loading screen:", err);
          const status = (err as { statusCode?: number })?.statusCode;
          const message = (err as { message?: string })?.message;
          if (status === 404) {
            setError("Screen not found or not published");
          } else if (status === 403) {
            setError("Access denied to this screen");
          } else {
            setError(message || "Unable to load screen");
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [assetId]);

  const previewBlock = useMemo(() => {
    if (!asset) return null;
    return {
      type: "ui_screen" as const,
      screen_id: asset.screen_id,
      params: {},
    };
  }, [asset]);

  if (loading) {
    return (
      <div className="rounded-xl border   p-6 text-center ">
        Loading screen...
      </div>
    );
  }

  if (error || !asset) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/50 p-4 text-sm text-red-200">
        <p className="font-semibold">Cannot render screen</p>
        <p>{error || "Unknown error"}</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="rounded-2xl border   p-4 flex-shrink-0">
        <h2 className="text-lg font-semibold text-white">
          {asset.name || asset.screen_id}
        </h2>
        <p className="text-xs ">
          Screen ID: {asset.screen_id} · Version {asset.version}
        </p>
        {asset.description && (
          <p className="text-sm  mt-1">{asset.description}</p>
        )}
        <p className="text-xs ">
          Published: {formatTimestamp(asset.published_at)} · Last update: {formatTimestamp(asset.updated_at)}
        </p>
        {asset.tags && Object.keys(asset.tags).length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {Object.entries(asset.tags).map(([key, value]) => (
              <span key={key} className="rounded-full border  px-2 py-0.5 text-xs ">
                {key}: {String(value)}
              </span>
            ))}
          </div>
        )}
      </div>
      <div className="flex-1 overflow-auto rounded-2xl border  /70 p-4">
        <UIScreenRenderer
          block={previewBlock!}
          schemaOverride={(typeof asset.schema_json === "object" && asset.schema_json !== null && "screen_id" in asset.schema_json)
            ? asset.schema_json as unknown as ScreenSchemaV1
            : undefined}
        />
      </div>
    </div>
  );
}
