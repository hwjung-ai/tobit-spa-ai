import { Suspense } from "react";
import CatalogsContent from "./catalogs-content";

export const metadata = {
  title: "Catalogs - Admin",
  description: "Database Catalog Management",
};

export default function CatalogsPage() {
  return (
    <div className="space-y-6">
      <Suspense fallback={<div className="text-center py-8 text-sm text-muted-foreground dark:text-muted-foreground">Loading catalogs...</div>}>
        <CatalogsContent />
      </Suspense>
    </div>
  );
}
