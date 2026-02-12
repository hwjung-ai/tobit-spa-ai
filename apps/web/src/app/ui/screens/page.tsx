import PublishedScreensList from "@/components/ui/screens/PublishedScreensList";

export default function PublishedScreensPage() {
  return (
    <div className="min-h-screen px-6 py-10 space-y-10" style={{ backgroundColor: "var(--background)" }}>
      <header className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight leading-none" style={{ color: "var(--foreground)" }}>Published Screens</h1>
        <p className="text-base leading-relaxed" style={{ color: "var(--muted-foreground)" }}>
          Browse and interact with published UI screens from the runtime viewer
        </p>
      </header>
      <main>
        <PublishedScreensList />
      </main>
    </div>
  );
}
