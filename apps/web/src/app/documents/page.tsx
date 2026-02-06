"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient/index";
import { useAuth } from "@/contexts/AuthContext";

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

type ChunkType = "answer" | "summary" | "detail" | "done" | "error";

interface StreamChunk {
  type: ChunkType;
  text: string;
  meta?: {
    document_id: string;
    chunks: { chunk_id: string; page: number | null }[];
  };
}

interface Reference {
  document_id: string;
  document_title: string;
  chunk_id: string;
  page: number | null;
  snippet: string;
  score?: number;
}

interface DocsHistoryEntry {
  id: string;
  createdAt: string;
  question: string;
  summary: string;
  answer: string;
  status: "ok" | "error";
  documentId: string;
  documentTitle?: string;
  references: Reference[];
}

interface DocsServerHistoryEntry {
  id: string;
  feature: string;
  question: string;
  summary: string | null;
  status: "ok" | "error";
  response: { answer?: string } | null;
  metadata: {
    documentId?: string;
    document_id?: string;
    documentTitle?: string;
    document_title?: string;
    references?: Reference[];
  } | null;
  created_at: string;
}

interface DocumentHistoryPayload {
  question: string;
  answer: string;
  summary: string;
  status: "ok" | "error";
  documentId: string;
  documentTitle?: string;
  references: Reference[];
  topK: number;
  errorDetails?: string;
}

interface DocumentPageState {
  selectedDocumentId?: string | null;
  references?: Reference[];
}

const generateLocalHistoryId = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

const summarizeDocAnswer = (answer: string, question: string) => {
  const trimmed = answer.trim();
  if (!trimmed) {
    return question || "(no summary)";
  }
  const firstLine = trimmed.split("\n")[0];
  return firstLine.length > 120 ? `${firstLine.slice(0, 120)}…` : firstLine;
};

const buildDocHistoryEntry = (raw: DocsServerHistoryEntry): DocsHistoryEntry | null => {
  const metadata = raw.metadata ?? {};
  const documentId = (metadata.documentId ?? metadata.document_id) as string | undefined;
  if (!documentId) {
    return null;
  }
  const answer = raw.response?.answer ?? "";
  return {
    id: raw.id,
    createdAt: raw.created_at,
    question: raw.question,
    summary: raw.summary ?? summarizeDocAnswer(answer, raw.question),
    answer,
    status: raw.status,
    documentId,
    documentTitle: (metadata.documentTitle ?? metadata.document_title) as string | undefined,
    references: (metadata.references ?? []) as Reference[],
  };
};

const STORAGE_KEY = "codex-document-page-state";
const DOCUMENT_HISTORY_LIMIT = 40;

type DocumentStatus = "queued" | "processing" | "done" | "failed";

interface DocumentItem {
  id: string;
  tenant_id: string;
  user_id: string;
  filename: string;
  content_type: string;
  size: number;
  status: DocumentStatus;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

interface DocumentDetail extends DocumentItem {
  deleted_at: string | null;
  chunk_count: number;
}

const badgeStyles: Record<DocumentStatus, string> = {
  queued: "bg-amber-400/10 text-amber-200 border-amber-500/40",
  processing: "bg-sky-500/10 text-sky-300 border-sky-500/60",
  done: "bg-emerald-500/10 text-emerald-200 border-emerald-500/60",
  failed: "bg-rose-500/10 text-rose-200 border-rose-500/60",
};


const formatTimestamp = (value: string) => {
  try {
    let dateStr = value;
    if (value && value.includes("T") && !value.endsWith("Z") && !/[+-]\d{2}:?\d{2}$/.test(value)) {
      dateStr = `${value}Z`;
    }
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return date.toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
  } catch {
    return value;
  }
};

export default function DocumentsPage() {
  const { isLoading: authLoading, user } = useAuth();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const streamAbortController = useRef<AbortController | null>(null);

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<DocumentDetail | null>(null);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  const [queryValue, setQueryValue] = useState("");
  const [topK, setTopK] = useState(3);
  const [streamChunks, setStreamChunks] = useState<StreamChunk[]>([]);
  const [streamStatus, setStreamStatus] = useState<"idle" | "streaming" | "error">("idle");
  const [streamError, setStreamError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [references, setReferences] = useState<Reference[]>([]);
  const [restoredStateApplied, setRestoredStateApplied] = useState(false);
  const persistedStateRef = useRef<DocumentPageState | null>(null);
  const [docHistory, setDocHistory] = useState<DocsHistoryEntry[]>([]);
  const [selectedDocHistoryId, setSelectedDocHistoryId] = useState<string | null>(null);
  const [docHistoryLoading, setDocHistoryLoading] = useState(false);
  const [docHistoryError, setDocHistoryError] = useState<string | null>(null);

  const selectedDocumentRef = useRef<DocumentDetail | null>(null);

  useEffect(() => {
    selectedDocumentRef.current = selectedDocument;
  }, [selectedDocument]);

  const addDocHistoryEntry = useCallback((entry: DocsHistoryEntry) => {
    setDocHistory((prev) => {
      const next = [entry, ...prev];
      if (next.length > DOCUMENT_HISTORY_LIMIT) {
        return next.slice(0, DOCUMENT_HISTORY_LIMIT);
      }
      return next;
    });
    setSelectedDocHistoryId(entry.id);
  }, []);

  const persistDocHistory = useCallback(
    async (payload: DocumentHistoryPayload) => {
      if (!payload.documentId || !payload.question) {
        return;
      }
      try {
        await authenticatedFetch("/history/", {
          method: "POST",
          body: JSON.stringify({
            feature: "docs",
            question: payload.question,
            summary: payload.summary,
            status: payload.status,
            response: {
              answer: payload.answer,
            },
            metadata: {
              documentId: payload.documentId,
              documentTitle: payload.documentTitle,
              references: payload.references,
              topK: payload.topK,
              errorDetails: payload.errorDetails,
            },
          }),
        });
      } catch (error) {
        console.error("Failed to persist document history", error);
      }
    },
    []
  );

  const fetchDocHistory = useCallback(async () => {
    setDocHistoryLoading(true);
    setDocHistoryError(null);
    try {
      const payload = await authenticatedFetch(
        `/history/?feature=docs&limit=${DOCUMENT_HISTORY_LIMIT}`
      ) as { data: { history: DocsServerHistoryEntry[] } };
      const rawHistory = (payload?.data?.history ?? []) as DocsServerHistoryEntry[];
      const hydrated = rawHistory
        .map(buildDocHistoryEntry)
        .filter((entry): entry is DocsHistoryEntry => Boolean(entry));
      setDocHistory(hydrated);
    } catch (error: unknown) {
      console.error("Failed to load document history", error);
      setDocHistoryError(error instanceof Error ? error.message : "Failed to load document history");
    } finally {
      setDocHistoryLoading(false);
    }
  }, []);

  const fetchDocumentDetail = useCallback(
    async (documentId: string) => {
      const payload = await authenticatedFetch(`/api/documents/${documentId}`) as { data?: { document: DocumentDetail } };
      setSelectedDocument(payload?.data?.document || null);
    },
    []
  );

  const fetchDocuments = useCallback(async () => {
    setLoadingDocuments(true);
    setDocumentsError(null);
    try {
      // Backend has /api/documents/ endpoint
      const payload = await authenticatedFetch("/api/documents/") as { data?: { documents: DocumentItem[] } };
      // Handle ResponseEnvelope format
      const docs = payload?.data?.documents ?? [];
      setDocuments(docs);
      const selectedId = selectedDocumentRef.current?.id;
      if (selectedId) {
        try {
          await fetchDocumentDetail(selectedId);
        } catch (error: unknown) {
          console.error("Failed to refresh selected document", error);
        }
      }
    } catch (error: unknown) {
      setDocumentsError(error instanceof Error ? error.message : "Failed to load documents");
    } finally {
      setLoadingDocuments(false);
    }
  }, [fetchDocumentDetail]);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    fetchDocuments();
  }, [authLoading, fetchDocuments, user?.id]);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    fetchDocHistory();
  }, [authLoading, fetchDocHistory, user?.id]);

  const selectDocument = useCallback(
    (documentId: string) => {
      if (selectedDocument?.id === documentId) {
        return;
      }
      setSelectedDocument(null);
      fetchDocumentDetail(documentId).catch(console.error);
      setReferences([]);
      setStreamChunks([]);
      setStreamStatus("idle");
      streamAbortController.current?.abort();
    },
    [fetchDocumentDetail, selectedDocument]
  );

  const documentHistoryEntries = useMemo(() => {
    if (!selectedDocument) {
      return [];
    }
    return docHistory.filter((entry) => entry.documentId === selectedDocument.id);
  }, [docHistory, selectedDocument]);

  useEffect(() => {
    if (docHistory.length === 0 || documents.length === 0) {
      return;
    }
    if (selectedDocument && documentHistoryEntries.length > 0) {
      return;
    }
    const recentHistory = docHistory
      .slice()
      .sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())[0];
    if (!recentHistory) {
      return;
    }
    const targetDoc = documents.find((doc) => doc.id === recentHistory.documentId);
    if (!targetDoc) {
      return;
    }
    selectDocument(targetDoc.id);
  }, [docHistory, documents, selectedDocument, documentHistoryEntries.length, selectDocument]);

  useEffect(() => {
    if (documentHistoryEntries.length === 0) {
      setSelectedDocHistoryId(null);
      return;
    }
    setSelectedDocHistoryId((prev) =>
      prev && documentHistoryEntries.some((entry) => entry.id === prev)
        ? prev
        : documentHistoryEntries[0].id
    );
  }, [documentHistoryEntries]);

  const selectedDocHistoryEntry = useMemo(() => {
    if (documentHistoryEntries.length === 0) {
      return null;
    }
    return (
      documentHistoryEntries.find((entry) => entry.id === selectedDocHistoryId) ??
      documentHistoryEntries[0]
    );
  }, [documentHistoryEntries, selectedDocHistoryId]);

  const persistDocumentState = useCallback(() => {
    if (typeof window === "undefined") {
      return;
    }
    const payload: DocumentPageState = {
      selectedDocumentId: selectedDocument?.id ?? null,
      references,
    };
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  }, [references, selectedDocument?.id]);

  useEffect(() => {
    if (!restoredStateApplied) {
      return;
    }
    persistDocumentState();
  }, [persistDocumentState, restoredStateApplied]);

  useEffect(() => {
    if (restoredStateApplied || documents.length === 0) {
      return;
    }
    if (typeof window !== "undefined" && !persistedStateRef.current) {
      const raw = window.sessionStorage.getItem(STORAGE_KEY);
      if (raw) {
        try {
          persistedStateRef.current = JSON.parse(raw);
        } catch {
          persistedStateRef.current = null;
        }
      }
    }
    const stored = persistedStateRef.current;
    if (stored?.selectedDocumentId) {
      selectDocument(stored.selectedDocumentId);
    } else if (!selectedDocument) {
      fetchDocumentDetail(documents[0].id).catch(console.error);
    }
    if (stored?.references && stored.references.length > 0) {
      setReferences(stored.references);
    }
    setRestoredStateApplied(true);
  }, [documents, fetchDocumentDetail, restoredStateApplied, selectDocument, selectedDocument]);
  const clearStream = () => {
    streamAbortController.current?.abort();
    streamAbortController.current = null;
    setStreamChunks([]);
    setStreamStatus("idle");
    setReferences([]);
  };

  const mergeChunk = (payload: StreamChunk, previous: StreamChunk[]): StreamChunk[] => {
    if (payload.type === "answer" && previous.length > 0 && previous[previous.length - 1].type === "answer") {
      const last = previous[previous.length - 1];
      const merged = {
        ...last,
        text: last.text + payload.text,
      };
      return [...previous.slice(0, -1), merged];
    }
    return [...previous, payload];
  };

  const startStream = async () => {
    if (!selectedDocument || !queryValue.trim()) {
      return;
    }
    clearStream();
    setStreamStatus("streaming");
    setStreamError(null);
    const controller = new AbortController();
    streamAbortController.current = controller;
    const questionText = queryValue.trim();
    const documentId = selectedDocument.id;
    const documentTitle = selectedDocument.filename;
    let accumulatedAnswer = "";

    try {
      const token = localStorage.getItem("access_token");
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      const url = baseUrl
        ? `${baseUrl}/api/documents/${selectedDocument.id}/query/stream`
        : `/api/documents/${selectedDocument.id}/query/stream`;
      const response = await fetch(url, {
        method: "POST",
        headers: {
          Accept: "text/event-stream",
          "Content-Type": "application/json",
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify({ query: queryValue.trim(), top_k: topK }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const body = await response.text();
        throw new Error(body || "Document stream failed");
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Stream unavailable");
      }

      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split(/\r?\n/);
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data:")) {
            continue;
          }
          const payload = JSON.parse(line.replace(/^data:\s*/, ""));
          if (payload.type === "answer") {
            accumulatedAnswer += payload.text;
          }
          setStreamChunks((prev) => mergeChunk(payload, prev));
          if (payload.type === "done") {
            setStreamStatus("idle");
            const validReferences = (payload.meta?.references ?? []).filter(
              (ref: Reference) => {
                const id = ref.document_id?.trim();
                return Boolean(id && id !== "undefined");
              }
            );
            setReferences(validReferences);
            const finalAnswer = accumulatedAnswer.trim();
            const historySummary = summarizeDocAnswer(finalAnswer, questionText);
            if (documentId) {
              const historyPayload: DocumentHistoryPayload = {
                question: questionText,
                answer: finalAnswer,
                summary: historySummary,
                status: "ok",
                documentId,
                documentTitle,
                references: validReferences,
                topK,
              };
              const localEntry: DocsHistoryEntry = {
                id: generateLocalHistoryId(),
                createdAt: new Date().toISOString(),
                question: historyPayload.question,
                summary: historyPayload.summary,
                answer: historyPayload.answer,
                status: historyPayload.status,
                documentId: historyPayload.documentId,
                documentTitle: historyPayload.documentTitle,
                references: historyPayload.references,
              };
              addDocHistoryEntry(localEntry);
              void persistDocHistory(historyPayload);
            }
          }
          if (payload.type === "error") {
            setStreamStatus("error");
            setStreamError(payload.text);
          }
        }
      }
      setStreamStatus("idle");
    } catch (error: unknown) {
      if (error instanceof Error && error.name === "AbortError") {
        return;
      }
      setStreamStatus("error");
      setStreamError(error instanceof Error ? error.message : "Streaming failed");
      if (documentId) {
        const finalAnswer = accumulatedAnswer.trim();
        const historySummary = summarizeDocAnswer(finalAnswer, questionText);
        const historyPayload: DocumentHistoryPayload = {
          question: questionText,
          answer: finalAnswer,
          summary: historySummary,
          status: "error",
          documentId,
          documentTitle,
          references,
          topK,
          errorDetails: error instanceof Error ? error.message : undefined,
        };
        const localEntry: DocsHistoryEntry = {
          id: generateLocalHistoryId(),
          createdAt: new Date().toISOString(),
          question: historyPayload.question,
          summary: historyPayload.summary,
          answer: historyPayload.answer,
          status: historyPayload.status,
          documentId: historyPayload.documentId,
          documentTitle: historyPayload.documentTitle,
          references: historyPayload.references,
        };
        addDocHistoryEntry(localEntry);
        void persistDocHistory(historyPayload);
      }
    } finally {
      if (streamAbortController.current === controller) {
        streamAbortController.current = null;
      }
    }
  };

  const buildReferenceViewerHref = useCallback(
    (reference: Reference) => {
      const documentId = reference.document_id ?? selectedDocument?.id;
      if (!documentId) {
        return undefined;
      }
      const params = new URLSearchParams();
      if (reference.chunk_id) {
        params.set("chunkId", reference.chunk_id);
      }
      if (reference.page != null) {
        params.set("page", reference.page.toString());
      }
      const query = params.toString();
      return `/documents/${documentId}/viewer${query ? `?${query}` : ""}`;
    },
    [selectedDocument]
  );

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      setUploadError("Please select a file before uploading");
      return;
    }
    setUploadError(null);
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const token = localStorage.getItem("access_token");
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
      const url = baseUrl ? `${baseUrl}/api/documents/upload` : "/api/documents/upload";
      const response = await fetch(url, {
        method: "POST",
        body: formData,
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.message || "Upload failed");
      }
      const payload = await response.json();
      const document = payload.data.document;
      setDocuments((prev) => [document, ...prev.filter((item) => item.id !== document.id)]);
      selectDocument(document.id);
      fileInputRef.current!.value = "";
    } catch (error: unknown) {
      setUploadError(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const deleteDocument = async (documentId: string) => {
    try {
      await authenticatedFetch(`/api/documents/${documentId}`, {
        method: "DELETE",
      });
      setDocuments((prev) => prev.filter((doc) => doc.id !== documentId));
      if (selectedDocument?.id === documentId) {
        setSelectedDocument(null);
        clearStream();
      }
    } catch (error: unknown) {
      setDocumentsError(error instanceof Error ? error.message : "Failed to delete document");
    }
  };

  const handleDeleteSelectedDocument = () => {
    if (!selectedDocument) {
      return;
    }
    if (!window.confirm(`Delete ${selectedDocument.filename}? This cannot be undone.`)) {
      return;
    }
    void deleteDocument(selectedDocument.id);
  };

  const formattedSize = useCallback((size: number) => `${Math.round(size / 1024)} KB`, []);

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Document index</p>
            <h2 className="text-2xl font-semibold text-white">Upload and query documents</h2>
          </div>
          <button
            onClick={fetchDocuments}
            className="rounded-2xl border border-slate-700 px-4 py-2 text-xs uppercase tracking-[0.3em] text-slate-200 transition hover:border-slate-500"
          >
            Refresh list
          </button>
        </div>
        <form onSubmit={handleUpload} className="mt-4 flex flex-col gap-3">
          <label className="text-sm text-slate-300">
            Select a file (txt/pdf/docx)
            <input
              ref={fileInputRef}
              type="file"
              className="mt-2 block w-full rounded-2xl border border-slate-700 bg-slate-950/50 px-4 py-2 text-sm text-white outline-none transition focus:border-slate-500"
            />
          </label>
          {uploadError ? (
            <p className="text-xs text-rose-400">{uploadError}</p>
          ) : null}
          <div className="flex items-center justify-between gap-3">
            <button
              type="submit"
              className="inline-flex items-center justify-center rounded-2xl bg-sky-500 px-6 py-3 text-sm font-semibold uppercase tracking-[0.3em] text-white transition hover:bg-sky-400 disabled:bg-slate-700"
              disabled={uploading}
            >
              {uploading ? "Uploading…" : "문서 업로드"}
            </button>
            <span className="text-xs uppercase tracking-[0.3em] text-slate-500">
              API: /documents/upload
            </span>
          </div>
        </form>
      </section>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <aside className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">Library</p>
            {loadingDocuments ? (
              <span className="text-xs text-slate-500">Loading...</span>
            ) : null}
          </div>
          {documentsError ? (
            <p className="mt-3 text-xs text-rose-400">{documentsError}</p>
          ) : null}
          <div className="mt-4 space-y-3">
            {documents.length === 0 ? (
              <p className="text-sm text-slate-500">No documents yet.</p>
            ) : null}
            {documents.map((document) => (
              <div
                key={document.id}
                className={`group flex flex-col gap-1 rounded-2xl border px-4 py-3 transition ${selectedDocument?.id === document.id
                    ? "border-sky-400 bg-sky-500/10 text-white"
                    : "border-slate-800 bg-slate-900 hover:border-slate-600"
                  }`}
                role="button"
                tabIndex={0}
                onClick={() => selectDocument(document.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    selectDocument(document.id);
                  }
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-left text-sm font-semibold">{document.filename}</span>
                  <span className={`rounded-full border px-3 py-1 text-[10px] ${badgeStyles[document.status]}`}>
                    {document.status}
                  </span>
                </div>
                <p className="text-xs text-slate-500">{formatTimestamp(document.updated_at)}</p>
                <button
                  className="self-end rounded-full border border-rose-400 px-2 py-0.5 text-[10px] uppercase tracking-[0.3em] text-rose-400 hover:bg-rose-500/10"
                  onClick={(event) => {
                    event.stopPropagation();
                    deleteDocument(document.id);
                  }}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        </aside>

        <div className="space-y-6">
          <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">
                  Document detail
                </p>
                <p className="text-sm text-slate-300">
                  {selectedDocument ? selectedDocument.filename : "Select a document to view metadata"}
                </p>
              </div>
              {selectedDocument ? (
                <span className={`rounded-full border px-3 py-1 text-[10px] ${badgeStyles[selectedDocument.status]}`}>
                  {selectedDocument.status}
                </span>
              ) : null}
            </div>
            {selectedDocument ? (
              <>
                <div className="mt-4 grid gap-3 text-xs text-slate-500 sm:grid-cols-2">
                  <div>
                    <p>Size: {formattedSize(selectedDocument.size)}</p>
                    <p>Uploaded: {formatTimestamp(selectedDocument.created_at)}</p>
                    <p>Chunks indexed: {selectedDocument.chunk_count}</p>
                  </div>
                  <div>
                    <p>Updated: {formatTimestamp(selectedDocument.updated_at)}</p>
                    {selectedDocument.error_message ? (
                      <p className="text-rose-400">Error: {selectedDocument.error_message}</p>
                    ) : null}
                  </div>
                </div>
                <div className="mt-4 flex justify-end">
                  <button
                    className="rounded-2xl border border-rose-400 px-4 py-2 text-[10px] uppercase tracking-[0.3em] text-rose-400 transition hover:bg-rose-500/10"
                    onClick={handleDeleteSelectedDocument}
                  >
                    Delete document
                  </button>
                </div>
              </>
            ) : null}
          </section>

          <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void startStream();
              }}
              className="space-y-4"
            >
              <div className="flex items-center justify-between gap-3">
                <label className="flex-1 text-sm text-slate-300">
                  Ask a question
                  <input
                    value={queryValue}
                    onChange={(event) => setQueryValue(event.target.value)}
                    placeholder="질문 예: 이 문서의 핵심 요약은?"
                    className="mt-2 w-full rounded-2xl border border-slate-800 bg-slate-950/50 px-4 py-3 text-base text-white outline-none transition focus:border-slate-500"
                    disabled={!selectedDocument || selectedDocument.status !== "done"}
                  />
                </label>
                <div className="flex flex-col gap-2 text-xs text-slate-400">
                  <span>Top K chunks</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={topK}
                    onChange={(event) => setTopK(Number(event.target.value))}
                    className="w-20 rounded-2xl border border-slate-800 bg-slate-950/50 px-3 py-2 text-sm text-white outline-none transition focus:border-slate-500"
                  />
                </div>
              </div>
              <div className="flex items-center justify-between gap-3">
                <button
                  type="submit"
                  className="inline-flex items-center justify-center rounded-2xl bg-sky-500 px-6 py-3 text-sm font-semibold uppercase tracking-[0.3em] text-white transition hover:bg-sky-400 disabled:bg-slate-700"
                  disabled={!selectedDocument || selectedDocument.status !== "done" || streamStatus === "streaming"}
                >
                  {streamStatus === "streaming" ? "Streaming…" : "메시지 전송"}
                </button>
                <span
                  className={`text-xs uppercase tracking-[0.3em] ${streamStatus === "error" ? "text-rose-400" : "text-slate-500"
                    }`}
                >
                  {streamStatus === "streaming" ? "SSE live" : streamStatus === "idle" ? "Ready" : "Error"}
                </span>
              </div>
              {streamError ? <p className="text-xs text-rose-400">{streamError}</p> : null}
            </form>
            <div className="mt-4 space-y-3">
              {streamChunks.length === 0 ? (
                <p className="text-sm text-slate-500">Streaming answers will appear here.</p>
              ) : null}
              {streamChunks.map((chunk, idx) => (
                <div key={`${chunk.type}-${idx}`} className="space-y-2 rounded-2xl border border-slate-800 bg-slate-950/50 p-4 text-sm">
                  <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs text-slate-300">
                    {chunk.type}
                  </span>
                  <p className="whitespace-pre-wrap text-base leading-relaxed text-white">{chunk.text}</p>
                  {chunk.meta ? (
                    <div className="text-xs text-slate-400">
                      <p>Document: {chunk.meta.document_id}</p>
                      <p>
                        Chunks:{" "}
                        {chunk.meta.chunks
                          .map((item) => `${item.chunk_id}${item.page ? ` (page ${item.page})` : ""}`)
                          .join(", ")}
                      </p>
                    </div>
                  ) : null}
                </div>
              ))}
              {references.length > 0 && (
                <section className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
                  <div className="mb-3 flex items-center justify-between text-[10px] uppercase tracking-[0.3em] text-slate-500">
                    <span>References</span>
                  </div>
                  <div className="space-y-3">
                    {references.map((reference) => {
                      const href = buildReferenceViewerHref(reference);
                      const containerClass =
                        "block rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-3 transition hover:border-slate-600 hover:bg-slate-900/90";
                      const disabledClass = "opacity-60 cursor-not-allowed";
                      const content = (
                        <>
                          <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.3em] text-slate-500">
                            <span>{reference.document_title}</span>
                            <span>{reference.page != null ? `Page ${reference.page}` : "Page ?"}</span>
                          </div>
                          <p className="mt-2 text-xs text-slate-200 line-clamp-3">{reference.snippet}</p>
                          {reference.score != null ? (
                            <p className="mt-2 text-[10px] text-slate-400">Score {reference.score.toFixed(3)}</p>
                          ) : null}
                        </>
                      );
                      return href ? (
                        <Link key={`${reference.document_id}-${reference.chunk_id}`} href={href} className={containerClass}>
                          {content}
                        </Link>
                      ) : (
                        <div
                          key={`${reference.document_id}-${reference.chunk_id}`}
                          className={`${containerClass} ${disabledClass}`}
                        >
                          {content}
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}
              <section className="rounded-2xl border border-slate-800 bg-slate-950/50 p-4 text-sm text-slate-300">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Document history</p>
                    <p className="text-[11px] text-slate-400">Select a prior question to review its answer.</p>
                  </div>
                  {docHistoryLoading ? <span className="text-xs text-slate-500">Loading…</span> : null}
                </div>
                {docHistoryError ? (
                  <p className="mt-2 text-[11px] text-rose-400">{docHistoryError}</p>
                ) : null}
                <div className="mt-4 space-y-2">
                  {documentHistoryEntries.length === 0 ? (
                    <p className="text-sm text-slate-500">
                      {selectedDocument ? "No documented questions yet." : "Select a document to view history."}
                    </p>
                  ) : (
                    documentHistoryEntries.map((entry) => {
                      const isSelected = entry.id === selectedDocHistoryId;
                      return (
                        <button
                          type="button"
                          key={entry.id}
                          onClick={() => setSelectedDocHistoryId(entry.id)}
                          className={`w-full rounded-2xl border px-4 py-3 text-left transition ${isSelected
                              ? "border-sky-500 bg-sky-500/10 text-white"
                              : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-600"
                            }`}
                        >
                          <div className="flex items-center justify-between text-[11px] uppercase tracking-[0.3em] text-slate-400">
                            <span>{entry.status === "error" ? "Error" : "OK"}</span>
                            <span>{formatTimestamp(entry.createdAt)}</span>
                          </div>
                          <p className="mt-2 text-sm font-semibold text-white">{entry.question}</p>
                          <p className="text-[12px] text-slate-400">{entry.summary}</p>
                        </button>
                      );
                    })
                  )}
                </div>
                {selectedDocHistoryEntry ? (
                  <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
                    <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Answer</p>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-white">
                      {selectedDocHistoryEntry.answer || "No answer recorded."}
                    </p>
                    {selectedDocHistoryEntry.references.length > 0 ? (
                      <div className="mt-3 text-xs text-slate-400">
                        <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">References</p>
                        <div className="mt-2 space-y-2">
                          {selectedDocHistoryEntry.references.map((reference) => (
                            <div
                              key={`${reference.document_id}-${reference.chunk_id}`}
                              className="rounded-xl border border-slate-800 bg-slate-950/50 px-3 py-2 text-[11px]"
                            >
                              <p className="text-white">{reference.document_title}</p>
                              <p className="text-slate-400">{reference.snippet}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </section>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
