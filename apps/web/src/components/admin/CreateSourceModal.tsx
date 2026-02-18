"use client";

import { useState } from "react";

import { fetchApi } from "@/lib/adminUtils";

interface CreateSourceModalProps {
  onClose: () => void;
  onSave: () => void;
}

type SourceType =
  | "postgresql"
  | "mysql"
  | "bigquery"
  | "snowflake"
  | "mongodb"
  | "neo4j"
  | "redis"
  | "kafka"
  | "s3"
  | "rest_api"
  | "graphql_api";

export default function CreateSourceModal({ onClose, onSave }: CreateSourceModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("postgresql");
  const [host, setHost] = useState("");
  const [port, setPort] = useState("5432");
  const [username, setUsername] = useState("");
  const [database, setDatabase] = useState("");
  const [secretKeyRef, setSecretKeyRef] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError("Source name is required");
      return;
    }

    setLoading(true);
    setError("");
    try {
      await fetchApi("/asset-registry/sources", {
        method: "POST",
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          source_type: sourceType,
          connection: {
            host: host.trim() || null,
            port: Number.isFinite(Number(port)) ? Number(port) : 5432,
            username: username.trim() || null,
            database: database.trim() || null,
            secret_key_ref: secretKeyRef.trim() || null,
          },
          tags: {},
        }),
      });
      onSave();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create source");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-lg overflow-hidden rounded-2xl border border-variant bg-surface-base shadow-2xl">
        <div className="border-b border-variant p-6">
          <h2 className="mb-1 text-xl font-bold text-foreground">Create Source</h2>
          <p className="text-xs text-muted-foreground">Create a database connection source asset</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          <div>
            <label className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Name *
            </label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={loading}
              className="w-full rounded-xl border border-variant bg-surface-base px-4 py-3 text-foreground transition-all focus:border-sky-500/50 focus:outline-none disabled:opacity-50"
              placeholder="e.g., primary_postgres"
            />
          </div>

          <div>
            <label className="mb-2 ml-1 block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Source Type *
            </label>
            <select
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value as SourceType)}
              disabled={loading}
              className="w-full rounded-xl border border-variant bg-surface-base px-4 py-3 text-foreground transition-all focus:border-sky-500/50 focus:outline-none disabled:opacity-50"
            >
              <option value="postgresql">postgresql</option>
              <option value="mysql">mysql</option>
              <option value="neo4j">neo4j</option>
              <option value="mongodb">mongodb</option>
              <option value="redis">redis</option>
              <option value="bigquery">bigquery</option>
              <option value="snowflake">snowflake</option>
              <option value="kafka">kafka</option>
              <option value="s3">s3</option>
              <option value="rest_api">rest_api</option>
              <option value="graphql_api">graphql_api</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <input
              value={host}
              onChange={(e) => setHost(e.target.value)}
              disabled={loading}
              className="rounded-xl border border-variant bg-surface-base px-4 py-3 text-foreground transition-all focus:border-sky-500/50 focus:outline-none disabled:opacity-50"
              placeholder="Host"
            />
            <input
              value={port}
              onChange={(e) => setPort(e.target.value)}
              disabled={loading}
              className="rounded-xl border border-variant bg-surface-base px-4 py-3 text-foreground transition-all focus:border-sky-500/50 focus:outline-none disabled:opacity-50"
              placeholder="Port"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              disabled={loading}
              className="rounded-xl border border-variant bg-surface-base px-4 py-3 text-foreground transition-all focus:border-sky-500/50 focus:outline-none disabled:opacity-50"
              placeholder="Username"
            />
            <input
              value={database}
              onChange={(e) => setDatabase(e.target.value)}
              disabled={loading}
              className="rounded-xl border border-variant bg-surface-base px-4 py-3 text-foreground transition-all focus:border-sky-500/50 focus:outline-none disabled:opacity-50"
              placeholder="Database"
            />
          </div>

          <div>
            <input
              value={secretKeyRef}
              onChange={(e) => setSecretKeyRef(e.target.value)}
              disabled={loading}
              className="w-full rounded-xl border border-variant bg-surface-base px-4 py-3 text-foreground transition-all focus:border-sky-500/50 focus:outline-none disabled:opacity-50"
              placeholder="Secret Ref (e.g., env:PG_PASSWORD)"
            />
          </div>

          <div>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={loading}
              className="w-full resize-none rounded-xl border border-variant bg-surface-base px-4 py-3 text-foreground transition-all focus:border-sky-500/50 focus:outline-none disabled:opacity-50"
              placeholder="Description"
              rows={2}
            />
          </div>

          {error ? (
            <div className="rounded-lg border border-red-800/50 bg-red-900/20 p-3 text-sm text-red-300">
              {error}
            </div>
          ) : null}

          <div className="flex gap-3 border-t border-variant pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 rounded-xl px-4 py-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground transition-colors hover:bg-surface-elevated hover:text-foreground disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-xl bg-sky-600 px-4 py-3 text-sm font-semibold uppercase tracking-wide text-white shadow-lg shadow-sky-900/20 transition-all hover:bg-sky-500 disabled:opacity-50"
            >
              {loading ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
