"use client";

import { Asset, formatRelativeTime } from "../../lib/adminUtils";
import Link from "next/link";

interface AssetTableProps {
    assets: Asset[];
}

export default function AssetTable({ assets }: AssetTableProps) {
    if (assets.length === 0) {
        return (
            <div className="text-center py-8 text-slate-400">
                No assets found
            </div>
        );
    }

    return (
        <div className="overflow-x-auto">
            <table className="w-full text-sm">
                <thead>
                    <tr className="border-b border-slate-800">
                        <th className="text-left py-3 px-4 text-slate-500 font-medium">Name</th>
                        <th className="text-left py-3 px-4 text-slate-500 font-medium">Type</th>
                        <th className="text-left py-3 px-4 text-slate-500 font-medium">Status</th>
                        <th className="text-left py-3 px-4 text-slate-500 font-medium font-mono">Version</th>
                        <th className="text-left py-3 px-4 text-slate-500 font-medium">Updated</th>
                        <th className="text-left py-3 px-4 text-slate-500 font-medium text-right">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {assets.map((asset) => (
                        <tr
                            key={asset.asset_id}
                            className="border-b border-slate-800 hover:bg-slate-900/50 transition-colors"
                        >
                            <td className="py-3 px-4">
                                <Link
                                    href={`/admin/assets/${asset.asset_id}`}
                                    className="text-sky-400 hover:text-sky-300 transition-colors"
                                >
                                    {asset.name}
                                </Link>
                            </td>
                            <td className="py-3 px-4">
                                <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${asset.asset_type === "prompt" ? "bg-purple-950/50 text-purple-300" :
                                        asset.asset_type === "mapping" ? "bg-blue-950/50 text-blue-300" :
                                            "bg-green-950/50 text-green-300"
                                    }`}>
                                    {asset.asset_type}
                                </span>
                            </td>
                            <td className="py-3 px-4">
                                <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${asset.status === "published" ? "bg-green-950/50 text-green-300" :
                                        "bg-slate-800 text-slate-300"
                                    }`}>
                                    {asset.status}
                                </span>
                            </td>
                            <td className="py-3 px-4 text-slate-300">
                                v{asset.version}
                            </td>
                            <td className="py-3 px-4 text-slate-400 text-xs">
                                {formatRelativeTime(asset.updated_at)}
                            </td>
                            <td className="py-3 px-4 text-right">
                                <Link
                                    href={`/admin/assets/${asset.asset_id}`}
                                    className="text-sky-400 hover:text-sky-300 text-xs transition-colors"
                                >
                                    View
                                </Link>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
