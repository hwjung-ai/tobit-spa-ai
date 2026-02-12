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
    <label className={`form-field-group ${className}`}>
      <span className="form-field-label">
        {label}
        {required && <span className="form-field-label-required">*</span>}
      </span>
      {children}
      {error && (
        <span className="form-field-error">
          ⚠ {error}
        </span>
      )}
      {help && (
        <span className="form-field-help">
          {help}
        </span>
      )}
    </label>
  );
}
