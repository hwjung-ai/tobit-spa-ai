# OPS Document Mode - Viewer Navigation Fix

**Date**: 2026-02-09
**Issue**: OPS 문서 모드에서 reference 클릭 시 viewer가 열리지 않음

## Problem Analysis

### 🔴 Before Fix

1. **Backend Issue**: `document_id` validation 부재
   - `document_id = getattr(result, 'document_id', '')` (기본값: 빈 문자열)
   - Invalid URL: `/documents//viewer` (document_id 누락)
   - Reference가 렌더링되지 않거나 broken link 생성

2. **Frontend Issue**: PDF 렌더링 느림
   - 100ms 고정 딜레이로 느린 PDF 렌더링 미대응
   - Highlighting 실패 또는 지연

## ✅ Solution Implemented

### 1. Backend Fix (OPS Document Mode)

**File**: `apps/api/app/modules/ops/services/__init__.py:312-350`

```python
# Before
document_id = getattr(result, 'document_id', '')  # ❌ Can be empty string

# After
document_id = getattr(result, 'document_id', None)

# Skip references without document_id
if not document_id:
    logger.warning(f"Skipping reference #{i}: missing document_id. chunk_id={chunk_id}")
    continue

# Build viewer URL only for valid references
viewer_url = f"/documents/{document_id}/viewer"
```

**Changes**:
- ✅ Default changed from `''` to `None` for type safety
- ✅ Explicit validation before URL construction
- ✅ Logging for debugging missing document_id
- ✅ Fixed `page is not None` check (was `page` which excludes page 0)

### 2. Frontend Fix (Document Viewer Highlighting)

**File**: `apps/web/src/app/documents/[documentId]/viewer/page.tsx:186-217`

```typescript
// Before
const timeout = window.setTimeout(() => {
  highlightSnippet();
}, 100);  // ❌ Fixed 100ms may not be enough

// After
const attemptHighlight = () => {
  const textLayer = document.querySelector(
    `.react-pdf__Page[data-page-number="${currentPage}"] .react-pdf__Page__textContent`
  );
  if (textLayer) {
    highlightSnippet();
    return true;
  }
  if (retries < maxRetries) {
    retries += 1;
    const delay = Math.min(100 * Math.pow(1.5, retries), 1000);  // ✅ Exponential backoff
    window.setTimeout(attemptHighlight, delay);
  }
  return false;
};

const timeout = window.setTimeout(attemptHighlight, 100);
```

**Changes**:
- ✅ Exponential backoff: 100ms → 150ms → 225ms → 337ms → 506ms → 759ms
- ✅ Maximum 5 retries with soft cap at 1000ms
- ✅ Checks for text layer existence before attempting highlight
- ✅ Added `currentPage` to dependency array

## 📊 Expected Behavior

### OPS Document Mode → Reference Click → Viewer Open → Highlighting

1. **Query in OPS "문서" mode**
   ```
   질문: "시스템의 주요 기능은?"
   ```

2. **Results with References**
   ```
   Answer: "시스템은 다음 기능을 제공합니다..."

   Source Documents (근거 문서)
   ├─ 1. System Design (p.3) ← Click this
   ├─ 2. Architecture Guide (p.7)
   └─ 3. Installation Manual (p.2)
   ```

3. **After Click**
   - ✅ Navigate to `/documents/{docId}/viewer?chunkId={chunkId}&page={page}`
   - ✅ PDF loads
   - ✅ Relevant text highlighted with exponential backoff
   - ✅ Page auto-scrolls to highlighted content

## 🧪 Test Checklist

- [ ] Start `make dev`
- [ ] Navigate to OPS page
- [ ] Select "문서" (document) mode
- [ ] Enter a question (e.g., "시스템 설명")
- [ ] Wait for results
- [ ] Click on a reference card
- [ ] Verify:
  - [ ] URL changed to `/documents/{id}/viewer?chunkId=...&page=...`
  - [ ] PDF loads
  - [ ] Relevant text highlighted in PDF
  - [ ] Page auto-scrolls to highlight

## 🔍 Debugging

### If reference doesn't render

1. **Check backend logs**:
   ```
   grep "Skipping reference" <api-logs>
   ```
   → If found, `document_id` is missing from search results

2. **Check database**:
   ```sql
   SELECT document_id, chunk_id, page_number
   FROM document_chunks
   LIMIT 5;
   ```
   → Verify `document_id` is populated

### If highlighting doesn't work

1. **Check browser console**:
   - Look for fetch errors in network tab
   - Check if `/documents/{id}/chunks/{chunkId}` returns data

2. **Check PDF layer rendering**:
   - Open DevTools → Inspector
   - Search for `.react-pdf__Page__textContent`
   - If not found, PDF is still rendering (normal with large docs)

## Technical Details

### Reference URL Format

Generated in backend:
```python
# Example
viewer_url = "/documents/abc-123-def/viewer?chunkId=chunk-456&page=3"
```

Rendered in frontend:
```typescript
// BlockRenderer.tsx:620-629
<Link href="/documents/abc-123-def/viewer?chunkId=chunk-456&page=3">
  {cardContent}
</Link>
```

### Highlighting Flow

1. Viewer loads document metadata
2. Fetch chunk info if `chunkId` present (line 163-179)
3. Derived page from chunk or URL param (line 77)
4. When both ready, start highlighting with retries (line 186+)
5. Retry every 100-1000ms until text layer found
6. Scroll highlighted text into view (line 131)

## Commits

- `5793d6a`: fix: Improve document reference viewer navigation and highlighting

## Files Changed

- ✅ `apps/api/app/modules/ops/services/__init__.py` (13 lines)
- ✅ `apps/web/src/app/documents/[documentId]/viewer/page.tsx` (27 lines)

## Related Issues

- OPS 문서 모드에서 reference 클릭 시 viewer 열림
- Document 페이지에서 reference 클릭 시 viewer 열림 (이미 정상)
