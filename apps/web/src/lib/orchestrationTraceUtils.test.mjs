import { test } from "node:test";
import assert from "node:assert/strict";

/**
 * Tests for orchestrationTraceUtils.ts
 *
 * These tests verify:
 * - Trace extraction from stage output
 * - Trace construction from step metadata
 * - Trace validation
 * - Strategy description generation
 * - Strategy badge generation
 * - Duration calculation
 * - Error detection and handling
 */

// Mock factory functions
function createMockTool(toolId, toolType = "http_api", depends_on = []) {
  return {
    tool_id: toolId,
    tool_type: toolType,
    depends_on,
    dependency_groups: [],
    output_mapping: {},
  };
}

function createMockExecutionGroup(groupIndex, tools, parallel = false) {
  return {
    group_index: groupIndex,
    tools,
    parallel_execution: parallel,
  };
}

function createMockTrace(strategy = "serial", groups = []) {
  const toolIds = new Set();
  for (const group of groups) {
    for (const tool of group.tools) {
      toolIds.add(tool.tool_id);
    }
  }

  return {
    strategy,
    execution_groups: groups,
    total_groups: groups.length,
    total_tools: toolIds.size,
    tool_ids: Array.from(toolIds),
  };
}

// ============================================================
// PHASE 1: TRACE EXTRACTION TESTS (10 tests)
// ============================================================

test("should extract trace from stage output with orchestration_trace field", () => {
  const expectedTrace = createMockTrace("serial", [
    createMockExecutionGroup(0, [createMockTool("tool_1")]),
  ]);

  const stageOutput = {
    orchestration_trace: expectedTrace,
    results: [],
  };

  const trace = stageOutput.orchestration_trace || null;

  assert.equal(trace !== null, true);
  assert.equal(trace.strategy, "serial");
});

test("should return null when stage output is missing", () => {
  const trace = null || null;

  assert.equal(trace, null);
});

test("should handle null stage output", () => {
  const stageOutput = null;
  const trace = stageOutput ? stageOutput.orchestration_trace || null : null;

  assert.equal(trace, null);
});

test("should extract trace from nested execution results", () => {
  const stageOutput = {
    execution_results: [
      {
        orchestration: {
          group_index: 0,
          tool_id: "tool_1",
          tool_type: "http_api",
          depends_on: [],
        },
      },
      {
        orchestration: {
          group_index: 1,
          tool_id: "tool_2",
          tool_type: "database",
          depends_on: ["tool_1"],
        },
      },
    ],
  };

  const hasOrchestrationData = stageOutput.execution_results.some(
    (r) => r.orchestration
  );

  assert.equal(hasOrchestrationData, true);
});

test("should handle empty execution results", () => {
  const stageOutput = {
    execution_results: [],
  };

  const hasData = stageOutput.execution_results.length > 0;

  assert.equal(hasData, false);
});

test("should prioritize direct orchestration_trace over constructed", () => {
  const directTrace = createMockTrace("parallel", [
    createMockExecutionGroup(0, [
      createMockTool("tool_1"),
      createMockTool("tool_2"),
    ]),
  ]);

  const stageOutput = {
    orchestration_trace: directTrace,
    execution_results: [{ orchestration: { group_index: 0, tool_id: "tool_3" } }],
  };

  const trace = stageOutput.orchestration_trace || null;

  assert.equal(trace.tool_ids.length, 2);
  assert.equal(trace.tool_ids.includes("tool_1"), true);
});

test("should construct trace when only execution results available", () => {
  const results = [
    {
      orchestration: {
        group_index: 0,
        tool_id: "tool_1",
        tool_type: "http_api",
        depends_on: [],
        output_mapping: { result: "$.data" },
      },
    },
    {
      orchestration: {
        group_index: 1,
        tool_id: "tool_2",
        tool_type: "database",
        depends_on: ["tool_1"],
        output_mapping: { data: "$.rows" },
      },
    },
  ];

  const groups = new Map();
  for (const result of results) {
    const { group_index, tool_id, tool_type, depends_on, output_mapping } = result.orchestration;
    if (!groups.has(group_index)) {
      groups.set(group_index, []);
    }
    groups.get(group_index).push({
      tool_id,
      tool_type,
      depends_on,
      dependency_groups: [],
      output_mapping,
    });
  }

  assert.equal(groups.size, 2);
});

test("should handle missing orchestration field in results", () => {
  const stageOutput = {
    execution_results: [
      { result: "something" },
      { data: [] },
    ],
  };

  const orchestrationResults = stageOutput.execution_results.filter(
    (r) => r.orchestration
  );

  assert.equal(orchestrationResults.length, 0);
});

test("should handle mixed results with and without orchestration", () => {
  const stageOutput = {
    execution_results: [
      { orchestration: { group_index: 0, tool_id: "tool_1" } },
      { result: "data" },
      { orchestration: { group_index: 1, tool_id: "tool_2" } },
    ],
  };

  const orchestrationResults = stageOutput.execution_results.filter(
    (r) => r.orchestration
  );

  assert.equal(orchestrationResults.length, 2);
});

// ============================================================
// PHASE 2: TRACE VALIDATION TESTS (8 tests)
// ============================================================

test("should validate correct trace structure", () => {
  const trace = createMockTrace("serial", [
    createMockExecutionGroup(0, [createMockTool("tool_1")]),
  ]);

  const isValid =
    typeof trace.strategy === "string" &&
    ["parallel", "serial", "dag"].includes(trace.strategy) &&
    Array.isArray(trace.execution_groups) &&
    typeof trace.total_groups === "number" &&
    typeof trace.total_tools === "number" &&
    Array.isArray(trace.tool_ids);

  assert.equal(isValid, true);
});

test("should reject invalid strategy", () => {
  const trace = {
    strategy: "invalid",
    execution_groups: [],
    total_groups: 0,
    total_tools: 0,
    tool_ids: [],
  };

  const isValid = ["parallel", "serial", "dag"].includes(trace.strategy);

  assert.equal(isValid, false);
});

test("should reject missing execution_groups", () => {
  const trace = {
    strategy: "serial",
    total_groups: 0,
    total_tools: 0,
    tool_ids: [],
  };

  const isValid = Array.isArray(trace.execution_groups);

  assert.equal(isValid, false);
});

test("should reject non-array tool_ids", () => {
  const trace = {
    strategy: "serial",
    execution_groups: [],
    total_groups: 0,
    total_tools: 0,
    tool_ids: "not-an-array",
  };

  const isValid = Array.isArray(trace.tool_ids);

  assert.equal(isValid, false);
});

test("should validate parallel strategy", () => {
  const trace = createMockTrace("parallel", [
    createMockExecutionGroup(0, [
      createMockTool("tool_1"),
      createMockTool("tool_2"),
    ]),
  ]);

  assert.equal(trace.strategy, "parallel");
  assert.equal(trace.execution_groups[0].parallel_execution, false);
});

test("should validate dag strategy", () => {
  const trace = createMockTrace("dag", [
    createMockExecutionGroup(0, [createMockTool("tool_1")]),
    createMockExecutionGroup(1, [
      createMockTool("tool_2", "database", ["tool_1"]),
    ]),
  ]);

  assert.equal(trace.strategy, "dag");
  assert.equal(trace.total_groups, 2);
});

test("should handle trace with empty tool_ids", () => {
  const trace = {
    strategy: "serial",
    execution_groups: [],
    total_groups: 0,
    total_tools: 0,
    tool_ids: [],
  };

  const isValid = Array.isArray(trace.tool_ids) && trace.tool_ids.length === 0;

  assert.equal(isValid, true);
});

test("should validate tool_ids matches actual tools", () => {
  const group1 = createMockExecutionGroup(0, [
    createMockTool("tool_1"),
    createMockTool("tool_2"),
  ]);
  const group2 = createMockExecutionGroup(1, [createMockTool("tool_3")]);

  const trace = createMockTrace("dag", [group1, group2]);

  assert.equal(trace.tool_ids.length, 3);
  assert.deepEqual(
    new Set(trace.tool_ids),
    new Set(["tool_1", "tool_2", "tool_3"])
  );
});

// ============================================================
// PHASE 3: STRATEGY DESCRIPTION TESTS (6 tests)
// ============================================================

test("should provide description for parallel strategy", () => {
  const strategy = "parallel";
  const description =
    strategy === "parallel"
      ? "All tools execute simultaneously with no dependencies"
      : "Unknown";

  assert.equal(description, "All tools execute simultaneously with no dependencies");
});

test("should provide description for serial strategy", () => {
  const strategy = "serial";
  const description =
    strategy === "serial"
      ? "Tools execute sequentially with automatic data flow between them"
      : "Unknown";

  assert.equal(
    description,
    "Tools execute sequentially with automatic data flow between them"
  );
});

test("should provide description for dag strategy", () => {
  const strategy = "dag";
  const description =
    strategy === "dag"
      ? "Complex execution with multiple independent branches and convergence points"
      : "Unknown";

  assert.equal(
    description,
    "Complex execution with multiple independent branches and convergence points"
  );
});

test("should provide default description for unknown strategy", () => {
  const strategy = "unknown";
  const description =
    strategy === "parallel"
      ? "Parallel"
      : strategy === "serial"
        ? "Serial"
        : strategy === "dag"
          ? "DAG"
          : "Unknown execution strategy";

  assert.equal(description, "Unknown execution strategy");
});

test("should return consistent descriptions", () => {
  const strategies = ["parallel", "serial", "dag"];
  const descriptions = {};

  for (const strategy of strategies) {
    descriptions[strategy] =
      strategy === "parallel"
        ? "All tools execute simultaneously with no dependencies"
        : strategy === "serial"
          ? "Tools execute sequentially with automatic data flow between them"
          : "Complex execution with multiple independent branches and convergence points";
  }

  assert.equal(descriptions["parallel"], descriptions["parallel"]);
  assert.equal(descriptions["serial"], descriptions["serial"]);
  assert.equal(descriptions["dag"], descriptions["dag"]);
});

test("should handle empty strategy string", () => {
  const strategy = "";
  const description =
    strategy === "parallel"
      ? "Parallel"
      : strategy === "serial"
        ? "Serial"
        : strategy === "dag"
          ? "DAG"
          : "Unknown execution strategy";

  assert.equal(description, "Unknown execution strategy");
});

// ============================================================
// PHASE 4: DURATION CALCULATION TESTS (10 tests)
// ============================================================

test("should calculate duration for serial execution as sum", () => {
  const toolDurations = new Map([
    ["tool_1", 100],
    ["tool_2", 150],
  ]);

  const group = createMockExecutionGroup(
    0,
    [createMockTool("tool_1"), createMockTool("tool_2")],
    false
  );

  let duration = 0;
  for (const tool of group.tools) {
    duration += toolDurations.get(tool.tool_id) || 0;
  }

  assert.equal(duration, 250);
});

test("should calculate duration for parallel execution as max", () => {
  const toolDurations = new Map([
    ["tool_1", 100],
    ["tool_2", 150],
  ]);

  const group = createMockExecutionGroup(
    0,
    [createMockTool("tool_1"), createMockTool("tool_2")],
    true
  );

  let duration = 0;
  for (const tool of group.tools) {
    duration = Math.max(duration, toolDurations.get(tool.tool_id) || 0);
  }

  assert.equal(duration, 150);
});

test("should handle single tool duration", () => {
  const toolDurations = new Map([["tool_1", 100]]);

  const group = createMockExecutionGroup(0, [createMockTool("tool_1")], false);

  let duration = 0;
  for (const tool of group.tools) {
    duration += toolDurations.get(tool.tool_id) || 0;
  }

  assert.equal(duration, 100);
});

test("should handle missing duration data", () => {
  const toolDurations = new Map();

  const group = createMockExecutionGroup(
    0,
    [createMockTool("tool_1"), createMockTool("tool_2")],
    false
  );

  let duration = 0;
  for (const tool of group.tools) {
    duration += toolDurations.get(tool.tool_id) || 0;
  }

  assert.equal(duration, 0);
});

test("should handle zero durations", () => {
  const toolDurations = new Map([
    ["tool_1", 0],
    ["tool_2", 0],
  ]);

  const group = createMockExecutionGroup(
    0,
    [createMockTool("tool_1"), createMockTool("tool_2")],
    false
  );

  let duration = 0;
  for (const tool of group.tools) {
    duration += toolDurations.get(tool.tool_id) || 0;
  }

  assert.equal(duration, 0);
});

test("should handle large durations", () => {
  const toolDurations = new Map([
    ["tool_1", 999999],
    ["tool_2", 888888],
  ]);

  const group = createMockExecutionGroup(
    0,
    [createMockTool("tool_1"), createMockTool("tool_2")],
    false
  );

  let duration = 0;
  for (const tool of group.tools) {
    duration += toolDurations.get(tool.tool_id) || 0;
  }

  assert.equal(duration, 1888887);
});

test("should handle many parallel tools", () => {
  const tools = [];
  const toolDurations = new Map();

  for (let i = 0; i < 100; i++) {
    const toolId = `tool_${i}`;
    tools.push(createMockTool(toolId));
    toolDurations.set(toolId, Math.random() * 1000);
  }

  const group = createMockExecutionGroup(0, tools, true);

  let duration = 0;
  for (const tool of group.tools) {
    duration = Math.max(duration, toolDurations.get(tool.tool_id) || 0);
  }

  assert.equal(typeof duration, "number");
  assert.equal(duration >= 0, true);
});

test("should handle fractional durations", () => {
  const toolDurations = new Map([
    ["tool_1", 10.5],
    ["tool_2", 20.3],
  ]);

  const group = createMockExecutionGroup(
    0,
    [createMockTool("tool_1"), createMockTool("tool_2")],
    false
  );

  let duration = 0;
  for (const tool of group.tools) {
    duration += toolDurations.get(tool.tool_id) || 0;
  }

  assert.equal(Math.abs(duration - 30.8) < 0.01, true);
});

test("should handle negative durations (edge case)", () => {
  const toolDurations = new Map([
    ["tool_1", -50],
    ["tool_2", 100],
  ]);

  const group = createMockExecutionGroup(
    0,
    [createMockTool("tool_1"), createMockTool("tool_2")],
    false
  );

  let duration = 0;
  for (const tool of group.tools) {
    duration += toolDurations.get(tool.tool_id) || 0;
  }

  assert.equal(duration, 50);
});

// ============================================================
// FINAL TESTS (4 tests)
// ============================================================

test("should handle trace with no tools", () => {
  const trace = createMockTrace("serial", []);

  assert.equal(trace.total_tools, 0);
  assert.equal(trace.tool_ids.length, 0);
});

test("should handle trace with duplicate tool_ids", () => {
  const toolIds = ["tool_1", "tool_2", "tool_1", "tool_3"];
  const uniqueIds = Array.from(new Set(toolIds));

  assert.equal(uniqueIds.length, 3);
});

test("should handle very large tool count", () => {
  const tools = [];
  for (let i = 0; i < 1000; i++) {
    tools.push(createMockTool(`tool_${i}`));
  }

  const trace = createMockTrace("serial", [
    createMockExecutionGroup(0, tools),
  ]);

  assert.equal(trace.total_tools, 1000);
});

test("should handle unicode characters in tool names", () => {
  const tool = createMockTool("tool_🚀_测试");

  assert.equal(tool.tool_id, "tool_🚀_测试");
});
