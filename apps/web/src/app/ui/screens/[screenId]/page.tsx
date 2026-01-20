import PublishedScreenDetail from "@/components/ui/screens/PublishedScreenDetail";

interface PublishedScreenPageProps {
  params: { screenId: string };
}

export default function PublishedScreenPage({ params }: PublishedScreenPageProps) {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <header className="space-y-2 rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Runtime Viewer</p>
        <h1 className="text-3xl font-semibold text-white">Screen Preview</h1>
      </header>
      <PublishedScreenDetail assetId={params.screenId} />
    </div>
  );
}
