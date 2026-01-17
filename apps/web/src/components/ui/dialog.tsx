import React, { useCallback, useEffect } from 'react';

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
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        aria-hidden="true"
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm"
        onClick={handleClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        className="relative z-10"
        {...rest}
      >
        {children}
      </div>
    </div>
  );
};

export const DialogContent = ({ children, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return <div {...rest}>{children}</div>;
};

export const DialogDescription = ({ children, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return <div {...rest}>{children}</div>;
};

export const DialogHeader = ({ children, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return <div {...rest}>{children}</div>;
};

export const DialogTitle = ({ children, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return <div {...rest}>{children}</div>;
};

export const DialogFooter = ({ children, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return <div {...rest}>{children}</div>;
};
