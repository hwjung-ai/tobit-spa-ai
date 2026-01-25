# Data → Admin 통합 설계서

**작성일**: 2026-01-25
**버전**: v1.0
**상태**: 설계 완료, 구현 대기

---

## 1. 현재 구조 분석

### 1.1 메인 메뉴 구조

```
┌─────────────────────────────────────────────────────────────────┐
│  ADMIN (/admin)                                                 │
├─────────────────────────────────────────────────────────────────┤
│  [Assets] [Screens] [Settings] [Inspector] [Regression] [Observability]
│                                                                 │
│  • Assets: 8가지 타입 CRUD (prompt, mapping, policy, query,    │
│            screen, source, schema, resolver)                    │
│  • Screens: screen asset 전용 visual editor                     │
│  • Settings: 시스템 설정                                        │
│  • Inspector: Trace 검사                                        │
│  • Regression: 회귀 테스트                                      │
│  • Observability: 모니터링/RCA                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  DATA (/data)                                                   │
├─────────────────────────────────────────────────────────────────┤
│  [Explorer] [Source] [Catalog] [Resolvers]                      │
│                                                                 │
│  • Explorer: PostgreSQL, Neo4j, Redis 쿼리 인터페이스           │
│  • Source: source asset CRUD + Connection Test                  │
│  • Catalog: schema asset CRUD + Schema Scan                     │
│  • Resolvers: resolver asset CRUD + Simulation                  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 현재 문제점

| 문제 | 설명 | 영향 |
|------|------|------|
| **중복 진입점** | source/schema/resolver가 Admin Assets에도, Data에도 존재 | 사용자 혼란, 유지보수 어려움 |
| **불완전한 연동** | AssetForm.tsx:280-308에서 "Data 메뉴에서 편집하세요" 링크로 우회 | 사용자 경험 저하 |
| **생성 불가** | CreateAssetModal.tsx:87에서 source/schema/resolver 생성 미지원 | 일관성 저하 |
| **동일 API 사용** | Data 모듈이 `/asset-registry/*` API 사용 → Asset Registry와 완전히 중복 | 코드 중복 |

---

## 2. 통합 후 구조

### 2.1 메인 메뉴 (통합 후)

```
┌─────────────────────────────────────────────────────────────────┐
│  ADMIN (/admin)                                                 │
├─────────────────────────────────────────────────────────────────┤
│  [Assets] [Screens] [Explorer] [Settings] [Inspector] [Regression] [Observability]
│                                                                 │
│  • Assets: 8가지 타입 통합 관리 (type별 전용 UI 포함)            │
│  • Screens: screen asset 전용 visual editor (유지)              │
│  • Explorer: 데이터 쿼리 도구 (신규 - Data Explorer 이동)        │
│  • Settings: 시스템 설정 (유지)                                 │
│  • Inspector: Trace 검사 (유지)                                 │
│  • Regression: 회귀 테스트 (유지)                               │
│  • Observability: 모니터링/RCA (유지)                           │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  DATA (/data) → 삭제                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Assets 탭 강화

```
/admin/assets
├── type=all (기본값)
├── type=prompt      → 기존 폼 유지
├── type=mapping     → 기존 폼 유지
├── type=policy      → 기존 폼 유지
├── type=query       → 기존 폼 유지
├── type=screen      → 기존 폼 + Screen Editor 링크
├── type=source      → 전용 폼 (Connection 설정 + Test 버튼)  ← 신규
├── type=schema      → 전용 폼 (Source 참조 + Scan 버튼)     ← 신규
└── type=resolver    → 전용 폼 (Rule Editor + Simulate)      ← 신규
```

---

## 3. 파일별 변경 계획

### 3.1 삭제할 파일

| 파일 | 이유 |
|------|------|
| `apps/web/src/app/data/layout.tsx` | Data 레이아웃 삭제 |
| `apps/web/src/app/data/sources/page.tsx` | Assets에 통합 |
| `apps/web/src/app/data/catalog/page.tsx` | Assets에 통합 |
| `apps/web/src/app/data/resolvers/page.tsx` | Assets에 통합 |
| `apps/web/src/components/data/DataNavigation.tsx` | 네비게이션 삭제 |

### 3.2 이동할 파일

| 원본 | 목적지 | 설명 |
|------|--------|------|
| `apps/web/src/app/data/page.tsx` | `apps/web/src/app/admin/explorer/page.tsx` | Data Explorer 이동 |
| `apps/web/src/components/data/Neo4jGraphFlow.tsx` | `apps/web/src/components/admin/Neo4jGraphFlow.tsx` | 그래프 컴포넌트 이동 |

### 3.3 수정할 파일

| 파일 | 변경 내용 |
|------|-----------|
| `apps/web/src/app/admin/layout.tsx` | Explorer 탭 추가 |
| `apps/web/src/components/admin/AssetForm.tsx` | source/schema/resolver 전용 폼 추가, Data 링크 제거 |
| `apps/web/src/components/admin/CreateAssetModal.tsx` | source/schema/resolver 생성 지원 |
| `apps/web/src/components/admin/AssetTable.tsx` | type별 액션 버튼 (Test, Scan, Simulate) 추가 |

### 3.4 신규 생성할 파일

| 파일 | 설명 |
|------|------|
| `apps/web/src/app/admin/explorer/page.tsx` | Data Explorer 페이지 |
| `apps/web/src/components/admin/SourceAssetForm.tsx` | Source 전용 폼 (Connection + Test) |
| `apps/web/src/components/admin/SchemaAssetForm.tsx` | Schema 전용 폼 (Scan 기능) |
| `apps/web/src/components/admin/ResolverAssetForm.tsx` | Resolver 전용 폼 (Rule Editor + Simulate) |

---

## 4. 상세 변경 사항

### 4.1 Admin Layout 변경

**파일**: `apps/web/src/app/admin/layout.tsx`

```typescript
// Before
const tabs = [
    { label: "Assets", href: "/admin/assets" },
    { label: "Screens", href: "/admin/screens" },
    { label: "Settings", href: "/admin/settings" },
    { label: "Inspector", href: "/admin/inspector" },
    { label: "Regression", href: "/admin/regression" },
    { label: "Observability", href: "/admin/observability" },
];

// After
const tabs = [
    { label: "Assets", href: "/admin/assets" },
    { label: "Screens", href: "/admin/screens" },
    { label: "Explorer", href: "/admin/explorer" },  // 신규
    { label: "Settings", href: "/admin/settings" },
    { label: "Inspector", href: "/admin/inspector" },
    { label: "Regression", href: "/admin/regression" },
    { label: "Observability", href: "/admin/observability" },
];
```

### 4.2 CreateAssetModal 변경

**파일**: `apps/web/src/components/admin/CreateAssetModal.tsx`

```typescript
// Before (line 87)
{(["prompt", "mapping", "policy", "query", "screen"] as const).map((type) => ...)}

// After
{(["prompt", "mapping", "policy", "query", "screen", "source", "schema", "resolver"] as const).map((type) => ...)}
```

### 4.3 AssetForm 변경

**파일**: `apps/web/src/components/admin/AssetForm.tsx`

```typescript
// Before (line 280-308): Data 링크로 우회
{["source", "schema", "resolver"].includes(asset.asset_type) && (
    <div>
        <p>이 타입은 Data 메뉴에서 편집하세요.</p>
        <Link href={`/data/sources?asset_id=${asset.asset_id}`}>...</Link>
    </div>
)}

// After: 타입별 전용 폼 컴포넌트 렌더링
{asset.asset_type === "source" && <SourceAssetForm asset={asset} onSave={onSave} />}
{asset.asset_type === "schema" && <SchemaAssetForm asset={asset} onSave={onSave} />}
{asset.asset_type === "resolver" && <ResolverAssetForm asset={asset} onSave={onSave} />}
```

---

## 5. 라우팅 변경 요약

| Before | After | 비고 |
|--------|-------|------|
| `/data` | `/admin/explorer` | Data Explorer 이동 |
| `/data/sources` | `/admin/assets?type=source` | Assets에 통합 |
| `/data/sources?asset_id=xxx` | `/admin/assets/xxx` | 개별 asset 페이지 |
| `/data/catalog` | `/admin/assets?type=schema` | Assets에 통합 |
| `/data/catalog?asset_id=xxx` | `/admin/assets/xxx` | 개별 asset 페이지 |
| `/data/resolvers` | `/admin/assets?type=resolver` | Assets에 통합 |
| `/data/resolvers?asset_id=xxx` | `/admin/assets/xxx` | 개별 asset 페이지 |

---

## 6. 구현 단계

### Phase 1: 기반 작업
- [ ] Explorer 탭 추가 (`/admin/explorer`)
- [ ] Data Explorer 페이지 이동
- [ ] Neo4jGraphFlow 컴포넌트 이동

### Phase 2: Asset 폼 통합
- [ ] SourceAssetForm 컴포넌트 생성
- [ ] SchemaAssetForm 컴포넌트 생성
- [ ] ResolverAssetForm 컴포넌트 생성
- [ ] AssetForm에서 타입별 폼 연동
- [ ] CreateAssetModal에 source/schema/resolver 추가

### Phase 3: 정리
- [ ] Data 모듈 파일 삭제
- [ ] 기존 Data 경로 → Admin 리다이렉트 설정 (선택)

---

## 7. 기존 탭 영향도

| 탭 | 변경 | 영향도 |
|-----|------|--------|
| Assets | type별 전용 폼 추가 | High |
| Screens | 변경 없음 | None |
| Explorer | 신규 추가 | New |
| Settings | 변경 없음 | None |
| Inspector | 변경 없음 | None |
| Regression | 변경 없음 | None |
| Observability | 변경 없음 | None |

---

## 8. 백업 및 롤백 계획

### 백업
```bash
# 통합 전 백업
git checkout -b backup/before-admin-data-integration
git push origin backup/before-admin-data-integration

# 통합 브랜치 생성
git checkout -b feature/admin-data-integration
```

### 롤백 계획
- **문제 발생 시**: `backup/before-admin-data-integration` 브랜치로 롤백
- **테스트 필요 시**: Data 모듈 유지하고 Admin에만 새 기능 추가 (병행 운영)

---

## 9. 리스크 및 완화책

| 리스크 | 확률 | 영향 | 완화책 |
|--------|------|------|--------|
| 기존 URL 호환성 문제 | 중간 | 높음 | 리다이렉트 설정, 사용자 안내 |
| 전용 폼 개발 시간 예상 초과 | 낮음 | 중간 | 기존 Data 폼 재사용, 점진적 이전 |
| 사용자 혼란 (URL 변경) | 중간 | 중간 | Migration Guide, in-app 알림 |

---

**문서 작성 완료**: 2026-01-25
**다음 단계**: Phase 1 구현 시작