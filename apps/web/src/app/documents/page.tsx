"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Legacy documents page redirect
 * Redirects users to the new /docs-query page
 */
export default function DocumentsRedirect() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to new docs page
    router.replace("/docs-query");
  }, [router]);

  return null;
}
