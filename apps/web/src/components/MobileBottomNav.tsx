"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  MessageSquare,
  FileText,
  FlaskConical,
  Activity,
  Code2,
  LayoutGrid,
  Shield,
} from "lucide-react";

const NAV_ITEMS = [
  { label: "Chat", href: "/", icon: MessageSquare },
  { label: "Docs", href: "/documents", icon: FileText },
  { label: "SIM", href: "/sim", icon: FlaskConical },
  { label: "Ops", href: "/ops", icon: Activity },
  { label: "API", href: "/api-manager", icon: Code2 },
  { label: "CEP", href: "/cep-builder", icon: Shield },
  { label: "Pages", href: "/ui/screens", icon: LayoutGrid, adminOnly: true },
];

export default function MobileBottomNav() {
  const pathname = usePathname() || "/";
  const enableAdmin =
    process.env.NEXT_PUBLIC_ENABLE_ASSET_REGISTRY === "true";

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-variant bg-surface-overlay backdrop-blur-sm md:hidden"
      aria-label="Mobile navigation"
    >
      <div className="flex items-center justify-around px-2 py-1">
        {NAV_ITEMS.filter((item) =>
          item.adminOnly ? enableAdmin : true
        ).map((item) => {
          const Icon = item.icon;
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.label}
              href={item.href}
              aria-current={isActive ? "page" : undefined}
              className={`flex flex-col items-center gap-0.5 px-2 py-1.5 text-xs uppercase tracking-wider transition ${
                isActive ? "text-primary-light" : "text-muted-foreground"
              }`}
            >
              <Icon className="h-5 w-5" strokeWidth={isActive ? 2.2 : 1.5} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
