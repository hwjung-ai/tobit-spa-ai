/**
 * Reusable form section component for API Manager
 * Provides consistent styling and structure for form grouping
 */

interface FormSectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
  columns?: 1 | 2 | 3;
  className?: string;
}

export default function FormSection({
  title,
  description,
  children,
  columns = 1,
  className = "",
}: FormSectionProps) {
  const gridClass = {
    1: "",
    2: "grid-cols-1 md:grid-cols-2",
    3: "grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
  }[columns];

  return (
    <div className={`space-y-3 rounded-xl p-4 ${className}`} style={{ border: "1px solid var(--border-muted)", backgroundColor: "rgba(30, 41, 59, 0.3)" }}>
      <div>
        <h3 className="text-lg font-semibold" style={{ color: "var(--muted-foreground)" }}>{title}</h3>
        {description && (
          <p className="mt-1 text-xs" style={{ color: "var(--muted-foreground)" }}>{description}</p>
        )}
      </div>
      <div className={gridClass ? `grid ${gridClass} gap-4` : ""}>
        {children}
      </div>
    </div>
  );
}
