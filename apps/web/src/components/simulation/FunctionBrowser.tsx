"use client";

import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";

type FunctionCategory = "rule" | "statistical" | "ml" | "domain";
type FunctionComplexity = "basic" | "intermediate" | "advanced";

interface FunctionParameter {
  name: string;
  type: string;
  default: number | string | boolean | any[];
  min?: number;
  max?: number;
  step?: number;
  description: string;
  unit: string;
  required: boolean;
}

interface FunctionOutput {
  name: string;
  unit: string;
  description: string;
}

interface FunctionMetadata {
  id: string;
  name: string;
  category: FunctionCategory;
  complexity: FunctionComplexity;
  description: string;
  confidence: number;
  tags: string[];
  assumptions: string[];
  references: string[];
  version: string;
  parameter_count: number;
  output_count: number;
  parameters?: FunctionParameter[];
  outputs?: FunctionOutput[];
}

interface Envelope<T> {
  data?: T;
  message?: string;
  detail?: string;
}

interface FunctionBrowserProps {
  onSelectFunction?: (functionId: string) => void;
  selectedFunctionId?: string | null;
}

export default function FunctionBrowser({ onSelectFunction, selectedFunctionId }: FunctionBrowserProps) {
  const [functions, setFunctions] = useState<FunctionMetadata[]>([]);
  const [filtered, setFiltered] = useState<FunctionMetadata[]>([]);
  const [selectedFunction, setSelectedFunction] = useState<FunctionMetadata | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [complexityFilter, setComplexityFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Available filter options
  const categories: { value: string; label: string }[] = [
    { value: "", label: "All Categories" },
    { value: "rule", label: "Rule" },
    { value: "statistical", label: "Statistical" },
    { value: "ml", label: "Machine Learning" },
    { value: "domain", label: "Domain" },
  ];

  const complexities: { value: string; label: string }[] = [
    { value: "", label: "All Levels" },
    { value: "basic", label: "Basic" },
    { value: "intermediate", label: "Intermediate" },
    { value: "advanced", label: "Advanced" },
  ];

  useEffect(() => {
    loadFunctions();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [functions, categoryFilter, complexityFilter, searchQuery]);

  useEffect(() => {
    if (selectedFunctionId) {
      loadFunctionDetail(selectedFunctionId);
    }
  }, [selectedFunctionId]);

  const loadFunctions = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (categoryFilter) params.set("category", categoryFilter);
      if (complexityFilter) params.set("complexity", complexityFilter);
      if (searchQuery) params.set("search", searchQuery);

      const response = await authenticatedFetch<Envelope<{ functions: FunctionMetadata[] }>>(
        `/api/sim/functions${params.toString() ? `?${params.toString()}` : ""}`
      );

      if (response.data?.functions) {
        setFunctions(response.data.functions);
      }
    } catch (err) {
      console.error("Failed to load functions", err);
      setStatusMessage("Failed to load function library");
    } finally {
      setLoading(false);
    }
  };

  const loadFunctionDetail = async (functionId: string) => {
    try {
      const response = await authenticatedFetch<Envelope<{ id: string } & Omit<FunctionMetadata, "parameter_count" | "output_count">>>(
        `/api/sim/functions/${functionId}`
      );

      if (response.data) {
        setSelectedFunction(response.data as FunctionMetadata);
      }
    } catch (err) {
      console.error("Failed to load function detail", err);
    }
  };

  const applyFilters = () => {
    let result = [...functions];

    if (categoryFilter) {
      result = result.filter(f => f.category === categoryFilter);
    }
    if (complexityFilter) {
      result = result.filter(f => f.complexity === complexityFilter);
    }
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(f =>
        f.name.toLowerCase().includes(query) ||
        f.description.toLowerCase().includes(query) ||
        f.id.toLowerCase().includes(query) ||
        f.tags.some(t => t.toLowerCase().includes(query))
      );
    }

    setFiltered(result);
  };

  const handleFunctionClick = (func: FunctionMetadata) => {
    setSelectedFunction(func);
    if (onSelectFunction) {
      onSelectFunction(func.id);
    }
  };

  const getCategoryColor = (category: FunctionCategory) => {
    switch (category) {
      case "rule": return "text-emerald-400";
      case "statistical": return "text-sky-400";
      case "ml": return "text-purple-400";
      case "domain": return "text-amber-400";
      default: return "text-[var(--muted-foreground)]";
    }
  };

  const getComplexityBadge = (complexity: FunctionComplexity) => {
    switch (complexity) {
      case "basic": return "bg-emerald-500/20 text-emerald-300";
      case "intermediate": return "bg-sky-500/20 text-sky-300";
      case "advanced": return "bg-purple-500/20 text-purple-300";
      default: return "bg-[var(--muted-background)] text-[var(--foreground-secondary)]";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <section className="rounded-3xl border  /70 p-6" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
        <h1 className="text-2xl font-semibold text-white">Simulation Function Library</h1>
        <p className="mt-2 text-sm " style={{color: "var(--foreground-secondary)"}}>
          Browse and select simulation functions organized by category and complexity.
        </p>
      </section>

      {/* Filters */}
      <section className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <aside className="space-y-4 rounded-3xl border   p-5" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
          <h2 className="text-sm font-semibold uppercase tracking-[0.25em] " style={{color: "var(--foreground-secondary)"}}>Filters</h2>

          {/* Search */}
          <label className="block text-xs uppercase tracking-[0.2em] " style={{color: "var(--muted-foreground)"}}>
            Search
            <input
              type="text"
              className="mt-2 w-full rounded-xl border   px-3 py-2 text-sm text-white outline-none focus:border-sky-500" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
              placeholder="Name, description, tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </label>

          {/* Category Filter */}
          <label className="block text-xs uppercase tracking-[0.2em] " style={{color: "var(--muted-foreground)"}}>
            Category
            <select
              className="mt-2 w-full rounded-xl border   px-3 py-2 text-sm text-white" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              {categories.map(cat => (
                <option key={cat.value} value={cat.value}>{cat.label}</option>
              ))}
            </select>
          </label>

          {/* Complexity Filter */}
          <label className="block text-xs uppercase tracking-[0.2em] " style={{color: "var(--muted-foreground)"}}>
            Complexity
            <select
              className="mt-2 w-full rounded-xl border   px-3 py-2 text-sm text-white" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}
              value={complexityFilter}
              onChange={(e) => setComplexityFilter(e.target.value)}
            >
              {complexities.map(comp => (
                <option key={comp.value} value={comp.value}>{comp.label}</option>
              ))}
            </select>
          </label>

          {/* Stats */}
          <div className="rounded-xl border  /50 p-3" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
            <p className="text-xs " style={{color: "var(--muted-foreground)"}}>Showing {filtered.length} of {functions.length} functions</p>
          </div>
        </aside>

        {/* Function List */}
        <main className="space-y-4">
          {loading ? (
            <div className="flex items-center justify-center p-12 " style={{color: "var(--muted-foreground)"}}>
              Loading function library...
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex items-center justify-center p-12 " style={{color: "var(--muted-foreground)"}}>
              No functions match your filters
            </div>
          ) : (
            <div className="grid gap-3">
              {filtered.map((func) => (
                <button
                  key={func.id}
                  onClick={() => handleFunctionClick(func)}
                  className={`rounded-2xl border p-4 text-left transition ${
                    selectedFunction?.id === func.id
                      ? "border-sky-500 bg-sky-500/10"
                      : "  hover:"
                  }`} style={{backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)"}}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className={`font-semibold ${getCategoryColor(func.category)}`}>
                          {func.name}
                        </h3>
                        <span className={`text-[10px] uppercase tracking-[0.15em] px-2 py-0.5 rounded ${getComplexityBadge(func.complexity)}`}>
                          {func.complexity}
                        </span>
                      </div>
                      <p className="mt-1 text-sm " style={{color: "var(--muted-foreground)"}}>{func.description}</p>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {func.tags.slice(0, 3).map((tag) => (
                          <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded  " style={{color: "var(--muted-foreground)", backgroundColor: "var(--surface-elevated)"}}>
                            {tag}
                          </span>
                        ))}
                        {func.tags.length > 3 && (
                          <span className="text-[10px] " style={{color: "var(--muted-foreground)"}}>+{func.tags.length - 3} more</span>
                        )}
                      </div>
                    </div>
                    <div className="ml-4 text-right">
                      <p className="text-xs " style={{color: "var(--muted-foreground)"}}>Confidence</p>
                      <p className="text-lg font-semibold text-white">{(func.confidence * 100).toFixed(0)}%</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </main>
      </section>

      {/* Function Detail Panel */}
      {selectedFunction && (
        <section className="rounded-3xl border   p-6" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-semibold text-white">{selectedFunction.name}</h2>
                <span className={`text-xs uppercase tracking-[0.2em] px-2 py-1 rounded ${getComplexityBadge(selectedFunction.complexity)}`}>
                  {selectedFunction.complexity}
                </span>
                <span className={`text-xs uppercase tracking-[0.2em] ${getCategoryColor(selectedFunction.category)}`}>
                  {selectedFunction.category}
                </span>
              </div>
              <p className="mt-2 text-sm " style={{color: "var(--foreground-secondary)"}}>{selectedFunction.description}</p>
              <p className="mt-1 text-xs " style={{color: "var(--muted-foreground)"}}>ID: {selectedFunction.id}</p>
            </div>
            <div className="ml-6 text-right">
              <p className="text-xs " style={{color: "var(--muted-foreground)"}}>Confidence</p>
              <p className="text-2xl font-semibold text-emerald-400">{(selectedFunction.confidence * 100).toFixed(0)}%</p>
            </div>
          </div>

          {/* Parameters */}
          {selectedFunction.parameters && selectedFunction.parameters.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold uppercase tracking-[0.25em] " style={{color: "var(--foreground-secondary)"}}>Parameters</h3>
              <div className="mt-3 grid gap-2">
                {selectedFunction.parameters.map((param) => (
                  <div key={param.name} className="rounded-xl border  /50 p-3" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium text-white">{param.name}</p>
                        <p className="text-xs " style={{color: "var(--muted-foreground)"}}>{param.description}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-xs " style={{color: "var(--muted-foreground)"}}>{param.type}</p>
                        {param.unit && <p className="text-xs " style={{color: "var(--muted-foreground)"}}>{param.unit}</p>}
                      </div>
                    </div>
                    <div className="mt-2 flex items-center gap-4 text-xs " style={{color: "var(--muted-foreground)"}}>
                      {param.min !== undefined && <span>Min: {param.min}</span>}
                      {param.max !== undefined && <span>Max: {param.max}</span>}
                      {param.step !== undefined && <span>Step: {param.step}</span>}
                      <span>Default: {String(param.default)}</span>
                      {param.required && <span className="text-rose-400">Required</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Outputs */}
          {selectedFunction.outputs && selectedFunction.outputs.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold uppercase tracking-[0.25em] " style={{color: "var(--foreground-secondary)"}}>Outputs</h3>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {selectedFunction.outputs.map((output) => (
                  <div key={output.name} className="rounded-xl border  /50 p-3" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-base)"}}>
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-white">{output.name}</p>
                      <span className="text-xs " style={{color: "var(--muted-foreground)"}}>{output.unit}</span>
                    </div>
                    <p className="mt-1 text-xs " style={{color: "var(--muted-foreground)"}}>{output.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-[0.25em] " style={{color: "var(--foreground-secondary)"}}>Assumptions</h3>
              <ul className="mt-2 space-y-1">
                {selectedFunction.assumptions.map((assumption, idx) => (
                  <li key={idx} className="text-xs " style={{color: "var(--muted-foreground)"}}>• {assumption}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-[0.25em] " style={{color: "var(--foreground-secondary)"}}>References</h3>
              <ul className="mt-2 space-y-1">
                {selectedFunction.references.map((ref, idx) => (
                  <li key={idx} className="text-xs  truncate" style={{color: "var(--muted-foreground)"}}>{ref}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-[0.25em] " style={{color: "var(--foreground-secondary)"}}>Version</h3>
              <p className="mt-2 text-xs " style={{color: "var(--muted-foreground)"}}>{selectedFunction.version}</p>
            </div>
          </div>
        </section>
      )}

      {statusMessage && (
        <div className="rounded-2xl border border-amber-700/40 bg-amber-950/20 p-4">
          <p className="text-sm text-amber-300">{statusMessage}</p>
        </div>
      )}
    </div>
  );
}
