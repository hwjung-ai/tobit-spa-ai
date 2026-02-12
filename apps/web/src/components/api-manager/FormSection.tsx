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
    <div className={`form-section ${className}`}>
      <div>
        <h3 className="form-section-title">{title}</h3>
        {description && (
          <p className="form-section-description">{description}</p>
        )}
      </div>
      <div className={gridClass ? `grid ${gridClass} gap-4` : ""}>
        {children}
      </div>
    </div>
  );
}
