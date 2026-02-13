# Dark Mode Variant Analysis - Missing dark: Prefixes

**Last Updated:** 2026-02-13  
**Scope:** Tailwind color classes missing `dark:` variants  
**Files Analyzed:** 35+ component files across `/apps/web/src/components/admin`, `/apps/web/src/components/ops`, `/apps/web/src/app`

---

## Executive Summary

**Total Issues Found:** 85+  
**Critical Priority:** 35+ (Primary buttons and main UI elements)  
**Medium Priority:** 30+ (Alert boxes, badges, status indicators)  
**Low Priority:** 20+ (Accent colors, opacity states)

**Most Common Issues:**
1. `bg-sky-600` without `dark:bg-sky-700` (23 instances)
2. Light backgrounds (`bg-*-50`) without dark variants (18 instances)
3. Text colors without dark variants (15+ instances)
4. Border colors in alert/status components (12 instances)

---

## Pattern 1: Primary Button Colors (bg-sky-600) - CRITICAL

### Summary
Primary action buttons using `bg-sky-600` lack dark mode variants. This affects user interactions across admin and ops interfaces.

### Files with Issues

| File | Lines | Issue | Recommended Fix |
|------|-------|-------|-----------------|
| ScreenAssetEditor.tsx | 451 | `bg-sky-600 hover:bg-sky-700` | Add `dark:bg-sky-700 dark:hover:bg-sky-600` |
| AssetTable.tsx | 28 | `bg-sky-600 text-white` (active tab) | Add `dark:bg-sky-700` |
| SystemSettingsPanel.tsx | 193 | `bg-sky-600 text-white hover:bg-sky-700` | Add `dark:bg-sky-700 dark:hover:bg-sky-600` |
| AssetForm.tsx | 623 | `bg-sky-600 hover:bg-sky-500` | Add `dark:bg-sky-700 dark:hover:bg-sky-600` |
| StageDiffView.tsx | 257 | `bg-sky-600 text-white rounded-lg hover:bg-sky-700` | Add `dark:bg-sky-700 dark:hover:bg-sky-600` |
| TraceDiffView.tsx | 500 | `bg-sky-600 text-white hover:bg-sky-700` | Add `dark:bg-sky-700 dark:hover:bg-sky-600` |
| ActionTab.tsx | 183, 194, 209, 221, 243, 402 | Multiple `bg-sky-600 text-white` instances | Add `dark:bg-sky-700 dark:hover:bg-sky-600` |
| CopilotPanel.tsx | 143 | `bg-sky-600 px-3 py-2 text-white hover:bg-sky-500` | Add `dark:bg-sky-700 dark:hover:bg-sky-600` |
| ScreenEditorHeader.tsx | 170, 263 | `bg-sky-600 hover:bg-sky-700 text-white` | Add `dark:bg-sky-700 dark:hover:bg-sky-600` |
| page.tsx | 57, 570 | `bg-sky-600 text-white` (hero buttons) | Add `dark:bg-sky-700` |
| admin/observability/page.tsx | 22 | `bg-sky-600 text-white` (tab styling) | Add `dark:bg-sky-700` |
| admin/explorer/page.tsx | 607, 652, 716, 741, 753, 765, 783, 795, 870, 883, 900 | 11 instances of `bg-sky-600 text-white border-sky-600` | Add `dark:bg-sky-700 dark:border-sky-700` |
| admin/assets/page.tsx | 13 | `bg-sky-600` (skeleton loader) | Add `dark:bg-sky-700` |
| admin/settings/page.tsx | 145, 156, 167, 333 | 4 instances of `bg-sky-600 text-white` | Add `dark:bg-sky-700` |
| admin/logs/page.tsx | 25, 26, 27, 28 | `bg-sky-600 text-white hover:bg-sky-500` (tabs) | Add `dark:bg-sky-700 dark:hover:bg-sky-600` |
| admin/tools/page.tsx | 13 | `bg-sky-600` (skeleton) | Add `dark:bg-sky-700` |
| tools-content.tsx | 151 | `bg-sky-600 hover:bg-sky-500 text-white` | Add `dark:bg-sky-700 dark:hover:bg-sky-600` |
| AssetOverrideDrawer.tsx | 272 | `bg-sky-600` (toggle styling) | Add `dark:bg-sky-700` |
| OrchestrationSection.tsx | 61, 74 | `bg-sky-600 text-white` (buttons) | Add `dark:bg-sky-700` |
| ConversationSummaryModal.tsx | 284 | `bg-sky-600 px-4 py-2 text-white hover:bg-sky-700` | Add `dark:bg-sky-700 dark:hover:bg-sky-600` |

**Total Instances:** 23+

**Recommended Fix Template:**
```jsx
// Before
className="bg-sky-600 hover:bg-sky-700 text-white"

// After
className="bg-sky-600 hover:bg-sky-700 dark:bg-sky-700 dark:hover:bg-sky-600 text-white"
```

---

## Pattern 2: Light Alert Backgrounds - MEDIUM PRIORITY

### Summary
Light colored alert backgrounds (`bg-*-50`) used for success/warning/error states lack dark mode variants.

### Files with Issues

| File | Lines | Issue | Recommended Fix |
|------|-------|-------|-----------------|
| ApiKeyManagementPanel.tsx | 311 | `bg-green-50 border-green-200` (success alert) | Add `dark:bg-green-950/30 dark:border-green-900/50` |
| ApiKeyManagementPanel.tsx | 318 | `bg-amber-50 border-amber-200` (warning alert) | Add `dark:bg-amber-950/30 dark:border-amber-900/50` |
| ApiKeyManagementPanel.tsx | 366 | `bg-green-50 text-green-800` (badge) | Add `dark:bg-green-950/30 dark:text-green-300` |
| ApiKeyManagementPanel.tsx | 370 | `bg-red-50 text-red-800` (badge) | Add `dark:bg-red-950/30 dark:text-red-300` |
| ApiKeyManagementPanel.tsx | 443 | `bg-red-50 border border-red-200` | Add `dark:bg-red-950/30 dark:border-red-900/50` |
| AssetOverrideModal.tsx | 88 | `bg-slate-100 border-variant text-foreground-secondary` | Add `dark:bg-slate-800` |
| AssetOverrideModal.tsx | 219 | `bg-slate-100 text-muted-foreground` | Add `dark:bg-slate-800` |
| ValidationChecklist.tsx | 22-25 | `bg-green-50`, `bg-red-50`, `bg-amber-50` | Add `dark:bg-*-950/30` variants |
| SystemHealthCard.tsx | 80 | `bg-green-50 border-green-200 text-green-900` | Add `dark:bg-green-950/30 dark:border-green-900/50 dark:text-green-300` |
| SystemHealthCard.tsx | 84 | `bg-red-50 border-red-200 text-red-900` | Add `dark:bg-red-950/30 dark:border-red-900/50 dark:text-red-300` |
| AdminDashboard.tsx | 391 | `bg-green-50 border border-green-200 text-green-800` | Add `dark:bg-green-950/30 dark:border-green-900/50 dark:text-green-300` |
| AdminDashboard.tsx | 400 | `bg-red-50 border-red-200 text-red-800` | Add `dark:bg-red-950/30 dark:border-red-900/50 dark:text-red-300` |

**Total Instances:** 18+

**Recommended Fix Template:**
```jsx
// Before
className="bg-green-50 border-green-200"

// After
className="bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900/50"

// For text colors
className="text-green-800"
// After
className="text-green-800 dark:text-green-300"
```

---

## Pattern 3: Text Color Contrast Issues - MEDIUM PRIORITY

### Summary
Light text colors on potentially light backgrounds without dark mode variants.

### Files with Issues

| File | Lines | Issue | Recommended Fix |
|------|-------|-------|-----------------|
| ApiKeyManagementPanel.tsx | 204 | `text-green-600` (bold heading) | Add `dark:text-green-400` |
| ApiKeyManagementPanel.tsx | 212 | `text-red-600` (bold heading) | Add `dark:text-red-400` |
| ApiKeyManagementPanel.tsx | 312 | `text-green-800` | Add `dark:text-green-300` |
| ApiKeyManagementPanel.tsx | 320 | `text-amber-800` | Add `dark:text-amber-300` |
| ApiKeyManagementPanel.tsx | 414 | `text-amber-600` | Add `dark:text-amber-400` |
| ApiKeyManagementPanel.tsx | 444, 447 | `text-red-800` | Add `dark:text-red-300` |
| ScreenAssetEditor.tsx | 462 | `bg-orange-700 hover:bg-orange-600 text-white` | Add `dark:bg-orange-800 dark:hover:bg-orange-700` |
| AssetForm.tsx | 681 | `bg-yellow-600 hover:bg-yellow-500 text-white` | Add `dark:bg-yellow-700 dark:hover:bg-yellow-600` |

**Total Instances:** 15+

---

## Pattern 4: White Background Containers - LOW-MEDIUM PRIORITY

### Summary
Explicit white backgrounds used for cards/containers that need dark mode equivalents.

### Files with Issues

| File | Lines | Issue | Recommended Fix |
|------|-------|-------|-----------------|
| admin/assets/[assetId]/page.tsx | 97 | `bg-white border-border` (empty state) | Add `dark:bg-slate-900` |
| admin/assets/[assetId]/page.tsx | 102 | `bg-slate-100 hover:bg-sky-600` | Add `dark:bg-slate-800 dark:hover:bg-sky-700` |
| admin/assets/[assetId]/page.tsx | 215 | `bg-white border-border` (form container) | Add `dark:bg-slate-900` |

**Total Instances:** 3

**Recommended Fix:**
```jsx
// Before
className="bg-white border-border"

// After
className="bg-white dark:bg-slate-900 border-border"
```

---

## Pattern 5: State-Based Colors Without Dark Variants - MEDIUM PRIORITY

### Summary
Loading, success, error states using specific colors that lack dark mode support.

### Files with Issues

| File | Lines | Issue | Recommended Fix |
|------|-------|-------|-----------------|
| SystemSettingsPanel.tsx | 188 | `bg-sky-400 text-white cursor-wait` (loading) | Add `dark:bg-sky-500` |
| SystemSettingsPanel.tsx | 190 | `bg-green-600 text-white` (success) | Add `dark:bg-green-700` |
| SystemSettingsPanel.tsx | 192 | `bg-red-600 text-white` (error) | Add `dark:bg-red-700` |

**Total Instances:** 3

---

## Pattern 6: Opacity-Based Accent Colors - LOW PRIORITY

### Summary
Colors with opacity modifiers that could benefit from dark mode adjustments for better contrast.

### Files with Issues

| File | Lines | Issue | Recommended Fix |
|------|-------|-------|-----------------|
| ReplanTimeline.tsx | 50, 56, 90 | `bg-red-500/10`, `bg-amber-500/10` | Consider adding `dark:bg-red-500/5` for better contrast |
| AssetOverrideModal.tsx | 78, 98, 218 | `bg-amber-500/10 border-amber-400/30` | Consider dark variants |
| InspectorStagePipeline.tsx | 42, 50, 377 | `bg-amber-500/10` and similar | Consider dark variants |

**Total Instances:** 10+

**Note:** These are already somewhat dark-mode friendly due to opacity, but explicit variants improve consistency.

---

## Pattern 7: Border Colors Without Variants - LOW PRIORITY

### Summary
Border colors in diff viewers and other components that need light mode support.

### Files with Issues

| File | Lines | Issue | Recommended Fix |
|------|-------|-------|-----------------|
| StageDiffView.tsx | 238 | `border-b-2 border-white` (loading spinner) | Add `dark:border-slate-400` |
| screen-editor/diff/DiffViewer.tsx | 19, 21, 23 | Multiple hardcoded borders | Add light mode variants |

**Total Instances:** 5+

---

## Implementation Priority

### Phase 1 (Critical - 23 instances)
Focus on primary button colors (`bg-sky-600`):
- All action buttons across admin UI
- Tab selection indicators
- Modal action buttons

**Estimated Impact:** Affects ~40% of UI interactions

### Phase 2 (High - 18 instances)
Light alert backgrounds (`bg-*-50`):
- Success/warning/error alerts
- Status badges
- Information cards

**Estimated Impact:** Affects ~25% of notification UI

### Phase 3 (Medium - 15+ instances)
Text color contrast:
- Headings and labels
- Status indicators
- Error messages

**Estimated Impact:** Affects ~20% of text readability

### Phase 4 (Low - 25+ instances)
Opacity states and borders:
- Accent colors with opacity
- Border colors in specialized views

**Estimated Impact:** Affects ~15% of specialized UI

---

## Global CSS Variables to Leverage

Current dark mode CSS variables available in `globals.css`:

```css
/* Dark Mode Colors (automatic @media (prefers-color-scheme: dark)) */
--background: 0 0% 100%         /* Light: white */
--foreground: 210 40% 96%        /* Dark: near white */
--primary: 210 100% 50%          /* Sky-500 */
--primary-foreground: 0 0% 100%  /* White */
--secondary: 220 13% 91%         /* Light gray */
--muted-foreground: 215 17% 51%  /* Gray */
--surface-overlay: 217 22% 9%    /* Dark blue-gray */
--border-muted: 217 17% 23%      /* Muted border */
```

**Recommendation:** Create component-specific dark mode variables instead of hardcoding:

```css
/* Add to globals.css */
:root {
  --button-primary-dark: 210 120% 55%;      /* sky-700 */
  --alert-success-bg-dark: rgb(4, 120, 87 / 0.3);
  --alert-warning-bg-dark: rgb(124, 45, 18 / 0.3);
  --alert-error-bg-dark: rgb(127, 29, 29 / 0.3);
}

@media (prefers-color-scheme: dark) {
  :root {
    --button-primary: var(--button-primary-dark);
  }
}
```

---

## Recommended Implementation Approach

### Option A: Direct dark: Prefix (Recommended)
```jsx
className="bg-sky-600 dark:bg-sky-700 hover:bg-sky-700 dark:hover:bg-sky-600"
```
**Pros:** Clear, explicit, no extra CSS
**Cons:** Longer class strings

### Option B: CSS Component Classes
```css
/* globals.css */
@layer components {
  .btn-primary {
    @apply bg-sky-600 hover:bg-sky-700 dark:bg-sky-700 dark:hover:bg-sky-600;
  }
}
```

```jsx
className="btn-primary text-white"
```
**Pros:** Reusable, maintainable, consistent
**Cons:** Requires CSS definition

### Option C: Tailwind Config Extension
```js
// tailwind.config.ts
module.exports = {
  theme: {
    extend: {
      colors: {
        'sky-dark': {
          600: 'light-mode-color',
          700: 'dark-mode-color',
        }
      }
    }
  }
}
```
**Pros:** Semantic naming
**Cons:** Requires build config change

**Recommendation:** Use **Option B** for high-reuse components (buttons, alerts) and **Option A** for one-off instances.

---

## Quick Reference: Dark Mode Color Mappings

| Light Color | Dark Equivalent | Use Case |
|-------------|-----------------|----------|
| `bg-sky-600` | `dark:bg-sky-700` | Primary buttons |
| `bg-green-50` | `dark:bg-green-950/30` | Success alerts |
| `bg-amber-50` | `dark:bg-amber-950/30` | Warning alerts |
| `bg-red-50` | `dark:bg-red-950/30` | Error alerts |
| `bg-white` | `dark:bg-slate-900` | Cards/containers |
| `bg-slate-100` | `dark:bg-slate-800` | Secondary containers |
| `text-green-800` | `dark:text-green-300` | Status text |
| `text-red-800` | `dark:text-red-300` | Error text |
| `text-amber-800` | `dark:text-amber-300` | Warning text |
| `border-green-200` | `dark:border-green-900/50` | Status borders |

---

## Testing Checklist

After implementing dark mode variants:

- [ ] Test all primary buttons in light mode
- [ ] Test all primary buttons in dark mode
- [ ] Verify alert boxes display correctly in both modes
- [ ] Check text contrast meets WCAG AA standards (4.5:1)
- [ ] Test on actual dark mode device/system settings
- [ ] Verify no color bleeds in opacity-based components
- [ ] Check skeleton loaders in both modes
- [ ] Test tab selection indicators
- [ ] Verify diff viewers display correctly
- [ ] Check status badges (success/warning/error)

---

## Files Summary by Issue Count

| File | Issue Count | Severity |
|------|-------------|----------|
| admin/explorer/page.tsx | 11 | Critical |
| ActionTab.tsx | 7 | Critical |
| ApiKeyManagementPanel.tsx | 9 | High |
| admin/settings/page.tsx | 4 | Critical |
| admin/logs/page.tsx | 4 | Critical |
| admin/assets/[assetId]/page.tsx | 3 | Medium |
| SystemSettingsPanel.tsx | 3 | Critical |
| AssetForm.tsx | 2 | Critical |
| StageDiffView.tsx | 2 | Critical |
| ScreenEditorHeader.tsx | 2 | Critical |
| ConversationSummaryModal.tsx | 1 | Critical |
| Others | 30+ | Mixed |

---

## Next Steps

1. **Review Priority Phases** - Determine which phase to implement first
2. **Create CSS Component Classes** - Build reusable button/alert classes
3. **Batch Update Files by Phase** - Update systematically by priority
4. **Add Dark Mode Testing** - Create test scenarios
5. **Deploy and Monitor** - Ensure no regression in light mode

---

**Document Location:** `/home/spa/tobit-spa-ai/DARK_MODE_ANALYSIS.md`

# Dark Mode Fixes - Real Code Examples

## Example 1: Admin Explorer Page (11 instances)

File: `/apps/web/src/app/admin/explorer/page.tsx`

**Before (Line 607):**
```jsx
className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${selectedCatalog === catalog.id ? "bg-sky-600 text-white border-sky-600" : "border-border"}`}
```

**After:**
```jsx
className={`px-4 py-2 rounded-lg font-medium text-sm transition-all ${selectedCatalog === catalog.id ? "bg-sky-600 dark:bg-sky-700 text-white border-sky-600 dark:border-sky-700" : "border-border"}`}
```

---

## Example 2: Action Tab Component (7 instances)

File: `/apps/web/src/components/admin/screen-editor/actions/ActionTab.tsx`

**Before (Line 183):**
```jsx
className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
  activeTab === 'triggerSource' 
    ? "bg-sky-600 text-white" 
    : "text-muted-foreground hover:bg-muted"
}`}
```

**After:**
```jsx
className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
  activeTab === 'triggerSource' 
    ? "bg-sky-600 dark:bg-sky-700 text-white hover:bg-sky-700 dark:hover:bg-sky-600" 
    : "text-muted-foreground hover:bg-muted"
}`}
```

---

## Example 3: API Key Management (Alert Backgrounds)

File: `/apps/web/src/components/admin/ApiKeyManagementPanel.tsx`

**Before (Line 311):**
```jsx
<Alert className="mb-4 bg-green-50 border-green-200">
  <AlertTitle className="text-green-900">Success!</AlertTitle>
  <AlertDescription className="text-green-800">{success}</AlertDescription>
</Alert>
```

**After:**
```jsx
<Alert className="mb-4 bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-900/50">
  <AlertTitle className="text-green-900 dark:text-green-300">Success!</AlertTitle>
  <AlertDescription className="text-green-800 dark:text-green-300">{success}</AlertDescription>
</Alert>
```

---

## Example 4: Text Color (Status Indicator)

File: `/apps/web/src/components/admin/ApiKeyManagementPanel.tsx`

**Before (Line 204):**
```jsx
<p className="text-3xl font-bold text-green-600">{activeKeysCount}</p>
```

**After:**
```jsx
<p className="text-3xl font-bold text-green-600 dark:text-green-400">{activeKeysCount}</p>
```

---

## Example 5: Primary Button with Hover State

File: `/apps/web/src/components/admin/AssetForm.tsx`

**Before (Line 623):**
```jsx
<button
  type="submit"
  className="px-6 py-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white rounded-lg transition-colors font-medium shadow-lg shadow-sky-900/20"
>
  Save Asset
</button>
```

**After:**
```jsx
<button
  type="submit"
  className="px-6 py-2 bg-sky-600 hover:bg-sky-700 dark:bg-sky-700 dark:hover:bg-sky-600 disabled:opacity-50 text-white rounded-lg transition-colors font-medium shadow-lg shadow-sky-900/20 dark:shadow-sky-900/40"
>
  Save Asset
</button>
```

---

## Example 6: Loading State with Multiple Colors

File: `/apps/web/src/components/admin/SystemSettingsPanel.tsx`

**Before (Lines 188-193):**
```jsx
className={
  isLoading
    ? 'bg-sky-400 text-white cursor-wait'
    : isSaved
    ? 'bg-green-600 text-white'
    : isError
    ? 'bg-red-600 text-white'
    : 'bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50 disabled:cursor-not-allowed'
}
```

**After:**
```jsx
className={
  isLoading
    ? 'bg-sky-400 dark:bg-sky-500 text-white cursor-wait'
    : isSaved
    ? 'bg-green-600 dark:bg-green-700 text-white'
    : isError
    ? 'bg-red-600 dark:bg-red-700 text-white'
    : 'bg-sky-600 dark:bg-sky-700 text-white hover:bg-sky-700 dark:hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed'
}
```

---

## Using CSS Component Classes (Recommended Approach)

Instead of repeating dark: variants everywhere, create reusable classes in globals.css:

**Add to globals.css:**
```css
@layer components {
  /* Primary Button */
  .btn-primary {
    @apply bg-sky-600 hover:bg-sky-700 dark:bg-sky-700 dark:hover:bg-sky-600 
           text-white font-medium rounded-lg transition-colors;
  }

  /* Button with loading state */
  .btn-loading {
    @apply bg-sky-400 dark:bg-sky-500 cursor-wait;
  }

  .btn-success {
    @apply bg-green-600 dark:bg-green-700 hover:bg-green-700 dark:hover:bg-green-600;
  }

  .btn-error {
    @apply bg-red-600 dark:bg-red-700 hover:bg-red-700 dark:hover:bg-red-600;
  }

  /* Alert Boxes */
  .alert-success {
    @apply bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-900/50;
  }

  .alert-warning {
    @apply bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50;
  }

  .alert-error {
    @apply bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-900/50;
  }

  /* Alert Text */
  .alert-success-text {
    @apply text-green-900 dark:text-green-300;
  }

  .alert-error-text {
    @apply text-red-900 dark:text-red-300;
  }

  .alert-warning-text {
    @apply text-amber-900 dark:text-amber-300;
  }
}
```

**Then use in components:**
```jsx
// Button example
<button className="btn-primary px-6 py-2">Save</button>

// Alert example
<div className="alert-success">
  <p className="alert-success-text">Success message</p>
</div>

// Loading state
<button className={`btn-primary ${isLoading ? 'btn-loading' : ''}`}>
  {isLoading ? 'Loading...' : 'Submit'}
</button>
```

Benefits:
- DRY principle (no repetition)
- Easy to maintain (change in one place)
- Consistent styling across the app
- Easier to read component code

