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
        { label: "Settings", href: "/admin/settings" },
        { label: "Inspector", href: "/admin/inspector" },
    ];

    return (
        <div className="flex flex-col min-h-screen bg-slate-950">
            {/* Sub Navigation */}
            <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur-md sticky top-0 z-40">
                <div className="max-w-7xl mx-auto px-6">
                    <div className="flex gap-8">
                        {tabs.map((tab) => {
                            const isActive = pathname.startsWith(tab.href);
                            return (
                                <Link
                                    key={tab.label}
                                    href={tab.href}
                                    className={`py-4 text-sm font-medium transition-colors border-b-2 ${isActive
                                            ? "border-sky-500 text-sky-400"
                                            : "border-transparent text-slate-400 hover:text-slate-200"
                                        }`}
                                >
                                    {tab.label}
                                </Link>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <main className="flex-1">
                {children}
            </main>
        </div>
    );
}
