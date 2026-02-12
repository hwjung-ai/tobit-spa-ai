import { Suspense } from "react";
import CatalogsContent from "./catalogs-content";

export const metadata = {
  title: "Catalogs - Admin",
  description: "Database Catalog Management",
};

export default function CatalogsPage() {
  return (
    <div className="space-y-6">
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold  dark:text-slate-900" style={{color: "rgb(15, 23, 42)"}}>Database Catalogs</h1>
          <p className="mt-2 text-sm  dark:" style={{color: "rgb(71, 85, 105)"}}>
            Manage database catalogs and configure schema discovery
          </p>
        </div>
      </div>

      <Suspense fallback={<div className="text-center py-8  dark:" style={{color: "rgb(71, 85, 105)"}}>Loading catalogs...</div>}>
        <CatalogsContent />
      </Suspense>
    </div>
  );
}
