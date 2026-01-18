"use client";

import ScreenAssetPanel from "@/components/admin/ScreenAssetPanel";

export default function ScreensPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-100">Screen Asset Management</h1>
      <p className="text-slate-400">Manage UI Screen assets - create, edit, publish, and rollback screen definitions</p>
      <ScreenAssetPanel />
    </div>
  );
}
