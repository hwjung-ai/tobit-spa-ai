"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function AdminLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();

    const tabs = [
        { label: "Assets", href: "/admin/assets" },
        { label: "Tools", href: "/admin/tools" },
        { label: "Catalogs", href: "/admin/catalogs" },
        { label: "Schemas", href: "/admin/schemas" },
        { label: "Screens", href: "/admin/screens" },
        { label: "Explorer", href: "/admin/explorer" },
        { label: "Settings", href: "/admin/settings" },
        { label: "Inspector", href: "/admin/inspector" },
        { label: "Regression", href: "/admin/regression" },
        { label: "Observability", href: "/admin/observability" },
    ];

    return (
        <div className="py-6 tracking-tight builder-shell builder-text">
            {/* Header & Section Title */}
            <div className="flex items-center justify-between mb-2">
                <h1 className="text-2xl font-semibold text-white">Admin Dashboard</h1>
                <div className="text-[10px] uppercase tracking-[0.25em] text-slate-500">
                    System Management
                </div>
            </div>
            <p className="mb-6 text-sm text-slate-400">
                Configure operational parameters, manage core assets, and audit system activities.
            </p>

            {/* Sub Navigation (Capsule Style like Data page) */}
            <div className="mb-6 flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Module:</span>
                    {tabs.map((tab) => {
                        const isActive = pathname.startsWith(tab.href);
                        return (
                            <Link
                                key={tab.label}
                                href={tab.href}
                                className={`rounded-full border px-4 py-1.5 text-[11px] font-bold uppercase tracking-[0.2em] transition ${isActive
                                    ? "border-sky-400 text-white bg-sky-400/5 shadow-[0_0_15px_rgba(56,189,248,0.1)]"
                                    : "border-slate-800 text-slate-400 hover:border-slate-600 hover:text-slate-200"
                                    }`}
                            >
                                {tab.label}
                            </Link>
                        );
                    })}
                </div>
            </div>

            {/* Main Content Area */}
            <div className="animate-in fade-in duration-700">
                {children}
            </div>
        </div>
    );
}
