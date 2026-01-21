import { use } from "react";
import PublishedScreenDetail from "@/components/ui/screens/PublishedScreenDetail";

interface PublishedScreenPageProps {
  params: Promise<{ screenId: string }>;
}

export default function PublishedScreenPage({ params }: PublishedScreenPageProps) {
  const { screenId } = use(params);

  return (
    <div className="flex h-[calc(100vh-96px)] flex-col gap-6 overflow-hidden">
      <header className="space-y-2 rounded-2xl border border-slate-800 bg-slate-950/60 p-6 flex-shrink-0">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Runtime Viewer</p>
        <h1 className="text-3xl font-semibold text-white">Screen Preview</h1>
      </header>
      <div className="flex-1 overflow-auto">
        <PublishedScreenDetail assetId={screenId} />
      </div>
    </div>
  );
}
