"use client";

import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";

interface TopologyNode {
  id: string;
  name: string;
  type: "server" | "service" | "db" | "network" | "storage";
  status: "healthy" | "warning" | "critical";
  baseline_load: number;
  simulated_load: number;
  load_change_pct: number;
}

interface TopologyLink {
  source: string;
  target: string;
  type: "dependency" | "traffic";
  baseline_traffic: number;
  simulated_traffic: number;
  traffic_change_pct: number;
}

interface TopologyData {
  nodes: TopologyNode[];
  links: TopologyLink[];
}

interface Envelope<T> {
  data?: T;
  message?: string;
  detail?: string;
}

interface TopologyMapProps {
  service: string;
  scenarioType: string;
  assumptions: Record<string, number>;
  enabled?: boolean;
}

export default function TopologyMap({
  service,
  scenarioType,
  assumptions,
  enabled = false,
}: TopologyMapProps) {
  const [topology, setTopology] = useState<TopologyData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);

  useEffect(() => {
    if (!enabled || !service) {
      setLoading(false);
      setTopology(null);
      return;
    }

    const fetchTopology = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({
          service,
          scenario_type: scenarioType,
        });
        
        // assumptions를 query param으로 추가
        Object.entries(assumptions).forEach(([key, value]) => {
          params.append(key, String(value));
        });

        const response = await authenticatedFetch<Envelope<{ topology: TopologyData }>>(
          `/api/sim/topology?${params.toString()}`
        );
        
        setTopology(response.data?.topology ?? null);
      } catch (err) {
        console.error("Failed to load topology:", err);
        setError(err instanceof Error ? err.message : "Failed to load topology");
      } finally {
        setLoading(false);
      }
    };

    // 디바운스 적용 (300ms)
    const timeoutId = setTimeout(fetchTopology, 300);
    
    return () => clearTimeout(timeoutId);
  }, [enabled, service, scenarioType, assumptions]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 " style={{ color: "var(--muted-foreground)" }}>
        Loading topology...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center p-8 text-rose-400">
        {error}
      </div>
    );
  }

  if (!topology) {
    return (
      <div className="flex items-center justify-center p-8 " style={{ color: "var(--muted-foreground)" }}>
        {enabled ? "No topology data" : "Run Simulation to load topology"}
      </div>
    );
  }

  // 간단한 레이아웃 계산 (force simulation 대신)
  const nodePositions = calculateNodePositions(topology);

  return (
    <div className="rounded-3xl border   p-5" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-overlay)" }}>
      <h2 className="text-sm font-semibold uppercase tracking-[0.25em] " style={{ color: "var(--foreground-secondary)" }}>
        System Topology Map
      </h2>
      <p className="mt-1 text-xs " style={{ color: "var(--muted-foreground)" }}>
        시뮬레이션 결과를 시스템 토폴로지에서 확인하세요.
      </p>

      <div className="mt-4 h-[500px] overflow-hidden rounded-2xl border  /50" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }}>
        <svg width="100%" height="100%" viewBox="0 0 800 500">
          {/* 링크 그리기 */}
          {topology.links.map((link, index) => {
            const source = nodePositions[link.source];
            const target = nodePositions[link.target];
            if (!source || !target) return null;

            const isTrafficLink = link.type === "traffic";
            const strokeWidth = Math.max(1, Math.min(5, link.simulated_traffic / 200));

            return (
              <line
                key={`link-${index}`}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke={isTrafficLink ? "#38bdf8" : "#64748b"}
                strokeWidth={strokeWidth}
                strokeOpacity={0.6}
                markerEnd={isTrafficLink ? "url(#arrowhead)" : undefined}
              />
            );
          })}

          {/* 링크 라벨 (트래픽 변화) */}
          {topology.links.map((link, index) => {
            const source = nodePositions[link.source];
            const target = nodePositions[link.target];
            if (!source || !target || link.type !== "traffic") return null;

            const midX = (source.x + target.x) / 2;
            const midY = (source.y + target.y) / 2;

            return (
              <text
                key={`link-label-${index}`}
                x={midX}
                y={midY - 10}
                fontSize="10"
                fill="#94a3b8"
                textAnchor="middle"
              >
                {link.traffic_change_pct >= 0 ? "+" : ""}
                {link.traffic_change_pct.toFixed(0)}%
              </text>
            );
          })}

          {/* 노드 그리기 */}
          {topology.nodes.map((node) => {
            const pos = nodePositions[node.id];
            if (!pos) return null;

            const radius = 25 + Math.abs(node.load_change_pct) / 5;
            const color =
              node.status === "critical"
                ? "#ef4444"
                : node.status === "warning"
                ? "#f59e0b"
                : "#22c55e";

            return (
              <g key={node.id}>
                {/* 노드 원 */}
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={radius}
                  fill={color}
                  stroke="#1e293b"
                  strokeWidth={2}
                  className="cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() => setSelectedNode(node)}
                />

                {/* 노드 타입 아이콘 */}
                <text
                  x={pos.x}
                  y={pos.y}
                  fontSize="16"
                  fill="white"
                  textAnchor="middle"
                  dominantBaseline="central"
                  className="pointer-events-none"
                >
                  {getTypeIcon(node.type)}
                </text>

                {/* 노드 이름 */}
                <text
                  x={pos.x}
                  y={pos.y + radius + 15}
                  fontSize="10"
                  fill="#e2e8f0"
                  textAnchor="middle"
                  className="pointer-events-none"
                >
                  {node.name}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* 범례 */}
      <div className="mt-3 flex items-center justify-between text-xs " style={{ color: "var(--muted-foreground)" }}>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-emerald-500" />
            <span>Healthy</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-amber-500" />
            <span>Warning</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-rose-500" />
            <span>Critical</span>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-1 bg-sky-400" />
          <span>Traffic</span>
          <div className="w-3 h-1 0" style={{ backgroundColor: "var(--surface-base)" }} />
          <span>Dependency</span>
        </div>
      </div>

      {/* 선택된 노드 상세 정보 */}
      {selectedNode && (
        <div className="mt-4 rounded-2xl border  /50 p-4" style={{ borderColor: "var(--border)" ,  backgroundColor: "var(--surface-base)" }}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="font-semibold text-white text-lg">{selectedNode.name}</h3>
              <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="" style={{ color: "var(--muted-foreground)" }}>Type:</span>
                  <span className="ml-2 text-white capitalize">{selectedNode.type}</span>
                </div>
                <div>
                  <span className="" style={{ color: "var(--muted-foreground)" }}>Status:</span>
                  <span
                    className={`ml-2 ${
                      selectedNode.status === "critical"
                        ? "text-rose-400"
                        : selectedNode.status === "warning"
                        ? "text-amber-400"
                        : "text-emerald-400"
                    }`}
                  >
                    {selectedNode.status}
                  </span>
                </div>
                <div>
                  <span className="" style={{ color: "var(--muted-foreground)" }}>Baseline:</span>
                  <span className="ml-2 text-white">{selectedNode.baseline_load}%</span>
                </div>
                <div>
                  <span className="" style={{ color: "var(--muted-foreground)" }}>Simulated:</span>
                  <span className="ml-2 text-white">{selectedNode.simulated_load}%</span>
                </div>
              </div>
              <div className="mt-2">
                <span className="" style={{ color: "var(--muted-foreground)" }}>Change:</span>
                <span
                  className={`ml-2 font-semibold ${
                    selectedNode.load_change_pct >= 0
                      ? "text-amber-400"
                      : "text-emerald-400"
                  }`}
                >
                  {selectedNode.load_change_pct >= 0 ? "+" : ""}
                  {selectedNode.load_change_pct}%
                </span>
              </div>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="ml-4  hover:text-white transition" style={{ color: "var(--muted-foreground)" }}
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// 유틸리티 함수: 노드 위치 계산 (링크 기반 계층형 레이아웃)
function calculateNodePositions(topology: TopologyData): Record<string, { x: number; y: number }> {
  const positions: Record<string, { x: number; y: number }> = {};
  const nodeIds = topology.nodes.map(n => n.id);
  const linkMap = new Map<string, string[]>(); // source -> targets

  // 링크 정보를 인접 리스트로 변환
  topology.links.forEach(link => {
    if (!linkMap.has(link.source)) {
      linkMap.set(link.source, []);
    }
    linkMap.get(link.source)?.push(link.target);
  });

  // 진입차수(in-degree) 계산
  const inDegree: Record<string, number> = {};
  nodeIds.forEach(id => inDegree[id] = 0);
  topology.links.forEach(link => {
    inDegree[link.target] = (inDegree[link.target] || 0) + 1;
  });

  // 위상 정렬 (Topological Sort)을 통한 계층(layer) 계산
  const layers: string[][] = [];
  const visited = new Set<string>();
  const remaining = [...nodeIds];

  // 반복적으로 진입차수가 0인 노드들을 찾아 레이어에 배치
  while (remaining.length > 0) {
    // 진입차수가 0이거나, 방문되지 않은 노드들 중 가장 적게 참조되는 것들 선택
    const currentLayer = remaining.filter(id => {
      const incomingLinks = topology.links.filter(l => l.target === id && visited.has(l.source));
      return incomingLinks.length === 0 || visited.size === 0;
    });

    if (currentLayer.length === 0 && remaining.length > 0) {
      // 사이클이 있거나 모든 노드가 연결되지 않은 경우
      currentLayer.push(remaining[0]);
    }

    layers.push(currentLayer);
    currentLayer.forEach(id => {
      visited.add(id);
      const idx = remaining.indexOf(id);
      if (idx > -1) remaining.splice(idx, 1);
    });
  }

  // 노드 위치 계산
  const svgWidth = 800;
  const svgHeight = 500;
  const margin = { top: 40, bottom: 40, left: 40, right: 40 };
  const availableHeight = svgHeight - margin.top - margin.bottom;

  layers.forEach((layer, layerIndex) => {
    const y = margin.top + (availableHeight / (layers.length + 1)) * (layerIndex + 1);
    const availableWidth = svgWidth - margin.left - margin.right;
    const step = availableWidth / (layer.length + 1);

    layer.forEach((nodeId, nodeIndex) => {
      positions[nodeId] = {
        x: margin.left + step * (nodeIndex + 1),
        y,
      };
    });
  });

  return positions;
}

// 유틸리티 함수: 노드 타입 아이콘
function getTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    server: "🖥️",
    service: "⚡",
    db: "🗄️",
    network: "🌐",
    storage: "💾",
  };
  return icons[type] || "📦";
}
