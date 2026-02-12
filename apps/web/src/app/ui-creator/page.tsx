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
    <div className="flex items-center justify-center min-h-screen" style={{ backgroundColor: "var(--surface-base)" }}>
      <div className="text-center">
        <p className="mb-2" style={{ color: "var(--foreground)" }}>UI Creator has been deprecated.</p>
        <p style={{ color: "var(--muted-foreground)" }}>Redirecting to Admin &gt; Screens...</p>
      </div>
    </div>
  );
}
