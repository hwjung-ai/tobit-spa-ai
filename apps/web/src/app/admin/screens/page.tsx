"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";
import ScreenAssetPanel from "@/components/admin/ScreenAssetPanel";

function ScreensPageContent() {
  const pathname = usePathname();

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">Screen Asset Management</h1>
      <p className="text-slate-600 dark:text-slate-400">Manage UI Screen assets - create, edit, publish, and rollback screen definitions</p>
      <ScreenAssetPanel key={pathname} />
    </div>
  );
}

export default function ScreensPage() {
  return (
    <Suspense fallback={
      <div className="space-y-4">
        <div className="h-10 w-96 bg-slate-200 rounded animate-pulse dark:bg-slate-800" />
        <div className="h-6 w-full bg-slate-200 rounded animate-pulse dark:bg-slate-800" />
      </div>
    }>
      <ScreensPageContent />
    </Suspense>
  );
}
