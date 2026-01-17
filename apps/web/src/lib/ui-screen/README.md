Screen Schema v1
================

This directory contains the Screen Schema v1 artifacts used by the UI Creator runtime.

Files
-----
- screen.schema.ts - TypeScript types and minimal helpers for the Screen Schema v1 (canonical for frontend runtime).
- screen.schema.json - JSON Schema (draft-07) used for validating screen.schema JSON at runtime or in the asset registry.

Design Notes
------------
- This implementation strictly follows CONTRACT_UI_CREATOR_V1.md and implements the MVP subset required for runtime rendering.
- The schema intentionally uses a flat `components` array for MVP; nested components for Modals/Tabs are supported via `props.components` but the editor-level nesting is out-of-scope.
- Binding expressions are dot-path-only (e.g., `{{state.device.id}}`). Computed expressions, functions, or dynamic indexing are explicitly NOT supported in v1.

MVP Subset (required fields to render):
- screen_id
- layout
- components[] (each component must include id and type; props optional)
- state.initial (required) - runtime uses this as the base state
- actions[] (required, can be empty or null) - component-level actions are supported
- bindings (required, can be empty or null) - map of target -> source for quick state initialization

Extensibility (NOT implemented in v1):
- Visibility rule evaluation (reserved field `visibility.rule`) - left as a placeholder for future phases.
- Computed props / transform functions - intentionally out-of-scope.
- Plugin-based custom components - out-of-scope.

Validation
----------
- Use the provided JSON Schema (`screen.schema.json`) to validate assets before publishing.

Runtime
-------
- The web runtime will load published Screen Assets and render them using the UIScreenRenderer. State initialization and bindings are applied at load-time.
- Action handlers referenced in component.actions.handler must map to deterministic executors registered server-side and executed via `/ops/ui-actions`.

Component Registry v1 (10 component families)
------------------------------------
Each component exposes props schema, supported binding kinds, and events.
`text`/`markdown`은 동일한 props schema를 공유합니다.

| Component Type | Props Schema (summary) | Bindings | Events |
| --- | --- | --- | --- |
| text | content, variant, color | state | - |
| markdown | content | state | - |
| button | label, variant, disabled | state | onClick |
| input | placeholder, inputType, name | state | onChange, onSubmit |
| table | columns, rows, selectable | state/result | onRowSelect, onRowClick |
| chart | series, options, type | state/result | onHover, onClick |
| badge | label, variant, color | state | - |
| tabs | tabs, activeIndex | state | onTabChange |
| modal | title, size, components, open | state | onOpen, onClose |
| keyvalue | items | state | - |
| divider | orientation | - | - |

Binding Examples (C5)
---------------------
1) Action payload from inputs:
   - payload_template: `{ "device_id": "{{inputs.device_id}}" }`
2) Component props from state:
   - props: `{ "rows": "{{state.results.list_maintenance_filtered}}" }`
3) Loading/Error binding:
   - `state.__loading.<action_id>` 또는 `state.__error.<action_id>` 값으로 로딩/에러 표시

Security
--------
- Do not include secrets or credentials in screen.asset.schema_json. Any sensitive inputs should be provided at runtime via inputs/context and will be masked in traces per project policy.
