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
        console.log("[PublishedScreensList] Loading published screens...");
        const envelope = await fetchApi<{
          assets: PublishedScreenAsset[];
          total: number;
        }>("/asset-registry/assets?asset_type=screen&status=published");
        console.log("[PublishedScreensList] Response envelope:", envelope);
        console.log("[PublishedScreensList] Assets loaded:", envelope.data?.assets);
        if (!cancelled) {
          setAssets(envelope.data.assets || []);
        }
      } catch (err: unknown) {
        console.error("[PublishedScreensList] Error loading:", err);
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
      <div className="rounded-xl border   p-6 text-center " style={{borderColor: "var(--border)", color: "var(--muted-foreground)", backgroundColor: "var(--surface-overlay)"}}>
        Loading published screens...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-red-800 bg-red-950/40 p-4 text-sm text-red-200">
        <p className="font-semibold">Failed to load screens</p>
        <p>{error}</p>
      </div>
    );
  }

  if (!assets.length) {
    return (
      <div className="rounded-xl border   p-6 text-center " style={{borderColor: "var(--border)", color: "var(--muted-foreground)", backgroundColor: "var(--surface-overlay)"}}>
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
          className="block rounded-2xl border   px-4 py-3 transition hover: hover:" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}
        >
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="text-sm font-semibold  truncate" style={{color: "var(--foreground)"}}>
              {asset.name || asset.screen_id}
            </h3>
            <span className="text-[10px] uppercase tracking-[0.4em] " style={{color: "var(--muted-foreground)"}}>
              v{asset.version}
            </span>
          </div>
          <p className="text-xs " style={{color: "var(--muted-foreground)"}}>
            Screen ID: {asset.screen_id}
          </p>
          <p className="text-[11px] " style={{color: "var(--muted-foreground)"}}>
            {asset.description || "No description available"}
          </p>
          <p className="text-[10px] " style={{color: "var(--muted-foreground)"}}>
            Published: {formatTimestamp(asset.published_at)} · Updated: {formatTimestamp(asset.updated_at)}
          </p>
        </Link>
      ))}
    </div>
  );
}
