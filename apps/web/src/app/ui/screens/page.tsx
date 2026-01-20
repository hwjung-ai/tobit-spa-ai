import PublishedScreensList from "@/components/ui/screens/PublishedScreensList";

export default function PublishedScreensPage() {
  return (
    <div className="py-6 space-y-4">
      <h1 className="text-2xl font-bold text-slate-100">Published Screens</h1>
      <p className="text-slate-400">Browse and interact with published UI screens from the runtime viewer</p>
      <PublishedScreensList />
    </div>
  );
}
