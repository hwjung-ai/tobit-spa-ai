import { Suspense } from "react";
import { PageHeader } from "@/components/shared";
import CatalogsContent from "./catalogs-content";

export const metadata = {
  title: "Catalogs - Admin",
  description: "Database Catalog Management",
};

export default function CatalogsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Database Catalogs"
        description="데이터베이스 카탈로그를 관리하고 연결 설정을 구성합니다."
      />

      <Suspense fallback={<div className="text-center py-8 text-sm text-slate-600 dark:text-slate-400">Loading catalogs...</div>}>
        <CatalogsContent />
      </Suspense>
    </div>
  );
}
