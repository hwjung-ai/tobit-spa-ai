"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";
import ScreenAssetPanel from "@/components/admin/ScreenAssetPanel";

function ScreensPageContent() {
  const pathname = usePathname();

  return (
    <div className="space-y-6">
      <main className="animate-in fade-in duration-700">
        <ScreenAssetPanel key={pathname} />
      </main>
    </div>
  );
}

export default function ScreensPage() {
  return (
    <Suspense fallback={
      <div className="space-y-6">
        <div className="h-10 w-40 animate-pulse rounded-lg bg-surface-base" />
        <div className="h-6 w-full rounded-xl bg-surface-base" />
      </div>
    }>
      <ScreensPageContent />
    </Suspense>
  );
}
