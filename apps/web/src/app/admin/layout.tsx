"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

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
        { label: "Screens", href: "/admin/screens" },
        { label: "Explorer", href: "/admin/explorer" },
        { label: "Settings", href: "/admin/settings" },
        { label: "Inspector", href: "/admin/inspector" },
        { label: "Regression", href: "/admin/regression" },
        { label: "Observability", href: "/admin/observability" },
        { label: "Logs", href: "/admin/logs" },
    ];

    return (
        <div className="py-6 tracking-tight builder-shell builder-text text-primary">
            {/* Header & Section Title */}
            <div className="flex items-center justify-between mb-2">
                <h1 className="text-2xl font-semibold text-primary">Admin Dashboard</h1>
                <div className="text-label-sm">
                    System Management
                </div>
            </div>
            <p className="mb-6 text-sm text-muted-standard">
                Configure operational parameters, manage core assets, and audit system activities.
            </p>

            {/* Sub Navigation (Capsule Style like Data page) */}
            <div className="mb-6 flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                    <span className="text-label-sm">Module:</span>
                    {tabs.map((tab) => {
                        const isActive = pathname.startsWith(tab.href);
                        return (
                            <Link
                                key={tab.label}
                                href={tab.href}
                                className={cn(
                                    "rounded-full border px-4 py-1.5 text-xs font-bold uppercase tracking-wider transition",
                                    isActive
                                        ? "bg-primary text-primary-foreground border-primary"
                                        : "border-transparent text-muted-standard hover:border-sky-500 hover:text-primary hover:bg-sky-500/10"
                                )}
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
