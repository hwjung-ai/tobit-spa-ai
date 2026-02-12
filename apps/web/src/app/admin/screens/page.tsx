"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";
import ScreenAssetPanel from "@/components/admin/ScreenAssetPanel";

function ScreensPageContent() {
  const pathname = usePathname();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">Screen Asset Management</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Manage UI Screen assets - create, edit, publish, and rollback screen definitions
        </p>
      </div>
      <ScreenAssetPanel key={pathname} />
    </div>
  );
}

export default function ScreensPage() {
  return (
    <Suspense fallback={
      <div className="space-y-6">
        <div className="h-10 w-40 animate-pulse rounded-lg bg-slate-200 dark:bg-slate-800" />
        <div className="h-6 w-full rounded-xl bg-slate-200 dark:bg-slate-800" />
      </div>
    }>
      <ScreensPageContent />
    </Suspense>
  );
}