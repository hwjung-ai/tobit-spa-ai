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
    <div className="flex items-center justify-center min-h-screen" style={{ backgroundColor: "rgb(248, 250, 252)" }}>
      <div className="text-center">
        <p className="mb-2" style={{ color: "rgb(15, 23, 42)" }}>UI Creator has been deprecated.</p>
        <p style={{ color: "rgb(71, 85, 105)" }}>Redirecting to Admin &gt; Screens...</p>
      </div>
    </div>
  );
}
