"use client";

import { useState } from "react";

interface JsonPreviewProps {
  data: Record<string, any>;
  title?: string;
  copyable?: boolean;
}

export function JsonPreview({
  data,
  title = "JSON 미리보기",
  copyable = true,
}: JsonPreviewProps) {
  const [copied, setCopied] = useState(false);

  const jsonString = JSON.stringify(data, null, 2);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(jsonString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold" style={{ color: "var(--foreground)" }}>{title}</p>
        {copyable && (
          <button
            onClick={handleCopy}
            className="text-xs transition-colors" style={{ color: "var(--muted-foreground)" }}
          >
            {copied ? "✓ 복사됨" : "📋 복사"}
          </button>
        )}
      </div>
      <pre className="rounded-lg p-3 overflow-x-auto text-xs" style={{ border: "1px solid var(--border-muted)", backgroundColor: "rgba(30, 41, 59, 0.4)", color: "var(--muted-foreground)" }}>
        <code>{jsonString}</code>
      </pre>
    </div>
  );
}
