"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
    { label: "EXPLORER", href: "/data" },
    { label: "SOURCE", href: "/data/sources" },
    { label: "CATALOG", href: "/data/catalog" },
    { label: "RESOLVERS", href: "/data/resolvers" },
];

export function DataNavigation() {
    const pathname = usePathname();

    return (
        <div className="flex items-center gap-1 mb-6 p-1 bg-slate-900/50 border border-slate-800 rounded-full w-fit">
            {NAV_ITEMS.map((item) => {
                const isActive = pathname === item.href;
                return (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                            "px-4 py-1.5 rounded-full text-[10px] font-bold tracking-[0.2em] transition-all whitespace-nowrap",
                            isActive
                                ? "bg-sky-500 text-white shadow-lg shadow-sky-900/20"
                                : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                        )}
                    >
                        {item.label}
                    </Link>
                );
            })}
        </div>
    );
}
