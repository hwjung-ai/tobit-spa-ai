import React from 'react';

export const Alert = ({ children, variant, ...rest }: { children?: React.ReactNode; variant?: "default" | "destructive" } & React.HTMLAttributes<HTMLDivElement>) => {
  const variantStyles = {
    default: "bg-slate-800 border-slate-700 text-slate-200",
    destructive: "bg-red-950/50 border-red-900/50 text-red-200",
  };

  return (
    <div
      role="alert"
      className={`border px-4 py-3 rounded ${variantStyles[variant || "default"]}`}
      {...rest}
    >
      {children}
    </div>
  );
};

export const AlertDescription = ({ children, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return <div {...rest}>{children}</div>;
};
