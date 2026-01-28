import { Suspense } from "react";
import SchemasContent from "./schemas-content";

export const metadata = {
  title: "Schemas - Admin",
  description: "Database Schema Asset Management",
};

export default function SchemasPage() {
  return (
    <div className="space-y-6">
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Schema Assets</h1>
          <p className="mt-2 text-sm text-gray-600">
            Manage database schema assets and configure schema discovery
          </p>
        </div>
      </div>

      <Suspense fallback={<div className="text-center py-8">Loading schemas...</div>}>
        <SchemasContent />
      </Suspense>
    </div>
  );
}
