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
        <p className="cep-condition-label">{title}</p>
        {copyable && (
          <button
            onClick={handleCopy}
            className="cep-text-muted"
          >
            {copied ? "✓ 복사됨" : "📋 복사"}
          </button>
        )}
      </div>
      <pre className="cep-item-card overflow-x-auto">
        <code>{jsonString}</code>
      </pre>
    </div>
  );
}
