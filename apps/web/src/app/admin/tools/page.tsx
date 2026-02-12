import { Suspense } from "react";
import ToolsPageContent from "./tools-content";

export default function ToolsPage() {
    return (
        <Suspense fallback={
            <div className="space-y-6">
                <div className="flex justify-between items-center rounded-2xl border p-5 shadow-sm" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
                    <div className="flex gap-6">
                        <div className="h-10 w-40 animate-pulse rounded-lg" style={{backgroundColor: "var(--surface-elevated)"}} />
                        <div className="h-10 w-40 animate-pulse rounded-lg" style={{backgroundColor: "var(--surface-elevated)"}} />
                    </div>
                    <div className="h-10 w-32 animate-pulse rounded-xl bg-sky-600" />
                </div>
                <div className="h-96 animate-pulse rounded-2xl border" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}} />
            </div>
        }>
            <ToolsPageContent />
        </Suspense>
    );
}
