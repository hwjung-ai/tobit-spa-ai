"use client";

import { Suspense } from "react";
import RegressionWatchPanel from "@/components/admin/RegressionWatchPanel";

export default function RegressionPage() {
  return (
    <Suspense fallback={<div className="p-4  dark:" style={{color: "rgb(71, 85, 105)"}}>Loading...</div>}>
      <RegressionWatchPanel />
    </Suspense>
  );
}
