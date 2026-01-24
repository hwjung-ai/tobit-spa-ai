"use client";

import { useState, useCallback, ReactNode } from "react";
import ConfirmDialog from "@/components/ui/ConfirmDialog";

interface ConfirmOptions {
    title: string;
    description?: string | ReactNode;
    confirmLabel?: string;
    cancelLabel?: string;
    variant?: "default" | "destructive";
}

export function useConfirm() {
    const [promise, setPromise] = useState<{
        resolve: (value: boolean) => void;
    } | null>(null);

    const [options, setOptions] = useState<ConfirmOptions>({
        title: "Confirm Action",
        description: "Are you sure you want to proceed?",
    });

    const confirm = useCallback((newOptions: ConfirmOptions) => {
        setOptions(newOptions);
        return new Promise<boolean>((resolve) => {
            setPromise({ resolve });
        });
    }, []);

    const handleClose = () => {
        setPromise(null);
    };

    const handleCancel = () => {
        promise?.resolve(false);
        handleClose();
    };

    const handleConfirm = () => {
        promise?.resolve(true);
        handleClose();
    };

    const ConfirmDialogComponent = () => (
        <ConfirmDialog
            open={promise !== null}
            onOpenChange={(open) => {
                if (!open) handleCancel();
            }}
            title={options.title}
            description={typeof options.description === "string" ? options.description : undefined}
            confirmLabel={options.confirmLabel}
            cancelLabel={options.cancelLabel}
            onConfirm={handleConfirm}
        />
    );

    return [confirm, ConfirmDialogComponent] as const;
}
