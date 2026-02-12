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
        { label: "Screens", href: "/admin/screens" },
        { label: "Explorer", href: "/admin/explorer" },
        { label: "Settings", href: "/admin/settings" },
        { label: "Inspector", href: "/admin/inspector" },
        { label: "Regression", href: "/admin/regression" },
        { label: "Observability", href: "/admin/observability" },
        { label: "Logs", href: "/admin/logs" },
    ];

    return (
        <div className="py-6 tracking-tight builder-shell builder-text" style={{color: "var(--foreground)"}}>
            {/* Header & Section Title */}
            <div className="flex items-center justify-between mb-2">
                <h1 className="text-2xl font-semibold" style={{color: "var(--foreground)"}}>Admin Dashboard</h1>
                <div className="text-[10px] uppercase tracking-[0.25em]" style={{color: "var(--muted-foreground)"}}>
                    System Management
                </div>
            </div>
            <p className="mb-6 text-sm" style={{color: "var(--muted-foreground)"}}>
                Configure operational parameters, manage core assets, and audit system activities.
            </p>

            {/* Sub Navigation (Capsule Style like Data page) */}
            <div className="mb-6 flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2">
                    <span className="text-[10px] uppercase tracking-[0.2em]" style={{color: "var(--muted-foreground)"}}>Module:</span>
                    {tabs.map((tab) => {
                        const isActive = pathname.startsWith(tab.href);
                        return (
                            <Link
                                key={tab.label}
                                href={tab.href}
                                className="rounded-full border px-4 py-1.5 text-[11px] font-bold uppercase tracking-[0.2em] transition"
                                style={{borderColor: isActive ? "var(--primary)" : "var(--border-muted)", color: isActive ? "var(--foreground)" : "var(--muted-foreground)", backgroundColor: isActive ? "rgba(14, 165, 233, 0.1)" : "transparent"}}
                                onMouseEnter={(e) => {
                                    if (!isActive) {
                                        e.currentTarget.style.borderColor = "var(--border)";
                                        e.currentTarget.style.color = "var(--foreground)";
                                    }
                                }}
                                onMouseLeave={(e) => {
                                    if (!isActive) {
                                        e.currentTarget.style.borderColor = "var(--border-muted)";
                                        e.currentTarget.style.color = "var(--muted-foreground)";
                                    }
                                }}
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
