# Hardcoded Chart Colors - Action Checklist

Quick reference for implementing the fixes.

## Pre-Implementation
- [ ] Review `/docs/HARDCODED_CHART_COLORS_ANALYSIS.md` for overview
- [ ] Review `/docs/HARDCODED_COLORS_DETAILED_FINDINGS.md` for technical details
- [ ] Create feature branch: `git checkout -b refactor/standardize-chart-colors`

---

## Phase 1: CSS Variables (globals.css)

### File: `/apps/web/src/app/globals.css`

**Action 1a: Add RGB variable to Dark Mode section**
- Navigate to line 131 (after `--chart-accent-pink: #f472b6;`)
- Add new line:
  ```css
  --chart-text-color-rgb: 148, 163, 184; /* slate-400 RGB for rgba() */
  ```
- ✅ Save file

**Action 1b: Add RGB variable to Light Mode section**
- Navigate to line 160 (after `--chart-accent-pink: #ec4899;`)
- Add new line:
  ```css
  --chart-text-color-rgb: 100, 116, 139; /* slate-500 RGB for rgba() */
  ```
- ✅ Save file

**Status after Phase 1**:
- [ ] Dark mode RGB variable added (line ~132)
- [ ] Light mode RGB variable added (line ~161)
- [ ] No syntax errors
- [ ] File saved

---

## Phase 2: Update AssetImpactAnalyzer

### File: `/apps/web/src/components/admin/AssetImpactAnalyzer.tsx`

**Action 2a: Replace hardcoded color at line 69**
- Current: `low: "#10b981", // green`
- Replace with: `low: "var(--chart-success-color)", // green (emerald-500 light, emerald-400 dark)`

**Action 2b: Replace hardcoded color at line 70**
- Current: `medium: "#f59e0b", // amber`
- Replace with: `medium: "var(--chart-warning-color)", // amber (amber-500 light, amber-400 dark)`

**Action 2c: Replace hardcoded color at line 71**
- Current: `high: "#ef4444", // red`
- Replace with: `high: "var(--chart-error-color)", // red (red-500 light, red-400 dark)`

**Status after Phase 2**:
- [ ] Line 69 updated
- [ ] Line 70 updated
- [ ] Line 71 updated
- [ ] No syntax errors
- [ ] File saved

---

## Phase 3: Update ObservabilityDashboard

### File: `/apps/web/src/components/admin/ObservabilityDashboard.tsx`

**Action 3: Replace hardcoded RGBA at line 210**

**Current code (line ~209-211):**
```javascript
cursor={{ fill: "rgba(148, 163, 184, 0.1)" }}
```

**Replace with:**
```javascript
cursor={{ fill: `rgba(var(--chart-text-color-rgb), 0.1)` }}
```

**Important**: Use backticks (`) not quotes ("")

**Status after Phase 3**:
- [ ] Line 210 updated
- [ ] Using backticks for template literal
- [ ] No syntax errors
- [ ] File saved

---

## Phase 4: Update ExecutionTimeline

### File: `/apps/web/src/components/admin/observability/ExecutionTimeline.tsx`

**Action 4: Replace hardcoded RGBA at line 130**

**Current code (line ~129-131):**
```javascript
cursor={{ stroke: "rgba(148, 163, 184, 0.2)" }}
```

**Replace with:**
```javascript
cursor={{ stroke: `rgba(var(--chart-text-color-rgb), 0.2)` }}
```

**Important**: Use backticks (`) not quotes ("")

**Status after Phase 4**:
- [ ] Line 130 updated
- [ ] Using backticks for template literal
- [ ] No syntax errors
- [ ] File saved

---

## Verification Steps

### Step 1: Code Review
- [ ] All files saved with no syntax errors
- [ ] No console warnings
- [ ] No TypeScript errors (if using strict mode)

### Step 2: Visual Testing - Dark Mode
1. Open app in browser
2. Ensure dark mode is enabled (System or Settings)
3. Navigate to AssetImpactAnalyzer component
   - [ ] Impact colors show as: low (darker green), medium (darker amber), high (darker red)
4. Navigate to ObservabilityDashboard
   - [ ] Cursor fill shows proper dark theme color (10% opacity)
5. Navigate to ExecutionTimeline (inside Observability)
   - [ ] Cursor stroke shows proper dark theme color (20% opacity)

### Step 3: Visual Testing - Light Mode
1. Switch to light mode (if dark was tested)
2. Navigate to AssetImpactAnalyzer component
   - [ ] Impact colors show as: low (brighter green), medium (brighter amber), high (brighter red)
3. Navigate to ObservabilityDashboard
   - [ ] Cursor fill shows proper light theme color (10% opacity)
4. Navigate to ExecutionTimeline
   - [ ] Cursor stroke shows proper light theme color (20% opacity)

### Step 4: Compare Before/After
- [ ] Chart colors are noticeably different between dark and light modes
- [ ] No flickering or color changes during theme transition
- [ ] All chart interactions work normally

### Step 5: Build & Production Check
```bash
# Run in project root
npm run build
npm run start
```
- [ ] No build errors
- [ ] App runs without errors
- [ ] No console warnings about CSS variables

---

## Commit Instructions

### After all phases complete:

```bash
# Stage all changes
git add apps/web/src/app/globals.css \
         apps/web/src/components/admin/AssetImpactAnalyzer.tsx \
         apps/web/src/components/admin/ObservabilityDashboard.tsx \
         apps/web/src/components/admin/observability/ExecutionTimeline.tsx

# Create commit
git commit -m "refactor: Standardize hardcoded chart colors to CSS variables

- Replace 3 hex colors in AssetImpactAnalyzer with semantic variables
- Add --chart-text-color-rgb for RGBA calculations in tooltips
- Update ObservabilityDashboard cursor fill to use CSS variable
- Update ExecutionTimeline cursor stroke to use CSS variable

Benefits:
- Automatic dark/light mode support
- Consistent with design system
- Single source of truth for colors
- Improved maintainability

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"

# Verify commit
git log -1 --stat
```

---

## Rollback Plan (if needed)

If anything goes wrong:

```bash
# Undo all changes
git reset --hard HEAD

# Or selectively revert specific file
git checkout HEAD -- apps/web/src/app/globals.css
git checkout HEAD -- apps/web/src/components/admin/AssetImpactAnalyzer.tsx
```

---

## Post-Implementation

- [ ] Update project memory if needed
- [ ] Mark phase as complete in MEMORY.md
- [ ] Create PR with link to documentation
- [ ] Request code review
- [ ] Merge to main after approval

---

## Troubleshooting

### Issue: Colors not changing on theme switch
- **Cause**: CSS variable fallback to hardcoded value
- **Fix**: Ensure globals.css variables are loaded before component code
- **Check**: Run `npm run build` to verify no errors

### Issue: RGBA variables showing as text
- **Cause**: Using quotes instead of backticks
- **Fix**: Change line 210 and 130 to use backticks:
  - `cursor={{ fill: \`rgba(var(...), 0.1)\` }}`
  - NOT: `cursor={{ fill: "rgba(var(...), 0.1)" }}`

### Issue: No visual difference between modes
- **Cause**: Theme toggle not working or CSS not loaded
- **Fix**: 
  1. Clear browser cache (Ctrl+Shift+Delete)
  2. Hard refresh (Ctrl+Shift+R)
  3. Check Network tab for globals.css loading

---

## Time Estimates

| Phase | Task | Time |
|-------|------|------|
| 1 | Update globals.css | 2 min |
| 2 | Update AssetImpactAnalyzer | 2 min |
| 3 | Update ObservabilityDashboard | 1 min |
| 4 | Update ExecutionTimeline | 1 min |
| 5 | Testing (all modes) | 5 min |
| 6 | Commit & cleanup | 2 min |
| **Total** | | **13 min** |

---

## Success Criteria

- [ ] All 4 files updated
- [ ] No syntax errors in any file
- [ ] Colors adapt to dark/light mode
- [ ] No console errors or warnings
- [ ] Commit created and pushed
- [ ] All tests pass
- [ ] Code review approved

