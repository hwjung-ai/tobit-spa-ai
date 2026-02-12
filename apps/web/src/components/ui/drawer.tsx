import React, { useCallback, useEffect } from 'react';
import { cn } from "@/lib/utils";

type DrawerProps = {
  open: boolean;
  onOpenChange?: (open: boolean) => void;
  children?: React.ReactNode;
} & React.HTMLAttributes<HTMLDivElement>;

export const Drawer = ({ open, onOpenChange, children, ...rest }: DrawerProps) => {
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
    <div className="fixed inset-0 z-50 flex justify-end">
      <div
        aria-hidden="true"
        className="fixed inset-0 backdrop-blur-sm animate-in fade-in duration-200"
        style={{ backgroundColor: "rgba(15, 23, 42, 0.8)" }}
        onClick={handleClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative z-10 w-full max-w-md h-full shadow-2xl animate-in slide-in-from-right duration-300"
        style={{ backgroundColor: "var(--surface-base)", borderLeft: "1px solid var(--border)" }}
        {...rest}
      >
        {children}
      </div>
    </div>
  );
};

export const DrawerContent = ({ children, className, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return (
    <div
      className={cn("flex flex-col h-full", className)}
      {...rest}
    >
      {children}
    </div>
  );
};

export const DrawerHeader = ({ children, className, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return (
    <div
      className={cn("flex flex-col space-y-1.5 p-6 text-center sm:text-left", className)}
      {...rest}
    >
      {children}
    </div>
  );
};

export const DrawerTitle = ({ children, className, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLHeadingElement>) => {
  return (
    <h2
      className={cn("text-lg font-semibold leading-none tracking-tight text-white", className)}
      {...rest}
    >
      {children}
    </h2>
  );
};

export const DrawerDescription = ({ children, className, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return (
    <p
      className={cn("text-sm", className)}
      style={{ color: "var(--muted-foreground)" }}
      {...rest}
    >
      {children}
    </p>
  );
};

export const DrawerFooter = ({ children, className, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return (
    <div
      className={cn("mt-auto flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 p-6 pt-0", className)}
      {...rest}
    >
      {children}
    </div>
  );
};

type DrawerCloseProps = {
  children: React.ReactNode;
  asChild?: boolean;
  onClick?: () => void;
} & React.ButtonHTMLAttributes<HTMLButtonElement>;

export const DrawerClose = ({ children, asChild = false, onClick, ...rest }: DrawerCloseProps) => {
  const handleClick = useCallback(() => {
    if (onClick) {
      onClick();
    }
  }, [onClick]);

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, {
      ...rest,
      onClick: handleClick,
    } as React.HTMLAttributes<HTMLButtonElement>);
  }

  return (
    <button
      onClick={handleClick}
      {...rest}
    >
      {children}
    </button>
  );
};
