import { Suspense } from "react";
import AssetsPageContent from "./assets-content";

export default function AssetsPage() {
    return (
        <Suspense fallback={
            <div className="space-y-6">
                <div className="flex justify-between items-center rounded-2xl border border-variant bg-surface-elevated p-5 shadow-sm dark:border-variant dark:bg-surface-base">
                    <div className="flex gap-6">
                        <div className="h-10 w-40 animate-pulse rounded-lg bg-surface-elevated dark:bg-surface-elevated" />
                        <div className="h-10 w-40 animate-pulse rounded-lg bg-surface-elevated dark:bg-surface-elevated" />
                    </div>
                    <div className="h-10 w-32 animate-pulse rounded-xl bg-sky-600" />
                </div>
                <div className="h-96 animate-pulse rounded-2xl border border-variant bg-surface-elevated dark:border-variant dark:bg-surface-base" />
            </div>
        }>
            <AssetsPageContent />
        </Suspense>
    );
}
