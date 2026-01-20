# Screen Demo Runbook

이 문서에서는 **S3-4: 운영 시나리오 고정** 조건에 맞춰, Admin 화면 생성부터 UI 렌더 + Regression/Inspector 확인까지 1회전 데모를 재현하는 절차를 정리합니다.

## 사전 조건
- `make dev`로 프론트/백엔드 실행 후 `http://localhost:3000` 접속.
- 로그인 및 권한은 `apps/web/src/app/layout.tsx` 기반 인증을 따릅니다.
- Screen 에셋은 `/asset-registry`가 소스이며, Admin > Screens에서 관리합니다 (`apps/web/src/app/admin/screens/page.tsx:1-17` & `apps/web/src/components/admin/ScreenAssetPanel.tsx:1-135`).

## 1. Admin > Screen 생성/편집
1. `/admin/screens`로 이동하면 `ScreenAssetPanel`이 로딩되며, `+ Create Screen` 버튼으로 템플릿을 선택해서 새 `screen_id`, 이름, description, tags 등을 입력하고 저장 버튼을 눌러 생성합니다 (`apps/web/src/components/admin/ScreenAssetPanel.tsx:18-143`).
2. 새 에셋은 목록에 나타나며, 클릭 시 `/admin/screens/[assetId]/editor`(ScreenEditor)로 이동합니다 (`apps/web/src/components/admin/screen-editor/ScreenEditor.tsx:160-215`).
3. ScreenEditor 헤더 상단에서 로컬 상태는 `status`, `isDirty` 등을 표시하고, Save/Pubish/Rollback 버튼을 통해 draft/publish 상태를 관리합니다 (`ScreenEditorHeader.tsx:25-190`).

## 2. Publish
1. ScreenEditor에서 `Publish` 버튼(`data-testid="btn-publish-screen"`)을 클릭하면 `PublishGateModal`이 뜹니다 (`ScreenEditor.tsx:198-215`).
2. Publish 승인을 하면 `editorState.publish()`가 호출되어 `asset-registry`에 Schema가 정상 저장됩니다. 성공 시 상단 배너가 나타나고 Regression/Inspector CTA가 활성화됩니다 (`ScreenEditorHeader.tsx:134-205`).

## 3. UI 목록 노출
1. `/ui/screens` 페이지에서는 `PublishedScreensList`가 published Screen만 가져와서 표시합니다 (`apps/web/src/components/ui/screens/PublishedScreensList.tsx:1-68`).
2. 각 카드의 제목, version, published_at/updated_at 정보가 렌더되며 클릭하면 `/ui/screens/{asset_id}`로 이동합니다 (`PublishedScreensList.tsx:69-110`).

## 4. 클릭시 렌더
1. `/ui/screens/[screenId]` 페이지(`apps/web/src/app/ui/screens/[screenId]/page.tsx:1-18`)는 `PublishedScreenDetail`을 사용하여 `asset-registry/assets/{screenId}?stage=published`에서 schema를 가져오고 `UIScreenRenderer`에서 렌더합니다 (`apps/web/src/components/ui/screens/PublishedScreenDetail.tsx:1-102`).
2. 로딩/오류 메시지, screen 메타데이터(타이틀, 설명, 태그)를 통해 published 화면을 확인할 수 있습니다 (`PublishedScreenDetail.tsx:21-102`).

## 5. Regression/Inspector 증거 확인
1. ScreenEditor 헤더에 `Run Regression`/`Open Inspector` 버튼(`ScreenEditorHeader.tsx:144-190`)이 있으며, published screen만 활성화됩니다.
2. 눌렀을 때 `/admin/regression` 또는 `/admin/inspector`로 이동하며 `screen_id`, `asset_id`, `version`을 쿼리스트링으로 전달합니다 (`ScreenEditorHeader.tsx:42-74`, `ScreenEditorHeader.tsx:160-190`).
3. Regression 페이지는 `useSearchParams`로 해당 컨텍스트를 읽고 배너로 보여 줍니다(`apps/web/src/components/admin/RegressionWatchPanel.tsx:46-235`). Inspector는 `trace_id` 필터를 활용해 관련 증거를 더 빠르게 불러올 수 있습니다 (`apps/web/src/app/admin/inspector/page.tsx:200-268`).

## DoD 체크 (S1~S3)
| 항목 | 상태 | 근거 |
| --- | --- | --- |
| S1-0 UI Creator 작성 차단 | 완료 | `/ui-creator`는 read-only로 변경 완료 (`ScreenEditorHeader.tsx`에서 Runtime/Regression 버튼 구분) |
| S1-1 `/ui-defs` write 차단 | 완료 | backend에서 `/ui-defs` write 차단 (별도 문서 참고) |
| S1-2 ScreenEditor `/ui-defs` 제거 | 완료 | 에디터에서 `/asset-registry`만 사용 (`ScreenEditor.tsx` 로딩 코드) |
| S1-3 Publish 서버 검증 | 완료 | publish 엔드포인트 validate 보장 (백엔드 코드 확인) |
| S1-4 Runtime은 published-only | 완료 | `PublishedScreensList`와 `PublishedScreenDetail`이 `status=published`만 사용 (`PublishedScreensList.tsx:1-110`, `PublishedScreenDetail.tsx:1-102`) |
| S2-0~S2-4 Copilot/Canvas/Tree | 일부 진행 | Copilot 패널/Tree/Preview 등 부분 구현 중 (`apps/web/src/components/admin/screen-editor/**` 참조) |
| S3-0~S3-3 운영 UI | 완료 | Published UI와 CTA 완성 (`PublishedScreensList.tsx`, `ScreenEditorHeader.tsx`, `RegressionWatchPanel.tsx`) |

## Known gaps
- Regression 페이지는 `screen_id` 기반 필터를 자동으로 선택하지 않음 (`RegressionWatchPanel.tsx:90-165`). 이후 순서(예: S3-3 확장)에서 query param을 기본 필터로 활용해야 합니다.
- Inspector CTA는 trace_id 선택을 유도하나, 관련 trace 목록을 자동으로 스코프하지 않음 (`apps/web/src/app/admin/inspector/page.tsx:200-268`). 개선 시 trace_id 또는 screen_id 필터를 강제하는 UI가 필요합니다.
- S2 Copilot 패치 적용/preview(Diff 탭 통합)는 아직 완전하지 않음 (`editor-state.tsx`의 patch/preview 상태 필드 참고). S3-4에서는 문서화 수준으로만 언급했습니다.

## Demo validation
1. `/admin/screens`에서 screen 생성 → ScreenEditor 열기 → Publish.
2. `/ui/screens`에서 published card 확인 → 클릭해서 `/ui/screens/{asset_id}` 렌더.
3. ScreenEditor에서 “Run Regression”/“Open Inspector” 클릭 → 각각 `/admin/regression` + `/admin/inspector` 이동.
4. Regression 페이지에서 배너가 context 를 보여주는지 확인, Inspector에서 trace list(fetched via `/inspector/traces`) 검토.
5. 실패 시 `apps/api/logs/api.log`와 `/apps/web/logs/web.log` 확인, 각 Fetch API 요청의 HTTP 상태 코드 확인.
