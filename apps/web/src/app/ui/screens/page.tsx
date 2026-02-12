import PublishedScreensList from "@/components/ui/screens/PublishedScreensList";

export default function PublishedScreensPage() {
  return (
    <div className="min-h-screen space-y-10 bg-white px-6 py-10 dark:bg-slate-950">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight leading-none text-slate-900 dark:text-slate-50">Published Screens</h1>
        <p className="text-base leading-relaxed text-slate-600 dark:text-slate-400">
          Browse and interact with published UI screens from the runtime viewer
        </p>
      </header>
      <main>
        <PublishedScreensList />
      </main>
    </div>
  );
}
