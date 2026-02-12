import React from 'react';

export const Alert = ({ children, variant, ...rest }: { children?: React.ReactNode; variant?: "default" | "destructive" } & React.HTMLAttributes<HTMLDivElement>) => {
  const variantStyles = {
    default: "border",
    destructive: "bg-red-950/50 border-red-900/50 text-red-200",
  };

  return (
    <div
      role="alert"
      className={`border px-4 py-3 rounded ${variantStyles[variant || "default"]}`}
      style={variant === "default" ? { borderColor: "var(--border)", backgroundColor: "var(--surface-elevated)", color: "#e2e8f0" } : {}}
      {...rest}
    >
      {children}
    </div>
  );
};

export const AlertDescription = ({ children, ...rest }: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return <div {...rest}>{children}</div>;
};
