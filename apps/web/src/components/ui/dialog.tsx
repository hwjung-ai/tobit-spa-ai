import React, { useCallback, useEffect } from 'react';
import { cn } from "@/lib/utils";

type DialogProps = {
  open: boolean;
  onOpenChange?: (open: boolean) => void;
  children?: React.ReactNode;
} & React.HTMLAttributes<HTMLDivElement>;

export const Dialog = ({ open, onOpenChange, children, ...rest }: DialogProps) => {
  const handleClose = useCallback(() => {
    if (onOpenChange) {
      onOpenChange(false);
    }
  }, [onOpenChange]);

  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        handleClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [open, handleClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        aria-hidden="true"
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200"
        onClick={handleClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative z-10 w-full flex justify-center animate-in zoom-in-95 duration-200"
        {...rest}
      >
        {children}
      </div>
    </div>
  );
};

export const DialogContent = (props: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  const { children, className, ...rest } = props;
  return (
    <div
      className={cn(
        "bg-slate-950 border border-slate-800 p-6 shadow-2xl rounded-2xl",
        className
      )}
      {...rest}
    >
      {children}
    </div>
  );
};

export const DialogDescription = (props: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  const { children, className, ...rest } = props;
  return (
    <div
      className={cn("text-sm text-slate-400", className)}
      {...rest}
    >
      {children}
    </div>
  );
};

export const DialogHeader = (props: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  const { children, className, ...rest } = props;
  return (
    <div
      className={cn("flex flex-col space-y-1.5 text-center sm:text-left", className)}
      {...rest}
    >
      {children}
    </div>
  );
};

export const DialogTitle = (props: { children?: React.ReactNode } & React.HTMLAttributes<HTMLHeadingElement>) => {
  const { children, className, ...rest } = props;
  return (
    <h2
      className={cn("text-lg font-semibold leading-none tracking-tight text-white", className)}
      {...rest}
    >
      {children}
    </h2>
  );
};

export const DialogFooter = (props: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  const { children, className, ...rest } = props;
  return (
    <div
      className={cn("flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 pt-4", className)}
      {...rest}
    >
      {children}
    </div>
  );
};

export const DialogTrigger = ({ children, onClick, ...rest }: { children?: React.ReactNode; onClick?: () => void } & React.ButtonHTMLAttributes<HTMLButtonElement>) => {
  return (
    <button
      onClick={onClick}
      {...rest}
    >
      {children}
    </button>
  );
};
