# Test IDs (data-testid) Naming Convention

This document defines the standard naming convention for `data-testid` attributes across the Tobit SPA AI project, particularly for U3-Entry implementation.

## Purpose

- **E2E Test Stability**: Enables Playwright tests to locate elements reliably without depending on CSS classes or component structure
- **Regression Testing**: Allows tests to remain stable even when UI styling or DOM structure changes
- **Maintainability**: Clear naming convention makes it easy to understand test selectors
- **Accessibility**: Improves overall test coverage and reliability

## Naming Convention

### Format

```
{area}-{component}-{purpose}-{identifier}
```

Where:
- **area**: Feature area (e.g., `screen`, `admin`, `component`, `layout`)
- **component**: Component type (e.g., `button`, `input`, `table`, `modal`)
- **purpose**: What it does (e.g., `create`, `edit`, `delete`, `publish`)
- **identifier**: Optional, specific identifier (e.g., asset ID, screen ID)

### Examples

#### Screen Management

```
screen-asset-{asset_id}           # Screen asset card
link-screen-{asset_id}            # Link to edit screen
btn-edit-{asset_id}               # Edit button
btn-publish-{asset_id}            # Publish button
btn-rollback-{asset_id}           # Rollback to draft button
status-badge-{asset_id}           # Status badge
```

#### Screen Editor

```
input-screen-name                 # Screen name input
textarea-screen-description       # Screen description textarea
textarea-schema-json              # Schema JSON editor
btn-save-draft                    # Save draft button
btn-publish-screen                # Publish button
btn-rollback-screen               # Rollback button
```

#### Admin Panel

```
btn-create-screen                 # Create new screen button
modal-create-screen               # Create screen modal
input-screen-id                   # Screen ID input in create modal
input-screen-name                 # Screen name input in create modal
input-screen-description          # Screen description input
btn-cancel-create                 # Cancel create button
btn-confirm-create                # Confirm create button
input-search-screens              # Search screens input
select-filter-status              # Status filter dropdown
```

#### Layout Renderers

```
layout-grid                       # Grid layout container
layout-stack-vertical             # Vertical stack layout
layout-stack-horizontal           # Horizontal stack layout
layout-list                       # List layout container
layout-modal                      # Modal layout container
layout-default                    # Default/fallback layout
grid-item-{component_id}          # Individual grid item
list-item-{component_id}          # Individual list item
```

#### Components

```
component-text-{component_id}     # Text component
component-markdown-{component_id} # Markdown component
component-button-{component_id}   # Button component
component-input-{component_id}    # Input component
component-table-{component_id}    # Table component
component-chart-{component_id}    # Chart component
component-badge-{component_id}    # Badge component
component-tabs-{component_id}     # Tabs component
component-modal-{component_id}    # Modal component
component-keyvalue-{component_id} # Key-value component
component-divider-{component_id}  # Divider component
```

#### Screen Renderer

```
screen-renderer-{screen_id}       # Main screen renderer container
```

## Best Practices

1. **Consistency**: Always use lowercase with hyphens, never camelCase or snake_case
2. **Specificity**: Make IDs specific enough to uniquely identify elements during testing
3. **Stability**: Avoid using indices or dynamically generated IDs that change on re-renders
4. **Readability**: Use clear, descriptive names that indicate the element's purpose
5. **Non-intrusive**: data-testid attributes should not affect styling or functionality

## Example Selectors in Playwright

```typescript
// Screen asset list
await page.locator('[data-testid="btn-create-screen"]').click();

// Fill create modal
await page.locator('[data-testid="input-screen-id"]').fill('dashboard_main');
await page.locator('[data-testid="input-screen-name"]').fill('Main Dashboard');

// Submit create modal
await page.locator('[data-testid="btn-confirm-create"]').click();

// Edit screen
await page.locator('[data-testid="btn-edit-{assetId}"]').click();

// Save draft
await page.locator('[data-testid="btn-save-draft"]').click();

// Publish screen
await page.locator('[data-testid="btn-publish-screen"]').click();

// Verify layout
const gridLayout = page.locator('[data-testid="layout-grid"]');
await expect(gridLayout).toBeVisible();

// Check component rendering
const textComp = page.locator('[data-testid="component-text-title"]');
await expect(textComp).toHaveText('Expected Text');
```

## Migration Guide

When adding data-testid to existing components:

1. Identify the component's role and purpose
2. Determine its location (admin, editor, renderer, etc.)
3. Apply the naming convention consistently
4. Update related Playwright tests to use the new selectors
5. Verify all tests pass with the new selectors

## Future Considerations

- As more components are added to U3, expand this guide with additional patterns
- Maintain consistency across frontend and backend test IDs
- Review and update this document with each U3 phase completion
