# Draft: Generic Orchestration Wave 1-2 Plan

## Requirements (confirmed)
- Goal: Remove CI domain hardcoding; make system domain-agnostic via dynamic tool assets.
- Scope: Wave 1 (Phase 0-1) + Wave 2 (Phase 2) only.
- Phase 0: Move hardcoded keywords to mapping assets; add YAML seeds; loader + caching in planner; seed into DB; verify DB load.
- Phase 1: Add tool asset schema (migration + Pydantic DTOs + CRUD + loader + API router); test CRUD + publish workflow.
- Phase 2: Dynamic tool loading (DynamicTool + registry extensions + loader + registry init hook + seed tools); test load/execute.
- Defer: Phase 3-5 until non-CI validation; Phase 4 (DAG executor) deferred explicitly.
- Plan must include: atomic tasks, parallelization, dependencies, success criteria, risk mitigation, file lists, category + skills.
- Test strategy: TDD (pytest, @pytest.mark.asyncio), run `pytest tests/unit/test_*.py -v` after each task.
- Validation domain for Phase 2: inventory (simple CRUD tools).
- Tool asset YAML schema from NEW_ORCHESTRATION.md Phase 1 (name/description/tool_type/tool_config/tool_input_schema/tool_output_schema).
- Wave 1 scope: API-only (no admin UI updates); use curl/Postman for API testing.

## Technical Decisions
- Follow existing Asset Registry patterns (CRUD, loader fallback, caching) for tool assets.
- Use Oracle’s 3-wave sequencing; prioritize Phase 0-2 deliverables.

## Research Findings
- Oracle: architecture is solid; ToolRegistry and BaseTool are domain-agnostic; Asset Registry patterns proven.
- Oracle: after Phase 2, must be able to create tool asset, load dynamically, execute via DynamicTool.

## Open Questions
- Publish workflow expectations for tool assets: same as other asset types (draft/published)?
- Exact 6 mapping asset names for Phase 0 seed files (defaults needed).

## Scope Boundaries
- INCLUDE: Phases 0-2 only (mappings, tool asset schema, dynamic tool loading).
- EXCLUDE: Phase 3-5, DAG executor (Phase 4), full UI updates unless explicitly required.
