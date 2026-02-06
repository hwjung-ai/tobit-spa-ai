"use client";

import { CepRuleFormPage } from "@/components/cep-builder-v2";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function CepBuilderV2Page() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);

  const handleSave = async (data: any) => {
    setIsLoading(true);
    try {
      const response = await fetch("/api/cep/rules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || "규칙 저장 실패");
      }

      const result = await response.json();
      console.log("규칙 저장 성공:", result);

      // 저장 후 목록 페이지로 이동
      setTimeout(() => {
        router.push("/cep-events");
      }, 2000);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    router.back();
  };

  return (
    <div className="min-h-screen bg-slate-950">
      <CepRuleFormPage
        onSave={handleSave}
        onCancel={handleCancel}
        isLoading={isLoading}
      />
    </div>
  );
}
