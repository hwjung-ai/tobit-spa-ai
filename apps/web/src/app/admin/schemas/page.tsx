import { Suspense } from "react";
import SchemasContent from "./schemas-content";

export default function SchemasPage() {
    return (
        <Suspense fallback={
            <div className="space-y-6">
                <div className="flex justify-between items-center bg-slate-900/50 rounded-2xl border border-slate-800 p-4 backdrop-blur-sm">
                    <div className="h-10 w-40 bg-slate-800 rounded-lg animate-pulse" />
                    <div className="h-10 w-32 bg-sky-600 rounded-xl animate-pulse" />
                </div>
                <div className="bg-slate-900/40 rounded-2xl border border-slate-800 h-96 animate-pulse" />
            </div>
        }>
            <SchemasContent />
        </Suspense>
    );
}
