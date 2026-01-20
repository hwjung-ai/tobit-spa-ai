"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { label: "Chat", href: "/" },
  { label: "Docs", href: "/documents" },
  { label: "Ops", href: "/ops" },
  { label: "API", href: "/api-manager" },
  { label: "UI Creator", href: "/ui-creator" },
  { label: "Screens", href: "/ui/screens" },
  { label: "CEP", href: "/cep-builder" },
  { label: "Data", href: "/data", adminOnly: true },
  { label: "Admin", href: "/admin/assets", adminOnly: true },
];

export default function NavTabs() {
  const pathname = usePathname() || "/";
  const enableDataExplorer =
    process.env.NEXT_PUBLIC_ENABLE_DATA_EXPLORER === "true";

  return (
    <nav className="flex gap-4 text-sm uppercase tracking-[0.3em]">
      {NAV_ITEMS.filter((item) =>
        item.adminOnly ? enableDataExplorer : true
      ).map((item) => {
        const isActive =
          pathname === item.href ||
          (item.href !== "/" && pathname.startsWith(item.href));
        return (
          <Link
            key={item.label}
            href={item.href}
            className={`transition border-b-2 pb-1 ${isActive
              ? "border-sky-400 text-white"
              : "border-transparent text-slate-400 hover:border-slate-600 hover:text-white"
            }`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
