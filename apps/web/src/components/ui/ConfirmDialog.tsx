"use client";

import React, { useRef, useEffect, useCallback } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./dialog";
import { Button } from "./button";

export interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  onConfirm: () => void;
}

export default function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  onConfirm,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  const handleConfirm = useCallback(() => {
    onConfirm();
    onOpenChange(false);
  }, [onConfirm, onOpenChange]);

  // Auto-focus Cancel button when dialog opens (safe default)
  useEffect(() => {
    if (open) {
      // Small delay to ensure DOM is ready
      const t = setTimeout(() => cancelRef.current?.focus(), 50);
      return () => clearTimeout(t);
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="bg-slate-950 border border-slate-800 shadow-2xl rounded-2xl p-6 max-w-sm mx-auto"
        onKeyDown={(e: React.KeyboardEvent) => {
          if (e.key === "Enter") {
            e.preventDefault();
            handleConfirm();
          }
        }}
      >
        <DialogHeader className="space-y-2">
          <DialogTitle className="text-lg font-semibold text-slate-100">{title}</DialogTitle>
          {description ? (
            <DialogDescription className="text-sm text-slate-400">{description}</DialogDescription>
          ) : null}
        </DialogHeader>
        <DialogFooter className="mt-6 flex justify-end gap-2">
          <Button
            ref={cancelRef}
            variant="ghost"
            size="sm"
            onClick={() => onOpenChange(false)}
          >
            {cancelLabel}
          </Button>
          <Button variant="destructive" size="sm" onClick={handleConfirm}>
            {confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
