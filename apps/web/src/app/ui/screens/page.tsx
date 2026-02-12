import PublishedScreensList from "@/components/ui/screens/PublishedScreensList";
import { PageHeader } from "@/components/shared";

export default function PublishedScreensPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-slate-950">
      <PageHeader
        title="Pages published"
        description="런타임 뷰어에서 게시된 UI 화면을 탐색하고 상호작용합니다."
      />
      <main className="px-6 py-6">
        <PublishedScreensList />
      </main>
    </div>
  );
}
