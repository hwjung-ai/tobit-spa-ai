import React from 'react';
import { cn } from '@/lib/utils';

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline';
}

const variantStyles = {
  default: 'inline-flex items-center rounded-full border border-transparent bg-sky-600 px-3 py-0.5 text-xs font-semibold text-white',
  secondary: 'inline-flex items-center rounded-full border border-transparent bg-surface-elevated px-3 py-0.5 text-xs font-semibold text-white dark:bg-surface-elevated',
  destructive: 'inline-flex items-center rounded-full border border-transparent bg-rose-600 px-3 py-0.5 text-xs font-semibold text-white',
  outline: 'inline-flex items-center rounded-full border px-3 py-0.5 text-xs font-semibold text-foreground border-border',
};

export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ variant = 'default', className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(variantStyles[variant], className)}
        {...props}
      />
    );
  }
);

Badge.displayName = 'Badge';
