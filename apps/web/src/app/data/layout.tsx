"use client";

import { usePathname } from "next/navigation";
import { DataNavigation } from "@/components/data/DataNavigation";

export default function DataLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    return (
        <div className="py-6 tracking-tight builder-shell builder-text">
            <div className="flex items-center justify-between mb-2">
                <h1 className="text-2xl font-semibold text-white">Data Management</h1>
                <div className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
                    Storage & Schema
                </div>
            </div>
            <p className="mb-6 text-sm text-slate-400">
                Manage data sources, explore schemas, and configure entity resolution rules.
            </p>

            <div className="mb-6">
                <DataNavigation />
            </div>

            <div className="animate-in fade-in duration-700">
                {children}
            </div>
        </div>
    );
}
