import React from 'react';

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline';
}

const variantStyles = {
  default: 'inline-flex items-center rounded-full border border-transparent bg-blue-600 px-2.5 py-0.5 text-xs font-semibold text-white',
  secondary: 'inline-flex items-center rounded-full border border-transparent bg-slate-600 px-2.5 py-0.5 text-xs font-semibold text-white',
  destructive: 'inline-flex items-center rounded-full border border-transparent bg-red-600 px-2.5 py-0.5 text-xs font-semibold text-white',
  outline: 'inline-flex items-center rounded-full border border-slate-300 px-2.5 py-0.5 text-xs font-semibold text-slate-700',
};

export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ variant = 'default', className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`${variantStyles[variant]} ${className ?? ''}`}
        {...props}
      />
    );
  }
);

Badge.displayName = 'Badge';
