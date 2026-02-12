"use client";

import { FormEvent, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { authenticatedFetch, getAuthHeaders } from "@/lib/apiClient/index";
import { PageHeader } from "@/components/shared";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";
import { useRouter, useSearchParams } from "next/navigation";
import { PdfViewerModal } from "@/components/pdf/PdfViewerModal";

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

type ChunkType = "answer" | "summary" | "detail" | "done" | "error";

const chunkTypeLabel: Record<ChunkType, string> = {
  answer: "답변",
  summary: "요약",
  detail: "상세",
  done: "완료",
  error: "오류",
};

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
  urlState?: {
    chunkId?: string;
    page?: number;
  };
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

const getBadgeStyle = (status: DocumentStatus): string => {
  const base = "px-2.5 py-0.5 rounded-full text-tiny font-semibold uppercase tracking-wider border border-solid border";
  switch (status) {
    case "queued":
      return `${base} bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/40`;
    case "processing":
      return `${base} bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/40`;
    case "done":
      return `${base} bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/40`;
    case "failed":
      return `${base} bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/40`;
    default:
      return `${base} border-slate-200 dark:border-slate-800`;
  }
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

function DocumentsPageContent() {
  const { isLoading: authLoading, user } = useAuth();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const streamAbortController = useRef<AbortController | null>(null);
  const router = useRouter();
  const searchParams = useSearchParams();

  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const selectedDocumentFromUrl = searchParams?.get("documentId") || undefined;
  const [selectedDocument, setSelectedDocument] = useState<DocumentDetail | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
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

  // PDF Viewer modal state
  const [pdfModalOpen, setPdfModalOpen] = useState(false);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [pdfFilename, setPdfFilename] = useState<string>("document.pdf");
  const [pdfInitialPage, setPdfInitialPage] = useState<number>(1);
  const [pdfViewerHref, setPdfViewerHref] = useState<string | undefined>(undefined);
  const [pdfHighlightSnippet, setPdfHighlightSnippet] = useState<string | undefined>(undefined);

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

  const deleteDocHistoryEntry = useCallback(async (id: string) => {
    try {
      await authenticatedFetch(`/history/${id}`, {
        method: "DELETE",
      });
    } catch (error) {
      console.error("Failed to delete document history entry", error);
    }
  }, []);

  const fetchDocumentDetail = useCallback(
    async (documentId: string) => {
      const payload = await authenticatedFetch(`/api/documents/${documentId}`) as { data?: { document: DocumentDetail } };
      const detail = payload?.data?.document || null;
      setSelectedDocument(detail);
      if (detail?.id) {
        setSelectedDocumentId(detail.id);
      }
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
      console.error("Failed to load documents:", error);
      // Don't show error for now, just show empty list
      setDocuments([]);
      // setDocumentsError(error instanceof Error ? error.message : "Failed to load documents");
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
    if (!selectedDocumentId) {
      return;
    }
    // When list is temporarily empty (e.g. backend unavailable), keep current selection
    // to avoid URL-init/select/clear loops.
    if (documents.length === 0) {
      return;
    }
    if (!documents.some((doc) => doc.id === selectedDocumentId)) {
      setSelectedDocumentId(null);
      setSelectedDocument(null);
    }
  }, [documents, selectedDocumentId]);

  useEffect(() => {
    if (authLoading) {
      return;
    }
    fetchDocHistory();
  }, [authLoading, fetchDocHistory, user?.id]);

  const selectDocument = useCallback(
    (documentId: string) => {
      if (selectedDocumentId === documentId) {
        return;
      }
      setSelectedDocumentId(documentId);
      setSelectedDocument(null);
      fetchDocumentDetail(documentId).catch(console.error);
      setReferences([]);
      setStreamChunks([]);
      setStreamStatus("idle");
      streamAbortController.current?.abort();

      // Update URL to include document ID
      const params = new URLSearchParams();
      params.set("documentId", documentId);
      router.replace(`/documents?${params.toString()}`);
    },
    [fetchDocumentDetail, router, selectedDocumentId]
  );

  // Initialize from URL
  useEffect(() => {
    // URL-based auto selection should run only when there is no active selection.
    // Otherwise it can override user's click while detail is still loading.
    // Also require at least one loaded document to avoid retry loops while backend is down.
    if (selectedDocumentFromUrl && !selectedDocumentId && documents.length > 0) {
      selectDocument(selectedDocumentFromUrl);
    }
  }, [selectedDocumentFromUrl, selectDocument, selectedDocumentId, documents.length]);

  // Restore URL state when document is selected
  const restoreUrlState = useCallback(() => {
    const stored = persistedStateRef.current;
    if (stored?.urlState) {
      const { chunkId, page } = stored.urlState;
      const params = new URLSearchParams(searchParams?.toString() ?? "");
      if (chunkId) {
        params.set("chunkId", chunkId);
      }
      if (page) {
        params.set("page", page.toString());
      }
      if (params.toString()) {
        window.history.replaceState(
          {},
          "",
          `/documents/${selectedDocument?.id}${params.toString() ? `?${params.toString()}` : ""}`
        );
      }
    }
  }, [searchParams, selectedDocument?.id]);

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
    // Respect user's current selection. Auto-select from recent history
    // only when no document is selected yet.
    if (selectedDocumentId) {
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
  }, [docHistory, documents, selectedDocumentId, selectDocument]);

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

  const handleRemoveDocHistory = useCallback(
    (id: string) => {
      setDocHistory((prev) => prev.filter((entry) => entry.id !== id));
      setSelectedDocHistoryId((prev) => (prev === id ? null : prev));
      void deleteDocHistoryEntry(id);
    },
    [deleteDocHistoryEntry]
  );

  const persistDocumentState = useCallback(() => {
    if (typeof window === "undefined") {
      return;
    }
    const payload: DocumentPageState = {
      selectedDocumentId: selectedDocument?.id ?? null,
      references,
      urlState: {
        chunkId: searchParams?.get("chunkId") || undefined,
        page: Number(searchParams?.get("page")) || undefined,
      },
    };
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  }, [references, selectedDocument?.id, searchParams]);

  // Persist state whenever references change
  useEffect(() => {
    if (restoredStateApplied) {
      persistDocumentState();
    }
  }, [references, persistDocumentState, restoredStateApplied]);

  // Update URL when references change
  useEffect(() => {
    if (selectedDocument && references.length > 0) {
      const params = new URLSearchParams();
      params.set("documentId", selectedDocument.id);
      if (references.length > 0) {
        params.set("references", encodeURIComponent(JSON.stringify(references)));
      }
      router.replace(`/documents?${params.toString()}`);
    }
  }, [references, selectedDocument, router]);

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
      setSelectedDocumentId(stored.selectedDocumentId);
      selectDocument(stored.selectedDocumentId);
    } else if (!selectedDocument) {
      setSelectedDocumentId(documents[0].id);
      fetchDocumentDetail(documents[0].id).catch(console.error);
    }
    if (stored?.references && stored.references.length > 0) {
      setReferences(stored.references);
    }
    if (selectedDocument && stored?.urlState) {
      restoreUrlState();
    }
    setRestoredStateApplied(true);
  }, [documents, fetchDocumentDetail, restoredStateApplied, restoreUrlState, selectDocument, selectedDocument]);
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
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
      const url = baseUrl
        ? `${baseUrl.replace(/\/+$/, "")}/api/documents/${selectedDocument.id}/query/stream`
        : `/api/documents/${selectedDocument.id}/query/stream`;
      const response = await fetch(url, {
        method: "POST",
        headers: {
          Accept: "text/event-stream",
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        body: JSON.stringify({ query: queryValue.trim(), top_k: topK }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const body = await response.text();
        let message = body || "Document stream failed";
        try {
          const parsed = JSON.parse(body);
          message = parsed?.detail || parsed?.message || message;
        } catch {
          // Keep raw body when parsing fails.
        }
        throw new Error(message);
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

  const buildReferencePdfHref = useCallback(
    (reference: Reference) => {
      const documentId = reference.document_id ?? selectedDocument?.id;
      if (!documentId) {
        return undefined;
      }
      return `/api/documents/${documentId}/viewer`;
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
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "";
      const url = baseUrl ? `${baseUrl.replace(/\/+$/, "")}/api/documents/upload` : "/api/documents/upload";
      const response = await fetch(url, {
        method: "POST",
        body: formData,
        headers: getAuthHeaders(),
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
        setSelectedDocumentId(null);
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
      <PageHeader
        title="Documents"
        description="문서를 업로드하고 관리하며, 전문 검색과 벡터 유사도로 질의합니다."
        actions={
          <button
            onClick={fetchDocuments}
            className="btn-secondary"
          >
            Refresh list
          </button>
        }
      />
      <section className="container-section text-foreground">
        <form onSubmit={handleUpload} className="flex flex-col gap-3">
          <label className="text-sm text-foreground">
            Select a file (txt/pdf/docx)
            <input
              ref={fileInputRef}
              type="file"
              className="mt-2 block w-full input-container text-sm"
            />
          </label>
          {uploadError ? (
            <p className="text-xs text-rose-600 dark:text-rose-400">{uploadError}</p>
          ) : null}
          <div className="flex items-center justify-between gap-3">
            <button
              type="submit"
              className="btn-primary"
              disabled={uploading}
            >
              {uploading ? "Uploading…" : "문서 업로드"}
            </button>
            <span className="text-xs uppercase tracking-wider text-muted-standard">
              API: /api/documents/upload
            </span>
          </div>
        </form>
      </section>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <aside
          className="rounded-2xl border p-5 bg-surface-elevated dark:border-border"
        >
          <div className="flex items-center justify-between">
            <h2 className="section-title">Library</h2>
            {loadingDocuments ? (
              <span className="text-xs text-muted-standard">Loading...</span>
            ) : null}
          </div>
          {documentsError ? (
            <p className="mt-3 text-xs text-rose-600 dark:text-rose-400">{documentsError}</p>
          ) : null}
          <div className="mt-4 space-y-3">
            {documents.length === 0 ? (
              <p className="text-sm text-muted-standard">No documents yet.</p>
            ) : null}
            {documents.map((document) => (
              <div
                key={document.id}
                className={cn(
                  "group relative flex flex-col gap-1 rounded-2xl border px-4 py-3 transition cursor-pointer text-foreground",
                  selectedDocumentId === document.id
                    ? "border-sky-500 bg-sky-500/10 dark:bg-sky-500/10"
                    : "border bg-surface-elevated hover:border-sky-500 dark:hover:bg-slate-800 dark:hover:border-sky-500"
                )}
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
                  <span className={getBadgeStyle(document.status)}>
                    {document.status}
                  </span>
                </div>
                <p className="text-xs text-muted-standard">{formatTimestamp(document.updated_at)}</p>
                <button
                  type="button"
                  className="absolute right-2 top-2 hidden h-5 w-5 items-center justify-center rounded-full border text-tiny transition group-hover:flex border-rose-600 bg-surface-elevated text-rose-600 hover:bg-rose-500/10 dark:border-rose-500 dark:bg-slate-950 dark:text-rose-400 dark:hover:bg-rose-500/10"
                  onClick={(event) => {
                    event.stopPropagation();
                    deleteDocument(document.id);
                  }}
                  aria-label="Delete document"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </aside>

        <div className="space-y-6">
          <section
            className="group rounded-2xl border p-5 bg-surface-elevated dark:border-border"
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="section-title">Document detail</h3>
                <p className="text-sm text-foreground">
                  {selectedDocument ? selectedDocument.filename : "Select a document to view metadata"}
                </p>
              </div>
              <div className="flex items-center gap-2">
                {selectedDocument ? (
                  <span className={getBadgeStyle(selectedDocument.status)}>
                    {selectedDocument.status}
                  </span>
                ) : null}
                <button
                  type="button"
                  className="hidden h-5 w-5 items-center justify-center rounded-full border text-tiny transition group-hover:flex border-rose-600 bg-surface-elevated text-rose-600 hover:bg-rose-500/10 dark:border-rose-500 dark:bg-slate-950 dark:text-rose-400 dark:hover:bg-rose-500/10"
                  onClick={handleDeleteSelectedDocument}
                  aria-label="Delete document"
                >
                  ✕
                </button>
              </div>
            </div>
            {selectedDocument ? (
              <>
                <div className="mt-4 grid gap-3 text-xs text-muted-standard">
                  <div>
                    <p>Size: {formattedSize(selectedDocument.size)}</p>
                    <p>Uploaded: {formatTimestamp(selectedDocument.created_at)}</p>
                    <p>Chunks indexed: {selectedDocument.chunk_count}</p>
                  </div>
                  <div>
                    <p>Updated: {formatTimestamp(selectedDocument.updated_at)}</p>
                    {selectedDocument.error_message ? (
                      <p className="text-rose-600 dark:text-rose-400">Error: {selectedDocument.error_message}</p>
                    ) : null}
                  </div>
                </div>
              </>
            ) : null}
          </section>

          <section
            className="rounded-2xl border p-5 bg-surface-elevated dark:border-border"
          >
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void startStream();
              }}
              className="space-y-4"
            >
              <div className="flex items-center justify-between gap-3">
                <label className="flex-1 text-sm text-foreground">
                  Ask a question
                  <input
                    value={queryValue}
                    onChange={(event) => setQueryValue(event.target.value)}
                    placeholder="질문 예: 이 문서의 핵심 요약은?"
                    className="mt-2 w-full rounded-2xl border px-4 py-3 text-base outline-none transition input-container"
                    disabled={!selectedDocument || selectedDocument.status !== "done"}
                  />
                </label>
                <div className="flex flex-col gap-2 text-xs text-muted-standard">
                  <span>Top K chunks</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={topK}
                    onChange={(event) => setTopK(Number(event.target.value))}
                    className="w-20 rounded-2xl border px-3 py-2 text-sm outline-none transition input-container"
                  />
                </div>
              </div>
              <div className="flex items-center justify-between gap-3">
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={!selectedDocument || selectedDocument.status !== "done" || streamStatus === "streaming"}
                >
                  {streamStatus === "streaming" ? (
                    <div className="flex items-center gap-2">
                      <span className="animate-pulse">Streaming</span>
                      <span className="animate-bounce">▶</span>
                    </div>
                  ) : "메시지 전송"}
                </button>
                <span
                  className="text-xs uppercase tracking-wider"
                  style={{color: streamStatus === "error" ? "var(--error)" : "var(--muted-foreground)"}}
                >
                  {streamStatus === "streaming" ? "SSE live" : streamStatus === "idle" ? "Ready" : "Error"}
                </span>
              </div>
              {streamError ? <p className="text-xs text-rose-600 dark:text-rose-400">{streamError}</p> : null}
            </form>
            <div className="mt-4 space-y-3">
              {streamChunks.length === 0 ? (
                <p className="text-sm text-muted-standard">Streaming answers will appear here.</p>
              ) : null}
              {streamChunks.map((chunk, idx) => (
                <div
                  key={`${chunk.type}-${idx}`}
                  className="space-y-2 br-card border p-4 text-sm bg-surface-elevated dark:bg-slate-950"
                >
                  <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs border bg-surface-base text-foreground dark:border-slate-800 dark:text-slate-50">
                    {chunkTypeLabel[chunk.type] ?? chunk.type}
                  </span>
                  <p className="whitespace-pre-wrap text-base leading-relaxed text-foreground">{chunk.text}</p>
                  {chunk.meta ? (
                    <div className="text-xs text-muted-standard">
                      <p>{selectedDocument?.filename ?? chunk.meta.document_id}</p>
                      <p>
                        {chunk.meta.chunks
                          .map((item) => `${item.chunk_id}${item.page ? ` (${item.page}p)` : ""}`)
                          .join(", ")}
                      </p>
                    </div>
                  ) : null}
                </div>
              ))}
              {references.length > 0 && (
                <section
                  className="rounded-2xl border p-4 text-sm bg-slate-100 border-slate-200 text-slate-900 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-50"
                >
                  <div className="mb-3 flex items-center justify-between text-tiny uppercase tracking-wider text-slate-600 dark:text-slate-400">
                    <span>근거 문서 ({references.length}건)</span>
                  </div>
                  <div className="space-y-3">
                    {references.map((reference, index) => {
                      const href = buildReferencePdfHref(reference);
                      const viewerHref = buildReferenceViewerHref(reference);
                      const content = (
                        <>
                          <div className="flex items-center justify-between text-tiny uppercase tracking-wider text-slate-600 dark:text-slate-400">
                            <span className="text-slate-900 dark:text-slate-50">{reference.document_title}</span>
                            <span>{reference.page != null ? `${reference.page}페이지` : "페이지 미확인"}</span>
                          </div>
                          <p className="mt-2 text-xs line-clamp-3 text-slate-900 dark:text-slate-50">{reference.snippet}</p>
                          {reference.score != null ? (
                            <p className="mt-2 text-tiny text-slate-600 dark:text-slate-400">유사도 {(reference.score * 100).toFixed(1)}%</p>
                          ) : null}
                        </>
                      );
                      return href ? (
                        <button
                          key={`${reference.document_id}-${reference.chunk_id}-${index}`}
                          type="button"
                          onClick={async () => {
                            try {
                              // Use fetchWithAuth for authenticated PDF fetch
                              const { fetchWithAuth } = await import("@/lib/apiClient");
                              const response = await fetchWithAuth(href);

                              console.log("PDF response status:", response.status, response.statusText);
                              console.log("PDF response headers:", Object.fromEntries(response.headers.entries()));

                              const blob = await response.blob();
                              console.log("PDF blob type:", blob.type, "size:", blob.size);

                              // Open PDF in modal - pass blob directly
                              setPdfBlob(blob);
                              setPdfFilename(reference.document_title || "document.pdf");
                              setPdfInitialPage(reference.page || 1);
                              setPdfHighlightSnippet(reference.snippet || undefined);
                              setPdfViewerHref(viewerHref);
                              setPdfModalOpen(true);
                            } catch (error) {
                              console.error('Failed to open document:', error);
                            }
                          }}
                          className="block rounded-2xl border px-4 py-3 transition cursor-pointer border-slate-200 bg-slate-50 text-slate-900 hover:border-sky-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-50"
                        >
                          {content}
                        </button>
                      ) : (
                        <div
                          key={`${reference.document_id}-${reference.chunk_id}`}
                          className="rounded-2xl border px-4 py-3 opacity-60 cursor-not-allowed border-slate-200 bg-slate-50 text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-50"
                          title="문서 정보가 부족하여 원문을 열 수 없습니다"
                        >
                          {content}
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}
              <section
                className="rounded-2xl border p-4 text-sm bg-slate-100 border-slate-200 text-slate-900 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-50"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-wider text-slate-600 dark:text-slate-400">Document history</p>
                    <p className="text-xs text-slate-600 dark:text-slate-400">Select a prior question to review its answer.</p>
                  </div>
                  {docHistoryLoading ? <span className="text-xs text-slate-600 dark:text-slate-400">Loading…</span> : null}
                </div>
                {docHistoryError ? (
                  <p className="mt-2 text-xs text-rose-600 dark:text-rose-400">{docHistoryError}</p>
                ) : null}
                <div className="mt-4 space-y-2">
                  {documentHistoryEntries.length === 0 ? (
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {selectedDocument ? "No documented questions yet." : "Select a document to view history."}
                    </p>
                  ) : (
                    documentHistoryEntries.map((entry) => {
                      const isSelected = entry.id === selectedDocHistoryId;
                      return (
                        <div
                          key={entry.id}
                          className={cn(
                            "group relative flex w-full flex-col rounded-2xl border px-4 py-3 transition cursor-pointer text-slate-900 dark:text-slate-50",
                            isSelected
                              ? "border-sky-500 bg-sky-500/10"
                              : "border-slate-200 bg-slate-50 hover:border-sky-500 dark:border-slate-800 dark:bg-slate-950 dark:hover:border-sky-500"
                          )}
                        >
                          <div
                            onClick={() => setSelectedDocHistoryId(entry.id)}
                            className="text-left"
                          >
                            <div className="flex items-center justify-between text-xs uppercase tracking-[0.3em] text-slate-600 dark:text-slate-400">
                              <span>{entry.status === "error" ? "Error" : "OK"}</span>
                              <div className="flex items-center gap-2">
                                <span>{formatTimestamp(entry.createdAt)}</span>
                                <button
                                  type="button"
                                  aria-label={`Delete history entry ${entry.question}`}
                                  onClick={(event) => {
                                    event.stopPropagation();
                                    handleRemoveDocHistory(entry.id);
                                  }}
                                  className="hidden h-5 w-5 items-center justify-center rounded-full border text-tiny transition group-hover:flex border-rose-600 bg-slate-100 text-rose-600 hover:bg-rose-500/10 dark:border-rose-500 dark:bg-slate-950 dark:text-rose-400 dark:hover:bg-rose-500/10"
                                  title="Delete history"
                                >
                                  ✕
                                </button>
                              </div>
                            </div>
                            <p className="mt-2 text-sm font-semibold text-slate-900 dark:text-slate-50">{entry.question}</p>
                            <p className="text-[12px] text-slate-600 dark:text-slate-400">{entry.summary}</p>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
                {selectedDocHistoryEntry ? (
                  <div
                    className="group relative mt-4 rounded-2xl border p-4 text-sm bg-slate-100 border-slate-200 text-slate-900 dark:bg-slate-950 dark:border-slate-800 dark:text-slate-50"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-xs uppercase tracking-[0.3em] text-slate-600 dark:text-slate-400">Answer</p>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-slate-600 dark:text-slate-400">{formatTimestamp(selectedDocHistoryEntry.createdAt)}</span>
                        <button
                          type="button"
                          aria-label={`Delete history entry ${selectedDocHistoryEntry.question}`}
                          onClick={() => handleRemoveDocHistory(selectedDocHistoryEntry.id)}
                          className="hidden h-5 w-5 items-center justify-center rounded-full border text-tiny transition group-hover:flex border-rose-600 bg-slate-100 text-rose-600 hover:bg-rose-500/10 dark:border-rose-500 dark:bg-slate-950 dark:text-rose-400 dark:hover:bg-rose-500/10"
                          title="Delete history"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-sm text-slate-900 dark:text-slate-50">
                      {selectedDocHistoryEntry.answer || "No answer recorded."}
                    </p>
                    {selectedDocHistoryEntry.references.length > 0 ? (
                      <div className="mt-3 text-xs text-slate-600 dark:text-slate-400">
                        <p className="text-tiny uppercase tracking-wider text-slate-600 dark:text-slate-400">References</p>
                        <div className="mt-2 space-y-2">
                          {selectedDocHistoryEntry.references.map((reference) => {
                            const viewerHref = buildReferenceViewerHref(reference);
                            const viewerUrl = buildReferencePdfHref(reference);

                            const content = (
                              <>
                                <p className="text-slate-900 dark:text-slate-50">{reference.document_title}</p>
                                <p className="text-slate-600 dark:text-slate-400">{reference.snippet}</p>
                                {reference.page != null ? (
                                  <p className="mt-1 text-tiny text-sky-600 dark:text-sky-400">
                                    페이지 {reference.page}
                                  </p>
                                ) : null}
                              </>
                            );

                            return viewerUrl ? (
                              <button
                                key={`${reference.document_id}-${reference.chunk_id}`}
                                type="button"
                                onClick={async () => {
                                  try {
                                    const { fetchWithAuth } = await import('@/lib/apiClient');
                                    const response = await fetchWithAuth(viewerUrl);
                                    const blob = await response.blob();
                                    // Open PDF in modal - pass blob directly
                                    setPdfBlob(blob);
                                    setPdfFilename(reference.document_title || "document.pdf");
                                    setPdfInitialPage(reference.page || 1);
                                    setPdfHighlightSnippet(reference.snippet || undefined);
                                    setPdfViewerHref(viewerHref);
                                    setPdfModalOpen(true);
                                  } catch (error) {
                                    console.error('Failed to open document:', error);
                                  }
                                }}
                                className="block rounded-xl border px-3 py-2 text-xs transition cursor-pointer w-full text-left border-slate-200 bg-slate-50 text-slate-900 hover:border-sky-500 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-50"
                              >
                                {content}
                              </button>
                            ) : (
                              <div
                                key={`${reference.document_id}-${reference.chunk_id}`}
                                className="rounded-xl border px-3 py-2 text-xs opacity-60 border-slate-200 bg-slate-50 text-slate-900 dark:border-slate-800 dark:bg-slate-950 dark:text-slate-50"
                              >
                                {content}
                              </div>
                            );
                          })}
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

      {/* PDF Viewer Modal */}
      <PdfViewerModal
        isOpen={pdfModalOpen}
        onClose={() => {
          setPdfModalOpen(false);
          setPdfBlob(null);
          setPdfHighlightSnippet(undefined);
          setPdfViewerHref(undefined);
        }}
        pdfBlob={pdfBlob}
        filename={pdfFilename}
        initialPage={pdfInitialPage}
        viewerHref={pdfViewerHref}
        highlightSnippet={pdfHighlightSnippet}
      />
    </div>
  );
}

// Wrapper component with Suspense boundary for useSearchParams
export default function DocumentsPage() {
  return (
    <Suspense fallback={<div className="p-4 text-slate-600 dark:text-slate-400">Loading documents...</div>}>
      <DocumentsPageContent />
    </Suspense>
  );
}
