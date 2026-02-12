import React from 'react';

export const Alert = ({ children, variant, ...rest }: { children?: React.ReactNode; variant?: "default" | "destructive" } & React.HTMLAttributes<HTMLDivElement>) => {
  const variantStyles = {
    default: "border",
    destructive: "bg-rose-950/50 border-rose-900/50 text-rose-200",
  };

  return (
    <div
      role="alert"
      className={`border px-4 py-3 rounded ${variantStyles[variant || "default"]}`}
      style={variant === "default" ? { borderColor: "var(--border)", backgroundColor: "var(--surface-elevated)", color: "var(--foreground)" } : {}}
      {...rest}
    >
      {children}
    </div>
  );
};

export const AlertDescription = ({ children, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return <div {...rest}>{children}</div>;
};
