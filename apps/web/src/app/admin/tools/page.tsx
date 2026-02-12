import { Suspense } from "react";
import ToolsPageContent from "./tools-content";

export default function ToolsPage() {
    return (
        <Suspense fallback={
            <div className="space-y-6">
                <div className="flex justify-between items-center rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-sm dark:border-slate-700 dark:bg-slate-900">
                    <div className="flex gap-6">
                        <div className="h-10 w-40 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
                        <div className="h-10 w-40 animate-pulse rounded-lg bg-slate-100 dark:bg-slate-800" />
                    </div>
                    <div className="h-10 w-32 animate-pulse rounded-xl bg-sky-600" />
                </div>
                <div className="h-96 animate-pulse rounded-2xl border border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-900" />
            </div>
        }>
            <ToolsPageContent />
        </Suspense>
    );
}
