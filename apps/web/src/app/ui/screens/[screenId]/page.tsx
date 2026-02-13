import { use } from "react";
import PublishedScreenDetail from "@/components/ui/screens/PublishedScreenDetail";

interface PublishedScreenPageProps {
  params: Promise<{ screenId: string }>;
}

export default function PublishedScreenPage({ params }: PublishedScreenPageProps) {
  const { screenId } = use(params);

  return (
    <div className="flex h-[calc(100vh-96px)] flex-col gap-6 overflow-hidden">
      <header className="space-y-2 flex-shrink-0 rounded-2xl border border-variant bg-surface-elevated p-6 dark:border-variant dark:bg-surface-base">
        <p className="text-xs uppercase tracking-widest text-muted-foreground dark:text-muted-foreground">Runtime Viewer</p>
        <h1 className="text-3xl font-semibold text-foreground dark:text-slate-50">Screen Preview</h1>
      </header>
      <div className="flex-1 overflow-auto">
        <PublishedScreenDetail assetId={screenId} />
      </div>
    </div>
  );
}
