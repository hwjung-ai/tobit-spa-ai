/**
 * Reusable form field wrapper with consistent styling
 * Handles label, input, error messages, and help text
 */

interface FormFieldGroupProps {
  label: string;
  error?: string;
  help?: string;
  required?: boolean;
  children: React.ReactNode;
  className?: string;
}

export default function FormFieldGroup({
  label,
  error,
  help,
  required = false,
  children,
  className = "",
}: FormFieldGroupProps) {
  return (
    <label className={`flex flex-col gap-1.5 ${className}`}>
      <span className="text-sm font-medium uppercase tracking-normal" style={{ color: "var(--muted-foreground)" }}>
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </span>
      {children}
      {error && (
        <span className="text-xs text-red-400">
          ⚠ {error}
        </span>
      )}
      {help && (
        <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>
          {help}
        </span>
      )}
    </label>
  );
}
