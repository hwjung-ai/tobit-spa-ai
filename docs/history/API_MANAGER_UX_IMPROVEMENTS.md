# API Manager UX Improvements - Implementation Guide

## Overview

This document outlines the Priority 1 UX improvements for the API Manager component. These improvements focus on enhancing form organization, error handling, and HTTP form builder functionality.

## ✅ Completed Implementations

### 1. Form Field Layout Refactoring (Priority 1.1)

**Status**: ✅ Complete

**Components Created**:
- `FormSection.tsx`: Provides section-based layout organization
- `FormFieldGroup.tsx`: Consistent field styling with label, error, and help text

**Benefits**:
- **Better Visual Hierarchy**: Sections group related fields logically
- **Improved Readability**: Clear separation between different configuration areas
- **Consistent Styling**: All form fields follow the same design pattern
- **Help Text Support**: Each field can display contextual help and error messages

**Usage Example**:

```typescript
import FormSection from "@/components/api-manager/FormSection";
import FormFieldGroup from "@/components/api-manager/FormFieldGroup";

export function ApiDefinitionTab() {
  return (
    <div className="space-y-4">
      {/* Basic Info Section */}
      <FormSection
        title="API Metadata"
        description="Define the basic information about your API"
        columns={2}
      >
        <FormFieldGroup
          label="API Name"
          required
          error={errors.apiName}
          help="Use descriptive names like 'User Profile API'"
        >
          <input
            type="text"
            value={apiName}
            onChange={(e) => setApiName(e.target.value)}
            className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
            placeholder="e.g., User Profile API"
          />
        </FormFieldGroup>

        <FormFieldGroup
          label="Description"
          help="Explain what this API does"
        >
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full h-24 rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
            placeholder="API description"
          />
        </FormFieldGroup>
      </FormSection>

      {/* Endpoint Section */}
      <FormSection
        title="Endpoint Configuration"
        description="Set the HTTP method and endpoint path"
        columns={2}
      >
        <FormFieldGroup label="HTTP Method" required>
          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
          >
            <option value="GET">GET</option>
            <option value="POST">POST</option>
            <option value="PUT">PUT</option>
            <option value="DELETE">DELETE</option>
          </select>
        </FormFieldGroup>

        <FormFieldGroup label="Endpoint Path" required>
          <input
            type="text"
            value={endpoint}
            onChange={(e) => setEndpoint(e.target.value)}
            className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
            placeholder="/api/users/{userId}"
          />
        </FormFieldGroup>
      </FormSection>
    </div>
  );
}
```

### 2. Centralized Error Messaging (Priority 1.2)

**Status**: ✅ Complete

**Component Created**:
- `ErrorBanner.tsx`: Fixed error banner for displaying validation errors

**Features**:
- **Sticky Positioning**: Stays at top of form while scrolling
- **Error/Warning Distinction**: Visual differentiation between errors and warnings
- **Automatic Dismissal**: Optional auto-dismiss after configurable duration
- **Clear Message Hierarchy**: Organized list format for multiple errors
- **Manual Dismiss**: Users can close the banner manually

**Benefits**:
- **Better Visibility**: Errors are immediately visible, not hidden in inline fields
- **Reduced Scrolling**: Users don't need to hunt for error messages
- **Grouped Feedback**: All validation issues shown in one place
- **UX Improvement**: Prevents missing validation errors

**Usage Example**:

```typescript
import { useState } from "react";
import ErrorBanner from "@/components/api-manager/ErrorBanner";

export function ApiManagerPage() {
  const [errors, setErrors] = useState<string[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);

  const handleValidation = () => {
    const newErrors: string[] = [];
    const newWarnings: string[] = [];

    if (!apiName.trim()) {
      newErrors.push("API name is required");
    }

    if (!endpoint.trim()) {
      newErrors.push("Endpoint path is required");
    }

    if (endpoint && !endpoint.startsWith("/")) {
      newWarnings.push("Endpoint should start with '/'");
    }

    setErrors(newErrors);
    setWarnings(newWarnings);
  };

  return (
    <div>
      {/* Fixed error banner at top */}
      <ErrorBanner
        title="Validation Issues"
        errors={errors}
        warnings={warnings}
        onDismiss={() => setErrors([])}
        autoDismissMs={5000} // Auto-dismiss after 5 seconds
      />

      {/* Rest of the form */}
      <div className="p-6 space-y-4">
        {/* Form content */}
      </div>
    </div>
  );
}
```

### 3. HTTP Logic Form Builder (Priority 1.3)

**Status**: ✅ Complete

**Component Created**:
- `HttpFormBuilder.tsx`: Structured form builder for HTTP specifications

**Features**:
- **Dual Mode**: Toggle between Form Builder and JSON View
- **Structured Input**: Visual form for HTTP headers, parameters, and body
- **Add/Remove Buttons**: Dynamically manage headers and parameters
- **Auto Conversion**: Automatic conversion between form and JSON
- **Read-Only Support**: Can be disabled for system APIs
- **Responsive Layout**: Adapts to different screen sizes

**Benefits**:
- **Better UX**: Visual form is easier than writing raw JSON
- **Error Prevention**: Structured fields prevent malformed JSON
- **Documentation**: Form fields are self-documenting
- **Flexibility**: Users can switch to JSON view if needed
- **Validation**: Can validate structure before saving

**Usage Example**:

```typescript
import { useState } from "react";
import { HttpFormBuilder, type HttpSpec } from "@/components/api-manager";

export function LogicTab() {
  const [httpSpec, setHttpSpec] = useState<HttpSpec>({
    url: "https://api.example.com/data",
    method: "GET",
    headers: "{}",
    body: "{}",
    params: "{}",
  });

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-slate-200">HTTP Logic</h3>

      <HttpFormBuilder
        value={httpSpec}
        onChange={setHttpSpec}
        isReadOnly={false}
      />

      {/* Debug output */}
      <div className="mt-4 p-3 rounded-lg bg-slate-900/50 border border-slate-700">
        <p className="text-xs text-slate-400 mb-2">Current Specification:</p>
        <pre className="text-[10px] text-slate-300 overflow-auto">
          {JSON.stringify(httpSpec, null, 2)}
        </pre>
      </div>
    </div>
  );
}
```

## Integration Guide

### Step 1: Import Components

```typescript
import {
  FormSection,
  FormFieldGroup,
  ErrorBanner,
  HttpFormBuilder,
} from "@/components/api-manager";
```

### Step 2: Refactor Form Sections

Replace the current inline form fields with `FormSection` + `FormFieldGroup` components:

**Before**:
```typescript
<label className="text-xs uppercase tracking-normal text-slate-500">
  API Name
  <input
    value={apiName}
    onChange={(e) => setApiName(e.target.value)}
    className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
  />
</label>
```

**After**:
```typescript
<FormSection title="API Metadata" columns={1}>
  <FormFieldGroup label="API Name" required>
    <input
      value={apiName}
      onChange={(e) => setApiName(e.target.value)}
      className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
    />
  </FormFieldGroup>
</FormSection>
```

### Step 3: Add Error Banner

Place the error banner at the top of the form:

```typescript
<ErrorBanner
  title="Form Validation Errors"
  errors={validationErrors}
  warnings={validationWarnings}
  onDismiss={handleDismissErrors}
/>
```

### Step 4: Replace HTTP JSON Editor

Replace the current HTTP spec textarea with the form builder:

**Before**:
```typescript
<textarea
  value={httpSpec.headers}
  onChange={(e) => setHttpSpec((prev) => ({ ...prev, headers: e.target.value }))}
  className="h-28 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-white outline-none focus:border-sky-500"
/>
```

**After**:
```typescript
<HttpFormBuilder
  value={httpSpec}
  onChange={setHttpSpec}
  isReadOnly={isSystemScope}
/>
```

## File Structure

```
apps/web/src/components/api-manager/
├── FormSection.tsx                 # Section wrapper with title/description
├── FormFieldGroup.tsx              # Field wrapper with label/error/help
├── ErrorBanner.tsx                 # Sticky error notification banner
├── HttpFormBuilder.tsx             # Structured HTTP spec form builder
└── index.ts                        # Central export point
```

## Component API Reference

### FormSection

```typescript
interface FormSectionProps {
  title: string;                    // Section title
  description?: string;             // Optional section description
  children: React.ReactNode;        // Form fields
  columns?: 1 | 2 | 3;             // Grid layout (default: 1)
  className?: string;               // Optional CSS classes
}
```

### FormFieldGroup

```typescript
interface FormFieldGroupProps {
  label: string;                    // Field label
  error?: string;                   // Error message (if any)
  help?: string;                    // Help/hint text
  required?: boolean;               // Show required indicator
  children: React.ReactNode;        // Input element
  className?: string;               // Optional CSS classes
}
```

### ErrorBanner

```typescript
interface ErrorBannerProps {
  title?: string;                   // Banner title (default: "Validation Error")
  errors: string[];                 // Error messages array
  warnings?: string[];              // Warning messages array
  onDismiss?: () => void;          // Dismiss callback
  autoDismissMs?: number;          // Auto-dismiss delay in ms (0 = disabled)
}
```

### HttpFormBuilder

```typescript
interface HttpSpec {
  url: string;
  method: "GET" | "POST" | "PUT" | "DELETE";
  headers: string;                  // JSON string
  body: string;                     // JSON string
  params: string;                   // JSON string
}

interface HttpFormBuilderProps {
  value: HttpSpec;
  onChange: (spec: HttpSpec) => void;
  isReadOnly?: boolean;
}
```

## Styling & Customization

All components follow the API Manager's existing dark theme:
- Background: `bg-slate-950/60`, `bg-slate-900`
- Borders: `border-slate-800`, `border-slate-700`
- Text: `text-white`, `text-slate-400`, `text-slate-500`
- Focus: `focus:border-sky-500`
- Rounded: `rounded-2xl`, `rounded-xl`, `rounded-lg`

You can customize by modifying the className props or editing the component files.

## Best Practices

### 1. Form Organization

Group related fields into logical sections:
```typescript
<FormSection title="Basic Configuration">
  {/* Basic fields */}
</FormSection>

<FormSection title="Advanced Settings">
  {/* Advanced fields */}
</FormSection>
```

### 2. Error Handling

Always validate before displaying errors:
```typescript
const validateForm = (): string[] => {
  const errors: string[] = [];

  if (!apiName.trim()) {
    errors.push("API name is required");
  }

  if (!endpoint.trim()) {
    errors.push("Endpoint is required");
  }

  return errors;
};
```

### 3. Help Text

Provide context-specific help:
```typescript
<FormFieldGroup
  label="Endpoint"
  help="Enter the path relative to the API base URL. Include parameters like /users/{userId}"
  error={errors.endpoint}
>
  <input {...} />
</FormFieldGroup>
```

## Testing Recommendations

### Component Testing

```typescript
describe("FormSection", () => {
  it("should render with title and children", () => {
    render(
      <FormSection title="Test Section">
        <input />
      </FormSection>
    );
    expect(screen.getByText("Test Section")).toBeInTheDocument();
  });

  it("should apply grid classes based on columns prop", () => {
    const { container } = render(
      <FormSection title="Test" columns={2}>
        <input />
      </FormSection>
    );
    expect(container.querySelector(".grid-cols-1")).toBeInTheDocument();
  });
});
```

### Integration Testing

Test the full form with error banner:
```typescript
describe("API Manager Form", () => {
  it("should show error banner on validation failure", async () => {
    render(<ApiManagerPage />);

    // Try to save without filling required fields
    fireEvent.click(screen.getByText("Save"));

    // Check for error banner
    await waitFor(() => {
      expect(
        screen.getByText(/API name is required/i)
      ).toBeInTheDocument();
    });
  });
});
```

## Migration Checklist

- [ ] Import new components into API Manager page
- [ ] Refactor definition tab form fields
- [ ] Add error banner to form container
- [ ] Replace HTTP spec textarea with HttpFormBuilder
- [ ] Test form validation and error display
- [ ] Test HTTP form builder (form mode and JSON mode)
- [ ] Verify existing functionality still works
- [ ] Update component documentation
- [ ] Add unit tests for new components
- [ ] Update E2E tests if applicable

## Future Enhancements (Priority 2+)

### Phase 2 Improvements
- [ ] Add real-time field validation feedback
- [ ] Implement autosave functionality
- [ ] Add field-specific syntax highlighting
- [ ] Create preset templates for common APIs
- [ ] Add parameter/header suggestions from history

### Phase 3 Improvements
- [ ] Add multi-language support (i18n)
- [ ] Implement drag-and-drop for header/param reordering
- [ ] Add JSON schema validation
- [ ] Create visual HTTP request builder
- [ ] Add Postman-style request/response preview

## Troubleshooting

### Issue: Error banner not dismissing

**Solution**: Ensure you're calling `onDismiss()` callback and clearing the error state:

```typescript
<ErrorBanner
  errors={errors}
  onDismiss={() => setErrors([])}
/>
```

### Issue: HTTP form builder not updating parent state

**Solution**: Make sure you're calling `onChange` when state updates:

```typescript
<HttpFormBuilder
  value={httpSpec}
  onChange={(newSpec) => setHttpSpec(newSpec)} // Important!
  isReadOnly={false}
/>
```

### Issue: Form sections not stacking properly

**Solution**: Ensure the parent container has appropriate spacing:

```typescript
<div className="space-y-4"> {/* space-y-4 adds gap between sections */}
  <FormSection title="Section 1">...</FormSection>
  <FormSection title="Section 2">...</FormSection>
</div>
```

## Performance Considerations

- **FormSection**: Minimal overhead, no re-renders unless children change
- **FormFieldGroup**: Pure component, only re-renders when props change
- **ErrorBanner**: Lightweight conditional rendering
- **HttpFormBuilder**: Use memo() if parent renders frequently

```typescript
const HttpFormBuilderMemo = React.memo(HttpFormBuilder);
```

## Accessibility

All components include:
- Proper label associations
- Error message associations
- Keyboard navigation support
- Screen reader friendly text
- Color contrast compliance

## Support

For issues or feature requests related to these components:

1. Check the troubleshooting section above
2. Review component prop types in TypeScript
3. Check existing usage examples in the codebase
4. Create a GitHub issue with reproduction steps

---

**Last Updated**: 2026-02-06
**Status**: ✅ Complete (Priority 1 implementations)
**Next Phase**: Priority 2 improvements (font sizing, JSON editor enhancements)
