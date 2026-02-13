import React from "react";
import { cn } from "@/lib/utils";

export const Alert = ({
  children,
  variant,
  className,
  ...rest
}: {
  children?: React.ReactNode;
  variant?: "default" | "destructive";
  className?: string;
} & React.HTMLAttributes<HTMLDivElement>) => {
  const variantStyles = {
    default: "border-variant bg-surface-elevated text-foreground",
    destructive: "bg-rose-950/50 border-rose-900/50 text-rose-200",
  };

  return (
    <div
      role="alert"
      className={cn("border px-4 py-3 rounded", variantStyles[variant || "default"], className)}
      {...rest}
    >
      {children}
    </div>
  );
};

export const AlertDescription = ({
  children,
  ...rest
}: { children?: React.ReactNode } & React.HTMLAttributes<HTMLDivElement>) => {
  return <div {...rest}>{children}</div>;
};
