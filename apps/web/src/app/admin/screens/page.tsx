"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import ScreenAssetPanel from "@/components/admin/ScreenAssetPanel";

export default function ScreensPage() {
  const pathname = usePathname();
  const [refreshKey, setRefreshKey] = useState(0);

  // Refresh the screen list when we return to /admin/screens
  useEffect(() => {
    if (pathname === "/admin/screens") {
      setRefreshKey((prev) => prev + 1);
    }
  }, [pathname]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-slate-100">Screen Asset Management</h1>
      <p className="text-slate-400">Manage UI Screen assets - create, edit, publish, and rollback screen definitions</p>
      <ScreenAssetPanel key={refreshKey} />
    </div>
  );
}
