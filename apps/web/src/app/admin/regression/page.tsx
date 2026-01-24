"use client";

import { Suspense } from "react";
import RegressionWatchPanel from "@/components/admin/RegressionWatchPanel";

export default function RegressionPage() {
  return (
    <Suspense fallback={<div className="p-4 text-slate-400">Loading...</div>}>
      <RegressionWatchPanel />
    </Suspense>
  );
}
