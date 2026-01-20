import PublishedScreensList from "@/components/ui/screens/PublishedScreensList";

export default function PublishedScreensPage() {
  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <header className="space-y-2 rounded-2xl border border-slate-800 bg-slate-950/60 p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Runtime</p>
        <h1 className="text-3xl font-semibold text-white">Published Screens</h1>
        <p className="text-sm text-slate-400">
          Browse the latest published UI screens and launch them in the runtime viewer. Drafts are not shown here.
        </p>
      </header>
      <PublishedScreensList />
    </div>
  );
}
