import * as React from "react"

import { cn } from "@/lib/utils"

type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[80px] w-full rounded-md border px-3 py-2 text-sm ring-offset-white focus-visible:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
      style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-base)", color: "var(--foreground)" }}
    />
  )
)
Textarea.displayName = "Textarea"

export { Textarea }
