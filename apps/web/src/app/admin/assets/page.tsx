import { Suspense } from "react";
import AssetsPageContent from "./assets-content";

export default function AssetsPage() {
    return (
        <Suspense fallback={
            <div className="space-y-6">
                <div className="flex justify-between items-center rounded-2xl border  bg-white p-5 shadow-sm dark: dark:/90" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }}>
                    <div className="flex gap-6">
                        <div className="h-10 w-40 animate-pulse rounded-lg  dark:" style={{ backgroundColor: "var(--surface-elevated)" ,  backgroundColor: "var(--surface-elevated)" }} />
                        <div className="h-10 w-40 animate-pulse rounded-lg  dark:" style={{ backgroundColor: "var(--surface-elevated)" ,  backgroundColor: "var(--surface-elevated)" }} />
                    </div>
                    <div className="h-10 w-32 animate-pulse rounded-xl bg-sky-600" />
                </div>
                <div className="h-96 animate-pulse rounded-2xl border  bg-white dark: dark:/90" style={{ borderColor: "var(--border)" ,  borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }} />
            </div>
        }>
            <AssetsPageContent />
        </Suspense>
    );
}
