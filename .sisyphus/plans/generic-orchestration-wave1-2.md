# Generic Orchestration Wave 1-2 Plan

## TL;DR

> **Quick Summary**: Implement Phase 0–2 to remove CI hardcoded keywords, add Tool Assets to Asset Registry, and enable dynamic tool loading with inventory-domain seed tools.
>
> **Deliverables**:
> - 6 mapping seed YAMLs for planner keyword sources
> - Tool Asset DB schema + CRUD + loader + API
> - DynamicTool + registry loading from tool assets
> - Inventory seed tools + tests
>
> **Estimated Effort**: Large
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: P1-1 → P1-2 → P1-3 → P1-4 → P2-1 → P2-2 → P2-3

---

## Context

### Original Request
Create a detailed work plan for Wave 1 (Phase 0–1) and Wave 2 (Phase 2) of the generic orchestration system, following Oracle’s guidance and project standards.

### Interview Summary
**Key Discussions**:
- Use TDD with pytest and run `pytest tests/unit/test_*.py -v` after each task.
- Validation domain for dynamic tools: inventory (simple CRUD).
- Tool asset YAML schema is defined in `docs/NEW_ORCHESTRATION.md` Phase 1.
- Wave 1 is API-only; Admin UI deferred to Wave 3.

**Research Findings**:
- Asset Registry already supports multiple asset types with loader fallback patterns.
- Planner has multiple hardcoded keyword maps that already use mapping loader + caching.
- Tool registry is string-based and can be extended for dynamic tools.

### Metis Review
**Identified Gaps** (addressed):
- Metis consultation tool unavailable in this environment; proceeded with explicit guardrails and defaults.

---

## Work Objectives

### Core Objective
Enable domain-agnostic orchestration by migrating planner keyword mappings to mapping assets, adding tool assets to the registry, and loading/executing dynamic tools from assets (validated via inventory domain).

### Concrete Deliverables
- 6 mapping YAML seeds under `apps/api/resources/mappings/`
- Tool asset schema fields in `tb_asset_registry` + Alembic migration
- ToolAsset CRUD + loader + API endpoints (`/ops/tool-assets`)
- DynamicTool class + registry loader from tool assets
- Inventory tool seed YAMLs under `apps/api/resources/tools/`

### Definition of Done
- All Phase 0–2 tests pass: `pytest tests/unit/test_*.py -v`
- Mapping assets load from DB via importer and planner keyword usage reflects assets
- Tool assets can be created, published, loaded, and executed by DynamicTool

### Must Have
- TDD workflow enforced for each task.
- API-only scope for Wave 1.

### Must NOT Have (Guardrails)
- No Admin UI changes in Wave 1.
- No Phase 3–5 work.
- No DAG executor (Phase 4) work.
- No changes to existing tool contract schemas beyond required additions.

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **User wants tests**: TDD
- **Framework**: pytest

### TDD Workflow (Applies to Every Task)
1. **RED**: Write failing test
   - Command: `pytest tests/unit/test_*.py -v`
   - Expected: at least 1 failure related to the new test
2. **GREEN**: Implement minimal code to pass
   - Command: `pytest tests/unit/test_*.py -v`
   - Expected: all tests pass
3. **REFACTOR**: Cleanup while keeping green
   - Command: `pytest tests/unit/test_*.py -v`
   - Expected: all tests pass

### Manual Execution Verification (Always include)
- API endpoints verified via curl for create/list/publish flow.
- Mapping importer run and logs reviewed for created assets.
- DynamicTool execution validated via a minimal request in a test or REPL.

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── P0-1 Mapping seed YAMLs (6 files)
├── P0-2 Mapping importer/script verification
└── P1-1 Tool asset DB migration + model fields

Wave 2 (After Wave 1):
├── P0-3 Planner keyword loader updates + tests
├── P1-2 Tool asset schemas + validators
└── P1-3 Tool asset CRUD + loader

Wave 3 (After Wave 2):
├── P1-4 Tool asset API router (/ops/tool-assets)
├── P2-1 DynamicTool class
├── P2-2 Tool registry load-from-asset
└── P2-3 Inventory seed tools + tests
```

Critical Path: P1-1 → P1-2 → P1-3 → P1-4 → P2-1 → P2-2 → P2-3

---

## TODOs

- [ ] P0-1. Create 6 mapping seed YAMLs for planner keywords

  **What to do**:
  - Create 6 YAML files under `apps/api/resources/mappings/` for:
    - `metric_aliases.yaml`
    - `agg_keywords.yaml`
    - `series_keywords.yaml`
    - `history_keywords.yaml`
    - `list_keywords.yaml`
    - `table_hints.yaml`
  - Mirror existing mapping seed structure (`name`, `description`, `mapping_type`, `scope`, `content`).
  - Populate `content` from existing hardcoded maps in planner.

  **Must NOT do**:
  - Do not add or modify other mapping types (cep/graph_scope/auto/filterable) in Phase 0.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Multi-file seed data creation with schema alignment.
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: No UI work.
    - `playwright`: No browser validation.

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with P0-2, P1-1)
  - **Blocks**: P0-3
  - **Blocked By**: None

  **References**:
  - `apps/api/resources/mappings/graph_relation_mapping.yaml` - Seed file structure pattern for mapping assets.
  - `apps/api/app/modules/ops/services/ci/planner/planner_llm.py` - Hardcoded keyword sets to migrate.

  **Acceptance Criteria**:
  - [ ] 6 new YAML files exist under `apps/api/resources/mappings/`.
  - [ ] Each file has `name`, `mapping_type`, `scope`, and `content` populated.
  - [ ] `pytest tests/unit/test_*.py -v` passes after implementation.

  **Manual Execution Verification**:
  - [ ] Open each YAML to confirm values match planner hardcoded lists.

  **Risk Mitigation**:
  - Risk: Inconsistent mapping_type naming → Mitigate by using `name` as mapping_type and aligning with loader expectations.

  **Files to create/modify**:
  - Create: `apps/api/resources/mappings/metric_aliases.yaml`
  - Create: `apps/api/resources/mappings/agg_keywords.yaml`
  - Create: `apps/api/resources/mappings/series_keywords.yaml`
  - Create: `apps/api/resources/mappings/history_keywords.yaml`
  - Create: `apps/api/resources/mappings/list_keywords.yaml`
  - Create: `apps/api/resources/mappings/table_hints.yaml`

- [ ] P0-2. Seed mapping assets into DB (scripted import)

  **What to do**:
  - Use or extend `scripts/mapping_asset_importer.py` to import the 6 new mapping assets.
  - Add a convenience wrapper script (if needed) for CI scope import.

  **Must NOT do**:
  - Do not publish non-target mapping assets.

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single script adjustment + manual run.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with P0-1, P1-1)
  - **Blocks**: P0-3
  - **Blocked By**: None

  **References**:
  - `scripts/mapping_asset_importer.py` - Existing mapping import workflow and payload structure.
  - `apps/api/app/modules/asset_registry/router.py` - Asset registry create/publish endpoints.

  **Acceptance Criteria**:
  - [ ] Importer lists all 6 YAML files for scope `ci`.
  - [ ] `--apply --publish` creates published mapping assets for all 6.
  - [ ] `pytest tests/unit/test_*.py -v` passes after implementation.

  **Manual Execution Verification**:
  - [ ] Run: `python scripts/mapping_asset_importer.py --scope ci --apply --publish`
  - [ ] Verify output shows 6 assets created/published.

  **Risk Mitigation**:
  - Risk: Duplicate drafts block publish → Mitigate with `--cleanup-drafts` option.

  **Files to create/modify**:
  - Modify: `scripts/mapping_asset_importer.py` (only if wrapper logic is required)
  - Optional Create: `scripts/seed_mapping_keywords.py`

- [ ] P0-3. Update planner keyword loaders to rely on mapping assets + tests

  **What to do**:
  - Write tests to confirm `_get_*` keyword loaders pull from mapping assets (RED).
  - Update `planner_llm.py` to remove hardcoded fallbacks for the 6 migrated keyword sets.
  - Keep regex constants as-is (explicitly allowed).

  **Must NOT do**:
  - Do not touch cep/graph_scope/auto/filterable keyword loaders in Phase 0.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Behavior change + tests in planner logic.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with P1-2, P1-3)
  - **Blocks**: None
  - **Blocked By**: P0-1, P0-2

  **References**:
  - `apps/api/app/modules/ops/services/ci/planner/planner_llm.py` - Keyword loader functions and caches.
  - `apps/api/app/modules/asset_registry/loader.py` - `load_mapping_asset` behavior.

  **Acceptance Criteria**:
  - [ ] New unit tests fail before code changes, pass after (TDD).
  - [ ] Hardcoded keyword fallbacks removed for the 6 mapping assets.
  - [ ] `pytest tests/unit/test_*.py -v` passes.

  **Manual Execution Verification**:
  - [ ] In a REPL/test, call `_get_*` and confirm values match seeded mappings.

  **Risk Mitigation**:
  - Risk: Planner behavior changes if mapping not found → Mitigate by ensuring DB seed publish as prerequisite.

  **Files to create/modify**:
  - Modify: `apps/api/app/modules/ops/services/ci/planner/planner_llm.py`
  - Create: `apps/api/tests/unit/test_planner_mapping_assets.py`

- [ ] P1-1. Add tool asset columns to `tb_asset_registry` (migration + model)

  **What to do**:
  - Create Alembic migration to add columns:
    - `tool_type` (Text)
    - `tool_config` (JSONB)
    - `tool_input_schema` (JSONB)
    - `tool_output_schema` (JSONB)
  - Update `TbAssetRegistry` model to include these fields.

  **Must NOT do**:
  - Do not remove or rename existing columns.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Migration + model update.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with P0-1, P0-2)
  - **Blocks**: P1-2, P1-3, P1-4
  - **Blocked By**: None

  **References**:
  - `apps/api/app/modules/asset_registry/models.py` - `TbAssetRegistry` field definitions.
  - `apps/api/alembic/versions/0039_add_source_asset_type.py` - Migration style reference.

  **Acceptance Criteria**:
  - [ ] Alembic migration file created and applies cleanly.
  - [ ] Model fields match migration types.
  - [ ] `pytest tests/unit/test_*.py -v` passes.

  **Manual Execution Verification**:
  - [ ] Run `make api-migrate` and confirm no errors.

  **Risk Mitigation**:
  - Risk: JSONB default null handling → Mitigate by matching existing JSONB nullable patterns.

  **Files to create/modify**:
  - Create: `apps/api/alembic/versions/0041_add_tool_asset_fields.py` (new revision)
  - Modify: `apps/api/app/modules/asset_registry/models.py`

- [ ] P1-2. Add ToolAsset Pydantic schemas + validators

  **What to do**:
  - Add `ToolAssetCreate`, `ToolAssetRead`, `ToolAssetUpdate` schemas.
  - Extend `validate_asset` with `validate_tool_asset` for publish-time checks.
  - Align schema fields to `docs/NEW_ORCHESTRATION.md` Phase 1 spec.

  **Must NOT do**:
  - Do not change existing schema classes.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Schema + validation changes.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with P0-3, P1-3)
  - **Blocks**: P1-3, P1-4
  - **Blocked By**: P1-1

  **References**:
  - `apps/api/app/modules/asset_registry/schemas.py` - Existing asset schemas.
  - `apps/api/app/modules/asset_registry/validators.py` - Asset validation patterns.
  - `docs/NEW_ORCHESTRATION.md:872` - Tool asset YAML schema definition.

  **Acceptance Criteria**:
  - [ ] Schemas expose `tool_type`, `tool_config`, `tool_input_schema`, `tool_output_schema`.
  - [ ] `validate_tool_asset` enforces required fields for publish.
  - [ ] `pytest tests/unit/test_*.py -v` passes.

  **Manual Execution Verification**:
  - [ ] Instantiate schemas in a REPL or test to ensure validation errors on missing fields.

  **Risk Mitigation**:
  - Risk: Overly strict validation blocks drafts → Mitigate by validating only on publish.

  **Files to create/modify**:
  - Modify: `apps/api/app/modules/asset_registry/schemas.py`
  - Modify: `apps/api/app/modules/asset_registry/validators.py`

- [ ] P1-3. Add ToolAsset CRUD + loader

  **What to do**:
  - Add CRUD helpers: `create_tool_asset`, `get_tool_asset`, `list_tool_assets`.
  - Add `load_tool_asset()` loader with DB → file fallback in `asset_registry/loader.py`.
  - Define file fallback location `apps/api/resources/tools/*.yaml`.

  **Must NOT do**:
  - Do not change existing asset list/create behaviors.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: CRUD + loader + asset registry integration.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with P0-3, P1-2)
  - **Blocks**: P1-4, P2-2
  - **Blocked By**: P1-1, P1-2

  **References**:
  - `apps/api/app/modules/asset_registry/crud.py` - CRUD patterns and publish workflow.
  - `apps/api/app/modules/asset_registry/loader.py` - Loader fallback patterns.

  **Acceptance Criteria**:
  - [ ] CRUD functions return `TbAssetRegistry` for tool assets.
  - [ ] `load_tool_asset` returns payload with `tool_*` fields.
  - [ ] `pytest tests/unit/test_*.py -v` passes.

  **Manual Execution Verification**:
  - [ ] Use Python shell to create tool asset draft and confirm loader fetches it.

  **Risk Mitigation**:
  - Risk: loader fallback bypasses real-mode constraints → Mitigate by mirroring `_is_real_mode` checks.

  **Files to create/modify**:
  - Modify: `apps/api/app/modules/asset_registry/crud.py`
  - Modify: `apps/api/app/modules/asset_registry/loader.py`

- [ ] P1-4. Add ToolAsset API router (`/ops/tool-assets`)

  **What to do**:
  - Add API endpoints for tool asset create/list/get/publish.
  - Mount under `/ops/tool-assets` (API-only for Wave 1).
  - Reuse ResponseEnvelope and auth patterns.

  **Must NOT do**:
  - Do not expose admin UI or non-ops routes.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: New API surface + registry integration.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with P2-1, P2-2, P2-3)
  - **Blocks**: P2-2
  - **Blocked By**: P1-3

  **References**:
  - `apps/api/app/modules/asset_registry/router.py` - Asset endpoints and ResponseEnvelope usage.
  - `apps/api/app/modules/ops/router.py` - `/ops` router inclusion patterns.

  **Acceptance Criteria**:
  - [ ] `/ops/tool-assets` endpoints respond with ResponseEnvelope.
  - [ ] Publish workflow updates `status` and version history.
  - [ ] `pytest tests/unit/test_*.py -v` passes.

  **Manual Execution Verification**:
  - [ ] `curl -X POST http://localhost:8000/ops/tool-assets` creates a draft.
  - [ ] `curl -X POST http://localhost:8000/ops/tool-assets/{id}/publish` publishes.

  **Risk Mitigation**:
  - Risk: route conflict with existing asset endpoints → Mitigate by using explicit `/ops/tool-assets` prefix.

  **Files to create/modify**:
  - Create: `apps/api/app/modules/ops/tool_assets_router.py`
  - Modify: `apps/api/app/modules/ops/router.py`

- [ ] P2-1. Implement `DynamicTool` class

  **What to do**:
  - Create `DynamicTool` extending `BaseTool`.
  - Accept tool asset metadata (type/config/input/output schemas).
  - Implement `should_execute`/`execute` using tool_config and existing executor patterns.

  **Must NOT do**:
  - Do not hardcode CI tool types in the dynamic implementation.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Core mechanics of dynamic execution.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with P1-4, P2-2, P2-3)
  - **Blocks**: P2-2
  - **Blocked By**: P1-3

  **References**:
  - `apps/api/app/modules/ops/services/ci/tools/base.py` - `BaseTool` interface.
  - `apps/api/app/modules/ops/services/ci/tools/ci.py` - Example tool execution pattern.

  **Acceptance Criteria**:
  - [ ] `DynamicTool` can be instantiated with asset data.
  - [ ] `execute` returns `ToolResult` and respects tool_config.
  - [ ] `pytest tests/unit/test_*.py -v` passes.

  **Manual Execution Verification**:
  - [ ] Run a unit test or REPL call to `DynamicTool.execute` with inventory tool config.

  **Risk Mitigation**:
  - Risk: mismatched config schema → Mitigate by validating tool_config against tool_input_schema.

  **Files to create/modify**:
  - Create: `apps/api/app/modules/ops/services/ci/tools/dynamic.py`

- [ ] P2-2. Extend ToolRegistry to load tools from assets

  **What to do**:
  - Add `register_from_asset()` and `load_from_db()` to `ToolRegistry`.
  - Use `load_tool_asset()` to fetch published tools and register them dynamically.
  - Update registry initialization to call dynamic loader.

  **Must NOT do**:
  - Do not remove current static tool registrations.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Registry behavior changes + initialization flow.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with P1-4, P2-1, P2-3)
  - **Blocks**: P2-3
  - **Blocked By**: P1-3, P2-1

  **References**:
  - `apps/api/app/modules/ops/services/ci/tools/base.py` - `ToolRegistry` implementation.
  - `apps/api/app/modules/ops/services/ci/tools/registry_init.py` - initialization entrypoint.
  - `apps/api/app/modules/asset_registry/loader.py` - `load_tool_asset()`.

  **Acceptance Criteria**:
  - [ ] Registry exposes dynamically loaded tool types in `list_tool_types()`.
  - [ ] No regressions for existing CI/Graph/Metric tools.
  - [ ] `pytest tests/unit/test_*.py -v` passes.

  **Manual Execution Verification**:
  - [ ] Log or assert that inventory tools are registered after initialization.

  **Risk Mitigation**:
  - Risk: double registration collisions → Mitigate by graceful skip (existing registry behavior).

  **Files to create/modify**:
  - Modify: `apps/api/app/modules/ops/services/ci/tools/base.py`
  - Modify: `apps/api/app/modules/ops/services/ci/tools/registry_init.py`

- [ ] P2-3. Seed inventory tool assets + tests

  **What to do**:
  - Create 2–3 tool YAMLs under `apps/api/resources/tools/` for inventory CRUD (e.g., `inventory_create`, `inventory_read`, `inventory_update`).
  - Add tool asset importer script (mirroring mapping importer).
  - Add tests validating loader + registry registration + DynamicTool execution.

  **Must NOT do**:
  - Do not embed complex domain logic; keep tool behavior minimal.

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Seed assets + loader + dynamic execution tests.
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with P1-4, P2-1, P2-2)
  - **Blocks**: None
  - **Blocked By**: P1-3, P2-2

  **References**:
  - `docs/NEW_ORCHESTRATION.md:872` - Tool asset YAML schema spec.
  - `apps/api/app/modules/asset_registry/loader.py` - load patterns for assets.
  - `apps/api/app/modules/ops/services/ci/tools/base.py` - registry interface.

  **Acceptance Criteria**:
  - [ ] Inventory tool YAMLs validate against tool schema and import cleanly.
  - [ ] DynamicTool can execute one inventory tool end-to-end in tests.
  - [ ] `pytest tests/unit/test_*.py -v` passes.

  **Manual Execution Verification**:
  - [ ] Run importer: `python scripts/tool_asset_importer.py --apply --publish`.
  - [ ] Confirm registered tools include inventory tool names.

  **Risk Mitigation**:
  - Risk: tool execution relies on missing data sources → Mitigate by using mock or in-memory executor in tests.

  **Files to create/modify**:
  - Create: `apps/api/resources/tools/inventory_create.yaml`
  - Create: `apps/api/resources/tools/inventory_read.yaml`
  - Create: `apps/api/resources/tools/inventory_update.yaml`
  - Create: `scripts/tool_asset_importer.py`
  - Create: `apps/api/tests/unit/test_dynamic_tool_registry.py`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|-----------|---------|-------|--------------|
| P0 group | `feat(assets): add mapping keyword seeds` | `apps/api/resources/mappings/*` | `pytest tests/unit/test_*.py -v` |
| P1 group | `feat(assets): add tool asset schema and api` | migration, asset registry files | `pytest tests/unit/test_*.py -v` |
| P2 group | `feat(tools): load dynamic tools from assets` | tool registry + dynamic tool | `pytest tests/unit/test_*.py -v` |

---

## Success Criteria

### Verification Commands
```bash
pytest tests/unit/test_*.py -v
```

### Final Checklist
- [ ] 6 mapping seeds present and importable
- [ ] Tool asset schema + CRUD + loader + API working
- [ ] Dynamic tool registration and execution validated with inventory tools
