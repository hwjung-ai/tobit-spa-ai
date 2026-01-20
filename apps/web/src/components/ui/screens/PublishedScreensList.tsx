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
      } catch (err: any) {
        if (!cancelled) {
          setError(err.message || "Unable to load published screens");
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
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 text-center text-slate-400">
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
      <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 text-center text-slate-500">
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
          className="block rounded-2xl border border-slate-800 bg-slate-900/60 px-4 py-3 transition hover:border-slate-600 hover:bg-slate-900"
        >
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="text-sm font-semibold text-slate-100 truncate">
              {asset.name || asset.screen_id}
            </h3>
            <span className="text-[10px] uppercase tracking-[0.4em] text-slate-500">
              v{asset.version}
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Screen ID: {asset.screen_id}
          </p>
          <p className="text-[11px] text-slate-500">
            {asset.description || "No description available"}
          </p>
          <p className="text-[10px] text-slate-500">
            Published: {formatTimestamp(asset.published_at)} · Updated: {formatTimestamp(asset.updated_at)}
          </p>
        </Link>
      ))}
    </div>
  );
}
