"use client";

import React, { useState, useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  addEdge,
  Connection,
  Edge,
  Node,
  NodeTypes,
  useNodesState,
  useEdgesState,
  OnConnect,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { Plus, Trash2, Save, Play } from "lucide-react";

interface WorkflowBuilderProps {
  workflow?: string;
  onChange?: (workflow: string) => void;
  readOnly?: boolean;
}

interface WorkflowNodeData {
  label: string;
  type: "sql" | "http" | "python";
  config: {
    query?: string;
    url?: string;
    method?: string;
    code?: string;
    params?: Record<string, unknown>;
  };
  nodeId: string;
}

// Custom node types
const SqlNode = ({ data }: { data: WorkflowNodeData }) => (
  <div className="rounded-2xl border-2 border-sky-600 bg-sky-500/10 px-4 py-2 text-center">
    <div className="text-tiny uppercase tracking-normal text-sky-400 font-semibold">
      SQL
    </div>
    <div className="mt-1 text-xs font-semibold text-foreground truncate max-w-48">
      {data.label}
    </div>
  </div>
);

const HttpNode = ({ data }: { data: WorkflowNodeData }) => (
  <div className="rounded-2xl border-2 border-emerald-500 bg-emerald-500/10 px-4 py-2 text-center">
    <div className="text-tiny uppercase tracking-normal text-emerald-400 font-semibold">
      HTTP
    </div>
    <div className="mt-1 text-xs font-semibold text-foreground truncate max-w-48">
      {data.label}
    </div>
  </div>
);

const PythonNode = ({ data }: { data: WorkflowNodeData }) => (
  <div className="rounded-2xl border-2 border-amber-500 bg-amber-500/10 px-4 py-2 text-center">
    <div className="text-tiny uppercase tracking-normal text-amber-400 font-semibold">
      Python
    </div>
    <div className="mt-1 text-xs font-semibold text-foreground truncate max-w-48">
      {data.label}
    </div>
  </div>
);

const nodeTypes: NodeTypes = {
  sql: SqlNode,
  http: HttpNode,
  python: PythonNode,
};

let nodeId = 0;

const getNextNodeId = () => {
  return `node_${nodeId++}`;
};

const createNode = (type: "sql" | "http" | "python"): Node<WorkflowNodeData> => {
  const id = getNextNodeId();
  return {
    id,
    type,
    position: { x: Math.random() * 500, y: Math.random() * 500 },
    data: {
      label: `${type.charAt(0).toUpperCase() + type.slice(1)} Node`,
      type,
      config: {},
      nodeId: id,
    },
  };
};

export default function WorkflowBuilder({ workflow, onChange, readOnly }: WorkflowBuilderProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodeType, setSelectedNodeType] = useState<"sql" | "http" | "python" | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node<WorkflowNodeData> | null>(null);
  const [workflowName, setWorkflowName] = useState<string>("");

  const onConnect: OnConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge({ ...params, markerEnd: { type: MarkerType.ArrowClosed } }, eds)),
    [setEdges]
  );

  const addNode = (type: "sql" | "http" | "python") => {
    const newNode = createNode(type);
    setNodes((nds) => [...nds, newNode]);
    setSelectedNodeType(null);
  };

  const removeNode = (nodeId: string) => {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
  };

  const updateNode = (nodeId: string, updates: Partial<WorkflowNodeData>) => {
    setNodes((nds) =>
      nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, ...updates } } : n))
    );
  };

  const clearWorkflow = () => {
    setNodes([]);
    setEdges([]);
    setWorkflowName("");
  };

  const generateWorkflowJSON = () => {
    const workflowConfig = {
      name: workflowName || "Untitled Workflow",
      version: "1.0",
      nodes: nodes.map((node) => ({
        id: node.id,
        label: node.data.label,
        type: node.data.type,
        config: node.data.config,
      })),
      edges: edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle,
        targetHandle: edge.targetHandle,
      })),
    };
    const jsonString = JSON.stringify(workflowConfig, null, 2);
    if (onChange) {
      onChange(jsonString);
    }
    return jsonString;
  };

  const parseWorkflowJSON = (jsonString: string) => {
    try {
      const config = JSON.parse(jsonString);
      if (config.name) {
        setWorkflowName(config.name);
      }
      if (config.nodes) {
        setNodes(
          config.nodes.map((node: any) => ({
            id: node.id,
            type: node.type,
            position: { x: Math.random() * 500, y: Math.random() * 500 },
            data: {
              label: node.label,
              type: node.type,
              config: node.config || {},
              nodeId: node.id,
            },
          }))
        );
      }
      if (config.edges) {
        setEdges(
          config.edges.map((edge: any) => ({
            id: `${edge.source}-${edge.target}`,
            source: edge.source,
            target: edge.target,
            sourceHandle: edge.sourceHandle,
            targetHandle: edge.targetHandle,
            markerEnd: { type: MarkerType.ArrowClosed },
          }))
        );
      }
    } catch (error) {
      console.error("Failed to parse workflow JSON:", error);
      alert("Invalid workflow JSON format");
    }
  };

  React.useEffect(() => {
    if (workflow) {
      parseWorkflowJSON(workflow);
    }
  }, [workflow]);

  React.useEffect(() => {
    if (nodes.length > 0) {
      generateWorkflowJSON();
    }
  }, [nodes, edges, workflowName]);

  return (
    <div className="builder-container space-y-4 rounded-2xl p-4">
      <h3 className="builder-title text-xs uppercase tracking-normal">Workflow Builder</h3>

      {/* Workflow Name */}
      <div className="space-y-2">
        <label className="builder-label-text text-xs uppercase tracking-normal">Workflow Name</label>
        <input
          type="text"
          value={workflowName}
          onChange={(e) => setWorkflowName(e.target.value)}
          disabled={readOnly}
          placeholder="My Workflow"
          className="builder-select-field w-full rounded-2xl border px-3 py-2 text-sm outline-none transition focus:border-sky-500"
        />
      </div>

      {/* Node Type Selection */}
      <div className="space-y-2">
        <label className="builder-label-text text-xs uppercase tracking-normal">Add Node</label>
        <div className="flex gap-2">
          {(["sql", "http", "python"] as const).map((type) => (
            <button
              key={type}
              onClick={() => addNode(type)}
              disabled={readOnly}
              className={`flex-1 rounded-2xl border px-4 py-2 text-xs font-bold uppercase tracking-normal text-foreground transition ${
                type === "sql"
                  ? "border-sky-500/50 bg-sky-600/80 hover:bg-sky-500 dark:hover:bg-sky-700"
                  : type === "http"
                  ? "border-emerald-500/50 bg-emerald-500/80 hover:bg-emerald-400"
                  : "border-amber-500/50 bg-amber-500/80 hover:bg-amber-400"
              }`}
            >
              <Plus className="mr-2 h-4 w-4" />
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* Workflow Canvas */}
      <div className="builder-canvas-container h-[600px] rounded-2xl border">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          deleteKeyCode="Delete"
          className="builder-canvas-inner"
        >
          <Background color="var(--chart-tooltip-bg)" gap={16} />
          <Controls />
          <MiniMap
            nodeColor={(n: Node) => {
              if (n.type === "sql") return "rgb(59, 130, 246)";
              if (n.type === "http") return "rgb(16, 185, 129)";
              if (n.type === "python") return "rgb(245, 158, 11)";
              return "rgb(100, 116, 139)";
            }}
            nodeStrokeWidth={3}
            zoomable
            pannable
          />
        </ReactFlow>
      </div>

      {/* Selected Node Configuration */}
      {selectedNode && (
        <div className="builder-config-panel space-y-3 rounded-2xl border p-4">
          <div className="flex items-center justify-between">
            <h4 className="builder-title text-xs uppercase tracking-normal">
              Node Configuration: {selectedNode.data.label}
            </h4>
            <button
              onClick={() => setSelectedNode(null)}
              className="builder-button-secondary rounded-full border px-2 py-1 text-tiny"
            >
              Close
            </button>
          </div>

          {/* Node Label */}
          <div className="space-y-1">
            <label className="builder-label-small text-tiny uppercase tracking-normal">Label</label>
            <input
              type="text"
              value={selectedNode.data.label}
              onChange={(e) =>
                updateNode(selectedNode.id, { label: e.target.value })
              }
              disabled={readOnly}
              className="builder-select-small w-full rounded-xl border px-3 py-2 text-xs outline-none transition focus:border-sky-500"
            />
          </div>

          {/* SQL Node Config */}
          {selectedNode.data.type === "sql" && (
            <div className="space-y-2">
              <label className="builder-label-small text-tiny uppercase tracking-normal">
                SQL Query
              </label>
              <textarea
                value={selectedNode.data.config.query || ""}
                onChange={(e) =>
                  updateNode(selectedNode.id, {
                    config: { ...selectedNode.data.config, query: e.target.value },
                  })
                }
                disabled={readOnly}
                rows={4}
                placeholder="SELECT * FROM table WHERE condition = 'value'"
                className="builder-textarea w-full rounded-xl border px-3 py-2 text-xs text-foreground outline-none transition focus:border-sky-500"
              />
            </div>
          )}

          {/* HTTP Node Config */}
          {selectedNode.data.type === "http" && (
            <div className="space-y-2">
              <div className="grid gap-2 grid-cols-2">
                <div className="space-y-1">
                  <label className="builder-label-small text-tiny uppercase tracking-normal">
                    Method
                  </label>
                  <select
                    value={selectedNode.data.config.method || "GET"}
                    onChange={(e) =>
                      updateNode(selectedNode.id, {
                        config: { ...selectedNode.data.config, method: e.target.value },
                      })
                    }
                    disabled={readOnly}
                    className="builder-select-small w-full rounded-xl border px-3 py-2 text-xs outline-none transition focus:border-sky-500"
                  >
                    <option value="GET">GET</option>
                    <option value="POST">POST</option>
                    <option value="PUT">PUT</option>
                    <option value="DELETE">DELETE</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="builder-label-small text-tiny uppercase tracking-normal">
                    URL
                  </label>
                  <input
                    type="text"
                    value={selectedNode.data.config.url || ""}
                    onChange={(e) =>
                      updateNode(selectedNode.id, {
                        config: { ...selectedNode.data.config, url: e.target.value },
                      })
                    }
                    disabled={readOnly}
                    placeholder="https://api.example.com/endpoint"
                    className="builder-select-small w-full rounded-xl border px-3 py-2 text-xs outline-none transition focus:border-sky-500"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Python Node Config */}
          {selectedNode.data.type === "python" && (
            <div className="space-y-2">
              <label className="builder-label-small text-tiny uppercase tracking-normal">
                Python Code
              </label>
              <textarea
                value={selectedNode.data.config.code || ""}
                onChange={(e) =>
                  updateNode(selectedNode.id, {
                    config: { ...selectedNode.data.config, code: e.target.value },
                  })
                }
                disabled={readOnly}
                rows={6}
                placeholder="def main(params, input_payload):\n    # Your code here\n    pass"
                className="builder-textarea w-full rounded-xl border px-3 py-2 text-xs outline-none transition focus:border-sky-500 font-mono"
              />
            </div>
          )}

          {/* Remove Node Button */}
          <button
            onClick={() => removeNode(selectedNode.id)}
            disabled={readOnly}
            className="w-full flex items-center justify-center gap-2 rounded-xl border border-rose-500/50 bg-rose-500/80 px-4 py-2 text-xs font-bold uppercase tracking-normal text-white transition hover:bg-rose-400"
          >
            <Trash2 className="h-4 w-4" />
            Remove Node
          </button>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center justify-between">
        <button
          onClick={clearWorkflow}
          disabled={readOnly}
          className="builder-button-reset rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-normal transition"
        >
          Clear Workflow
        </button>
        <div className="flex gap-2">
          <button
            onClick={() => generateWorkflowJSON()}
            disabled={readOnly}
            className="flex items-center gap-2 rounded-full border border-indigo-500/30 bg-indigo-500/80 px-4 py-2 text-xs font-bold uppercase tracking-normal text-foreground transition hover:bg-indigo-400 hover:shadow-md"
          >
            <Save className="h-4 w-4" />
            Save
          </button>
          <button
            onClick={() => {
              const json = generateWorkflowJSON();
              console.log("Executing workflow:", json);
              alert("Workflow execution would start here. (In production, integrate with Workflow Executor)");
            }}
            disabled={readOnly}
            className="flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/80 px-4 py-2 text-xs font-bold uppercase tracking-normal text-white transition hover:bg-emerald-400 hover:shadow-md"
          >
            <Play className="h-4 w-4" />
            Execute
          </button>
        </div>
      </div>

      {/* Workflow JSON Preview */}
      <div className="builder-preview-container space-y-2 rounded-2xl border p-4">
        <h4 className="builder-title text-xs uppercase tracking-normal">
          Workflow JSON
        </h4>
        <pre className="builder-json-preview max-h-40 overflow-auto rounded-xl p-3 text-xs font-mono">
          {generateWorkflowJSON()}
        </pre>
      </div>

      {/* Help Section */}
      <div className="builder-help-section space-y-2 rounded-2xl border p-3">
        <h4 className="builder-help-title text-xs uppercase tracking-normal">Quick Help</h4>
        <div className="builder-help-text space-y-1 text-xs">
          <p>• Drag nodes to position them on the canvas</p>
          <p>• Connect nodes by dragging from one node's handle to another</p>
          <p>• Click on a node to configure its properties</p>
          <p>• Press <span className="font-mono text-sky-400">Delete</span> key to remove selected node</p>
          <p>• Use <span className="font-mono text-sky-400">{"{{steps.node_id.rows}}"}</span> for parameter mapping</p>
          <p>• Available node types: SQL, HTTP, Python</p>
        </div>
      </div>
    </div>
  );
}
