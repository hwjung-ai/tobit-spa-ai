"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Chat", href: "/" },
  { label: "Docs", href: "/documents" },
  { label: "SIM", href: "/sim" },
  { label: "Ops", href: "/ops" },
  { label: "API", href: "/api-manager" },
  { label: "Pages", href: "/ui/screens" },
  { label: "CEP", href: "/cep-builder" },
  { label: "Admin", href: "/admin/assets", adminOnly: true },
];

export default function NavTabs() {
  const pathname = usePathname() || "/";
  const enableAdmin =
    process.env.NEXT_PUBLIC_ENABLE_ASSET_REGISTRY === "true";

  return (
    <nav className="flex gap-4 text-base uppercase tracking-wider text-muted-foreground" aria-label="Main navigation">
      {NAV_ITEMS.filter((item) =>
        item.adminOnly ? enableAdmin : true
      ).map((item) => {
        const isActive =
          pathname === item.href ||
          (item.href !== "/" && pathname.startsWith(item.href));
        return (
          <Link
            key={item.label}
            href={item.href}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "rounded-sm border-b-2 px-1 pb-1 font-semibold transition-colors",
              isActive
                ? "border-primary-light text-foreground"
                : "border-transparent text-muted-foreground hover:bg-surface-elevated hover:text-foreground"
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
