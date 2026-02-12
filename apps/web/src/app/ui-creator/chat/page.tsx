"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function UICreatorChatRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/admin/screens");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen ui-redirect-bg">
      <div className="text-center">
        <p className="text-slate-600 dark:text-slate-400 mb-2">UI Creator has been deprecated.</p>
        <p className="text-slate-500 dark:text-slate-500">Redirecting to Admin &gt; Screens...</p>
      </div>
    </div>
  );
}
