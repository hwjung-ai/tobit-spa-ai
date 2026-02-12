"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";
import ScreenAssetPanel from "@/components/admin/ScreenAssetPanel";

function ScreensPageContent() {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-50">
      <header className="border-b border-slate-200 px-6 py-4 dark:border-slate-800">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-50">Screen Asset Management</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
          Manage UI Screen assets - create, edit, publish, and rollback screen definitions
        </p>
      </header>
      <main className="min-h-[calc(100vh-96px)] px-6 py-6">
        <ScreenAssetPanel key={pathname} />
      </main>
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