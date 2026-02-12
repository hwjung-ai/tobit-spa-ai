"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function UICreatorChatRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/admin/screens");
  }, [router]);

  return (
    <div className="flex items-center justify-center min-h-screen bg-white dark:" style={{ backgroundColor: "var(--surface-base)" }}>
      <div className="text-center">
        <p className=" dark: mb-2" style={{ color: "var(--foreground)" ,  color: "var(--foreground-secondary)" }}>UI Creator has been deprecated.</p>
        <p className=" dark:" style={{ color: "var(--muted-foreground)" ,  color: "var(--muted-foreground)" }}>Redirecting to Admin &gt; Screens...</p>
      </div>
    </div>
  );
}
