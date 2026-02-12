import PublishedScreensList from "@/components/ui/screens/PublishedScreensList";

export default function PublishedScreensPage() {
  return (
    <div className="py-6 space-y-4">
      <h1 className="text-2xl font-bold " style={{ color: "var(--foreground)" }}>Published Screens</h1>
      <p className="" style={{ color: "var(--muted-foreground)" }}>Browse and interact with published UI screens from the runtime viewer</p>
      <PublishedScreensList />
    </div>
  );
}
