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
        <p className="text-xs font-semibold text-white">{title}</p>
        {copyable && (
          <button
            onClick={handleCopy}
            className="text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            {copied ? "✓ 복사됨" : "📋 복사"}
          </button>
        )}
      </div>
      <pre className="rounded-lg border border-slate-700 bg-slate-900/40 p-3 overflow-x-auto text-xs text-slate-300">
        <code>{jsonString}</code>
      </pre>
    </div>
  );
}
