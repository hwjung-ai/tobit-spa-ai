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
    <div className="flex items-center justify-center min-h-screen bg-surface-base px-4 py-6 md:px-6 md:py-8">
      <div className="text-center">
        <p className="mb-2 text-foreground">UI Creator has been deprecated.</p>
        <p className="text-muted-foreground">Redirecting to Admin &gt; Screens...</p>
      </div>
    </div>
  );
}
