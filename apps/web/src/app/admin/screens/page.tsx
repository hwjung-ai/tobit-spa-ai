"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";
import ScreenAssetPanel from "@/components/admin/ScreenAssetPanel";

function ScreensPageContent() {
  const pathname = usePathname();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold" style={{ color: "var(--foreground)" }}>Screen Asset Management</h1>
      <p style={{ color: "var(--muted-foreground)" }}>Manage UI Screen assets - create, edit, publish, and rollback screen definitions</p>
      <ScreenAssetPanel key={pathname} />
    </div>
  );
}

export default function ScreensPage() {
  return (
    <Suspense fallback={
      <div className="space-y-4">
        <div className="h-10 w-96 rounded animate-pulse" style={{ backgroundColor: "var(--muted-background)" }} />
        <div className="h-6 w-full rounded animate-pulse" style={{ backgroundColor: "var(--muted-background)" }} />
      </div>
    }>
      <ScreensPageContent />
    </Suspense>
  );
}
