"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function UICreatorRedirect() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to Admin Screens
    router.replace("/admin/screens");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-white dark:bg-slate-950">
      <div className="text-center">
        <p className="text-slate-700 dark:text-slate-300 mb-2">UI Creator has been deprecated.</p>
        <p className="text-slate-600 dark:text-slate-400">Redirecting to Admin &gt; Screens...</p>
      </div>
    </div>
  );
}
