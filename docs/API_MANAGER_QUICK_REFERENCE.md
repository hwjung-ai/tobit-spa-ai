# API Manager Components - Quick Reference

## 🚀 Quick Start

### 1. Import Components
```typescript
import {
  FormSection,
  FormFieldGroup,
  ErrorBanner,
  HttpFormBuilder,
} from "@/components/api-manager";
```

### 2. Use in Your Form
```typescript
import { useState } from "react";
import { ErrorBanner, FormSection, FormFieldGroup } from "@/components/api-manager";

export function MyForm() {
  const [errors, setErrors] = useState<string[]>([]);
  const [apiName, setApiName] = useState("");

  return (
    <div>
      <ErrorBanner errors={errors} onDismiss={() => setErrors([])} />

      <div className="space-y-4">
        <FormSection title="Basic Information" columns={1}>
          <FormFieldGroup
            label="API Name"
            required
            error={errors.includes("API name required") ? "API name is required" : undefined}
            help="Enter a descriptive name for your API"
          >
            <input
              value={apiName}
              onChange={(e) => setApiName(e.target.value)}
              className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white"
            />
          </FormFieldGroup>
        </FormSection>
      </div>
    </div>
  );
}
```

---

## 📋 Component Cheat Sheet

### FormSection
Wraps related fields into a visual section

```typescript
<FormSection
  title="Section Title"                 // Required
  description="Optional description"    // Optional
  columns={2}                          // 1, 2, or 3 (default: 1)
  className="custom-class"             // Optional
>
  {/* FormFieldGroup or other content */}
</FormSection>
```

**Best Practices**:
- Use columns={2} for small forms
- Use columns={1} for single-column layouts
- Group related fields (e.g., method + endpoint)

---

### FormFieldGroup
Wraps an input element with label, error, and help

```typescript
<FormFieldGroup
  label="Field Label"                  // Required
  error="Error message"                // Show if validation fails
  help="Helpful hint text"             // Optional helper text
  required={true}                      // Shows * if true
  className="optional-class"           // Optional
>
  <input {...props} />                 // Any form element
</FormFieldGroup>
```

**Best Practices**:
- Always use for consistency
- Keep error messages short and actionable
- Use help text to explain complex fields
- Mark all required fields with required={true}

---

### ErrorBanner
Shows validation errors and warnings at top of form

```typescript
<ErrorBanner
  title="Form Errors"                  // Default: "Validation Error"
  errors={["Error 1", "Error 2"]}      // Array of error messages
  warnings={["Warning 1"]}              // Array of warning messages (optional)
  onDismiss={() => {}}                 // Callback when dismissed
  autoDismissMs={5000}                 // Auto-dismiss after 5 seconds (0 = never)
/>
```

**Best Practices**:
- Place at top of scrollable form
- Clear errors when user submits
- Use for form-level validation, not field-level
- Keep messages under 100 characters each

---

### HttpFormBuilder
Provides form-based HTTP spec editing

```typescript
import { HttpFormBuilder, type HttpSpec } from "@/components/api-manager";

const [httpSpec, setHttpSpec] = useState<HttpSpec>({
  url: "https://api.example.com",
  method: "GET",
  headers: "{}",
  body: "{}",
  params: "{}",
});

<HttpFormBuilder
  value={httpSpec}
  onChange={setHttpSpec}
  isReadOnly={false}
/>
```

**Best Practices**:
- Initialize with empty or default values
- Use HttpSpec type for TypeScript support
- Set isReadOnly={true} for system APIs
- Headers/body/params stored as JSON strings internally

---

## 🎯 Common Patterns

### Pattern 1: Simple Form
```typescript
<div className="space-y-4">
  <FormSection title="Settings" columns={1}>
    <FormFieldGroup label="Name" required>
      <input {...} />
    </FormFieldGroup>
    <FormFieldGroup label="Description">
      <textarea {...} />
    </FormFieldGroup>
  </FormSection>
</div>
```

### Pattern 2: Two-Column Layout
```typescript
<FormSection title="Configuration" columns={2}>
  <FormFieldGroup label="Method">
    <select {...} />
  </FormFieldGroup>
  <FormFieldGroup label="Endpoint">
    <input {...} />
  </FormFieldGroup>
</FormSection>
```

### Pattern 3: Form with Errors
```typescript
<div>
  <ErrorBanner
    errors={validationErrors}
    warnings={validationWarnings}
    onDismiss={clearErrors}
    autoDismissMs={5000}
  />

  <div className="space-y-4 mt-4">
    {/* Form sections */}
  </div>
</div>
```

### Pattern 4: HTTP Spec Configuration
```typescript
<FormSection title="HTTP Configuration">
  <HttpFormBuilder
    value={httpSpec}
    onChange={(newSpec) => {
      // Update parent state
      setHttpSpec(newSpec);
    }}
    isReadOnly={isSystemApi}
  />
</FormSection>
```

---

## 🔧 Customization

### Change Colors
All components use Tailwind classes. Modify the component files:

```typescript
// In FormSection.tsx
className={`space-y-3 rounded-xl border border-slate-700 bg-slate-900/30 p-4`}
//                                              ^^^^^^ Change these
```

### Change Spacing
Use the className prop:

```typescript
<FormSection className="p-6">  {/* Larger padding */}
  {/* content */}
</FormSection>
```

### Extend Components
Create wrapper components for specific use cases:

```typescript
// MyCustomFormSection.tsx
export function MyFormSection({ title, children }: any) {
  return (
    <FormSection title={title} className="bg-blue-900/20">
      {children}
    </FormSection>
  );
}
```

---

## 🧪 Testing Examples

### Test FormFieldGroup
```typescript
import { render, screen } from "@testing-library/react";
import FormFieldGroup from "@/components/api-manager/FormFieldGroup";

it("should display label", () => {
  render(
    <FormFieldGroup label="Test Label">
      <input />
    </FormFieldGroup>
  );
  expect(screen.getByText("Test Label")).toBeInTheDocument();
});

it("should display error message", () => {
  render(
    <FormFieldGroup label="Test" error="Field is required">
      <input />
    </FormFieldGroup>
  );
  expect(screen.getByText(/Field is required/)).toBeInTheDocument();
});
```

### Test ErrorBanner
```typescript
it("should show error banner when errors exist", () => {
  render(
    <ErrorBanner
      title="Errors"
      errors={["Error 1", "Error 2"]}
    />
  );
  expect(screen.getByText(/Error 1/)).toBeInTheDocument();
});

it("should hide banner when dismissed", () => {
  const { rerender } = render(
    <ErrorBanner errors={["Error"]} />
  );

  fireEvent.click(screen.getByText("✕"));
  // Banner should disappear
});
```

---

## 🐛 Troubleshooting

### Issue: Component not found
**Solution**: Check import path and filename casing
```typescript
// ✓ Correct
import { FormSection } from "@/components/api-manager";

// ✗ Wrong
import { FormSection } from "@/components/ApiManager";
```

### Issue: Styles not applying
**Solution**: Ensure Tailwind CSS is configured and parent has required classes
```typescript
// Parent needs spacing
<div className="space-y-4">
  <FormSection>...</FormSection>
  <FormSection>...</FormSection>
</div>
```

### Issue: Error banner not showing
**Solution**: Ensure you're setting non-empty errors array
```typescript
// ✓ Correct
const [errors, setErrors] = useState<string[]>(["Error message"]);

// ✗ Wrong - component checks array length
const [errors, setErrors] = useState<string[]>([]);
```

### Issue: HttpFormBuilder not updating
**Solution**: Ensure onChange callback is properly set
```typescript
// ✓ Correct
<HttpFormBuilder
  value={spec}
  onChange={(newSpec) => setSpec(newSpec)}  // Required!
/>

// ✗ Wrong - no callback
<HttpFormBuilder value={spec} />
```

---

## 📚 Full Documentation

For complete documentation, examples, and API reference:
→ See `docs/API_MANAGER_UX_IMPROVEMENTS.md`

For summary and status:
→ See `docs/API_MANAGER_IMPROVEMENTS_SUMMARY.md`

---

## ⚡ Quick Commands

```bash
# Check component types
cat apps/web/src/components/api-manager/FormSection.tsx

# View all components
ls -la apps/web/src/components/api-manager/

# Search for component usage
grep -r "FormSection" apps/web/src/

# Run tests
npm test -- api-manager
```

---

**Last Updated**: 2026-02-06
**Quick Reference Version**: 1.0
