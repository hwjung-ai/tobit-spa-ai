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
    <div className={`space-y-3 rounded-xl border border-slate-700 bg-slate-900/30 p-4 ${className}`}>
      <div>
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        {description && (
          <p className="mt-1 text-[11px] text-slate-400">{description}</p>
        )}
      </div>
      <div className={gridClass ? `grid ${gridClass} gap-4` : ""}>
        {children}
      </div>
    </div>
  );
}
