/**
 * HTTP Logic Form Builder
 * Provides structured form inputs for HTTP specification
 * Supports method, URL, headers, body, and query parameters
 */

import { useState } from "react";
import FormSection from "./FormSection";
import FormFieldGroup from "./FormFieldGroup";

export interface HttpSpec {
  url: string;
  method: "GET" | "POST" | "PUT" | "DELETE";
  headers: string;
  body: string;
  params: string;
}

interface HeaderEntry {
  key: string;
  value: string;
}

interface ParamEntry {
  key: string;
  value: string;
}

interface HttpFormBuilderProps {
  value: HttpSpec;
  onChange: (spec: HttpSpec) => void;
  isReadOnly?: boolean;
}

export default function HttpFormBuilder({
  value,
  onChange,
  isReadOnly = false,
}: HttpFormBuilderProps) {
  const [viewMode, setViewMode] = useState<"form" | "json">("form");
  const [headerEntries, setHeaderEntries] = useState<HeaderEntry[]>(() => {
    try {
      const parsed = JSON.parse(value.headers || "{}");
      return Object.entries(parsed).map(([key, val]) => ({
        key,
        value: String(val),
      }));
    } catch {
      return [];
    }
  });

  const [paramEntries, setParamEntries] = useState<ParamEntry[]>(() => {
    try {
      const parsed = JSON.parse(value.params || "{}");
      return Object.entries(parsed).map(([key, val]) => ({
        key,
        value: String(val),
      }));
    } catch {
      return [];
    }
  });

  const handleHeaderChange = (index: number, key: "key" | "value", val: string) => {
    const updated = [...headerEntries];
    updated[index] = { ...updated[index], [key]: val };
    setHeaderEntries(updated);

    const headersObj = updated.reduce(
      (acc, { key, value }) => {
        if (key) acc[key] = value;
        return acc;
      },
      {} as Record<string, string>
    );
    onChange({ ...value, headers: JSON.stringify(headersObj, null, 2) });
  };

  const handleParamChange = (index: number, key: "key" | "value", val: string) => {
    const updated = [...paramEntries];
    updated[index] = { ...updated[index], [key]: val };
    setParamEntries(updated);

    const paramsObj = updated.reduce(
      (acc, { key, value }) => {
        if (key) acc[key] = value;
        return acc;
      },
      {} as Record<string, string>
    );
    onChange({ ...value, params: JSON.stringify(paramsObj, null, 2) });
  };

  const addHeader = () => {
    setHeaderEntries([...headerEntries, { key: "", value: "" }]);
  };

  const removeHeader = (index: number) => {
    const updated = headerEntries.filter((_, i) => i !== index);
    setHeaderEntries(updated);

    const headersObj = updated.reduce(
      (acc, { key, value }) => {
        if (key) acc[key] = value;
        return acc;
      },
      {} as Record<string, string>
    );
    onChange({ ...value, headers: JSON.stringify(headersObj, null, 2) });
  };

  const addParam = () => {
    setParamEntries([...paramEntries, { key: "", value: "" }]);
  };

  const removeParam = (index: number) => {
    const updated = paramEntries.filter((_, i) => i !== index);
    setParamEntries(updated);

    const paramsObj = updated.reduce(
      (acc, { key, value }) => {
        if (key) acc[key] = value;
        return acc;
      },
      {} as Record<string, string>
    );
    onChange({ ...value, params: JSON.stringify(paramsObj, null, 2) });
  };

  return (
    <div className="space-y-4">
      {/* Mode Toggle */}
      <div className="flex items-center gap-2 border-b pb-3" style={{ borderColor: "var(--border-muted)" }}>
        <button
          onClick={() => setViewMode("form")}
          className={`px-3 py-1 rounded-md text-xs font-medium transition ${
            viewMode === "form"
              ? "bg-sky-500/20 text-sky-300 border border-sky-500/50"
              : ""
          }`}
          style={viewMode !== "form" ? { color: "var(--muted-foreground)" } : undefined}
          disabled={isReadOnly}
        >
          Form Builder
        </button>
        <button
          onClick={() => setViewMode("json")}
          className={`px-3 py-1 rounded-md text-xs font-medium transition ${
            viewMode === "json"
              ? "bg-sky-500/20 text-sky-300 border border-sky-500/50"
              : ""
          }`}
          disabled={isReadOnly}
        >
          JSON View
        </button>
      </div>

      {viewMode === "form" ? (
        <div className="space-y-4">
          {/* Method & URL */}
          <FormSection title="Basic Configuration" columns={2}>
            <FormFieldGroup label="HTTP Method" required>
              <select
                value={value.method}
                onChange={(e) => onChange({ ...value, method: e.target.value as any })}
                disabled={isReadOnly}
                className="w-full rounded-xl border px-3 py-2 text-sm outline-none focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-elevated)", color: "var(--foreground)" }}
              >
                <option value="GET">GET</option>
                <option value="POST">POST</option>
                <option value="PUT">PUT</option>
                <option value="DELETE">DELETE</option>
              </select>
            </FormFieldGroup>

            <FormFieldGroup label="URL" required>
              <input
                type="url"
                value={value.url}
                onChange={(e) => onChange({ ...value, url: e.target.value })}
                disabled={isReadOnly}
                className="w-full rounded-xl border px-3 py-2 text-sm outline-none focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-elevated)", color: "var(--foreground)" }}
                placeholder="https://api.example.com/endpoint"
              />
            </FormFieldGroup>
          </FormSection>

          {/* Headers */}
          <FormSection
            title="HTTP Headers"
            description="Add custom headers for the request"
          >
            <div className="space-y-2 col-span-full">
              {headerEntries.map((entry, idx) => (
                <div key={idx} className="flex gap-2 items-end">
                  <input
                    type="text"
                    value={entry.key}
                    onChange={(e) => handleHeaderChange(idx, "key", e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Header name (e.g., Authorization)"
                    className="flex-1 rounded-lg border px-3 py-2 text-xs outline-none focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-elevated)", color: "var(--foreground)" }}
                  />
                  <input
                    type="text"
                    value={entry.value}
                    onChange={(e) => handleHeaderChange(idx, "value", e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Header value"
                    className="flex-1 rounded-lg border px-3 py-2 text-xs outline-none focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-elevated)", color: "var(--foreground)" }}
                  />
                  {!isReadOnly && (
                    <button
                      onClick={() => removeHeader(idx)}
                      className="px-2 py-2 rounded-lg text-red-400 hover:bg-red-500/10 transition text-xs font-medium"
                    >
                      Remove
                    </button>
                  )}
                </div>
              ))}
              {!isReadOnly && (
                <button
                  onClick={addHeader}
                  className="text-xs text-sky-400 hover:text-sky-300 font-medium mt-2"
                >
                  + Add Header
                </button>
              )}
            </div>
          </FormSection>

          {/* Query Parameters */}
          <FormSection
            title="Query Parameters"
            description="Add URL query parameters"
          >
            <div className="space-y-2 col-span-full">
              {paramEntries.map((entry, idx) => (
                <div key={idx} className="flex gap-2 items-end">
                  <input
                    type="text"
                    value={entry.key}
                    onChange={(e) => handleParamChange(idx, "key", e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Parameter name"
                    className="flex-1 rounded-lg border px-3 py-2 text-xs outline-none focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-elevated)", color: "var(--foreground)" }}
                  />
                  <input
                    type="text"
                    value={entry.value}
                    onChange={(e) => handleParamChange(idx, "value", e.target.value)}
                    disabled={isReadOnly}
                    placeholder="Parameter value"
                    className="flex-1 rounded-lg border px-3 py-2 text-xs outline-none focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-elevated)", color: "var(--foreground)" }}
                  />
                  {!isReadOnly && (
                    <button
                      onClick={() => removeParam(idx)}
                      className="px-2 py-2 rounded-lg text-red-400 hover:bg-red-500/10 transition text-xs font-medium"
                    >
                      Remove
                    </button>
                  )}
                </div>
              ))}
              {!isReadOnly && (
                <button
                  onClick={addParam}
                  className="text-xs text-sky-400 hover:text-sky-300 font-medium mt-2"
                >
                  + Add Parameter
                </button>
              )}
            </div>
          </FormSection>

          {/* Request Body */}
          {(value.method === "POST" || value.method === "PUT") && (
            <FormSection title="Request Body">
              <div className="col-span-full">
                <FormFieldGroup label="Body (JSON)">
                  <textarea
                    value={value.body}
                    onChange={(e) => onChange({ ...value, body: e.target.value })}
                    disabled={isReadOnly}
                    className="w-full h-32 rounded-lg border px-3 py-2 font-mono text-xs outline-none focus:border-sky-500 custom-scrollbar disabled:cursor-not-allowed disabled:opacity-60" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-elevated)", color: "var(--foreground)" }}
                    placeholder='{"key": "value"}'
                  />
                </FormFieldGroup>
              </div>
            </FormSection>
          )}
        </div>
      ) : (
        /* JSON View */
        <div className="space-y-3">
          <div>
            <label className="text-xs uppercase tracking-normal" style={{ color: "var(--muted-foreground)" }}>
              Full HTTP Specification (JSON)
            </label>
            <textarea
              value={JSON.stringify(
                {
                  method: value.method,
                  url: value.url,
                  headers: JSON.parse(value.headers || "{}"),
                  params: JSON.parse(value.params || "{}"),
                  body: value.body ? JSON.parse(value.body) : null,
                },
                null,
                2
              )}
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  onChange({
                    ...value,
                    method: parsed.method || value.method,
                    url: parsed.url || value.url,
                    headers: JSON.stringify(parsed.headers || {}),
                    params: JSON.stringify(parsed.params || {}),
                    body: JSON.stringify(parsed.body || {}),
                  });
                } catch {
                  // Ignore parse errors while typing
                }
              }}
              disabled={isReadOnly}
              className="w-full h-64 rounded-lg border px-3 py-2 font-mono text-xs outline-none focus:border-sky-500 custom-scrollbar disabled:cursor-not-allowed disabled:opacity-60" style={{ border: "1px solid var(--border-muted)", backgroundColor: "var(--surface-elevated)", color: "var(--foreground)" }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
