"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchApi, formatTimestamp } from "@/lib/adminUtils";

type PublishedScreenAsset = {
  asset_id: string;
  screen_id: string;
  name: string | null;
  version: number;
  status: string;
  published_at: string | null;
  updated_at: string;
  description: string | null;
};

export default function PublishedScreensList() {
  const [assets, setAssets] = useState<PublishedScreenAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const envelope = await fetchApi<{
          assets: PublishedScreenAsset[];
          total: number;
        }>("/asset-registry/assets?asset_type=screen&status=published");
        if (!cancelled) {
          setAssets(envelope.data.assets || []);
        }
      } catch (err: unknown) {
        if (process.env.NODE_ENV === 'development') {
          console.error("[PublishedScreensList] Error loading:", err);
        }
        const errorMessage = err instanceof Error ? err.message : "Unable to load published screens";
        if (!cancelled) {
          setError(errorMessage);
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
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border p-6 text-center border-variant dark:border-variant text-muted-foreground dark:text-muted-foreground bg-surface-elevated dark:bg-surface-elevated/50">
        Loading published screens...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border p-4 text-sm border-rose-500/40 bg-rose-500/10 text-rose-400">
        <p className="font-semibold">Failed to load screens</p>
        <p>{error}</p>
      </div>
    );
  }

  if (!assets.length) {
    return (
      <div className="rounded-xl border p-6 text-center border-variant dark:border-variant text-muted-foreground dark:text-muted-foreground bg-surface-elevated dark:bg-surface-elevated/50">
        No published screens available
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {assets.map((asset) => (
        <Link
          key={asset.asset_id}
          href={`/ui/screens/${asset.asset_id}`}
          className="block rounded-2xl border border-variant bg-surface-overlay hover:bg-surface-elevated px-4 py-3 transition-all"
        >
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="text-sm font-semibold text-foreground truncate">
              {asset.name || asset.screen_id}
            </h3>
            <span className="text-tiny uppercase tracking-wider text-muted-foreground">
              v{asset.version}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            Screen ID: {asset.screen_id}
          </p>
          <p className="text-xs text-muted-foreground">
            {asset.description || "No description available"}
          </p>
          <p className="text-xs text-muted-foreground">
            Published: {formatTimestamp(asset.published_at)} · Updated: {formatTimestamp(asset.updated_at)}
          </p>
        </Link>
      ))}
    </div>
  );
}
