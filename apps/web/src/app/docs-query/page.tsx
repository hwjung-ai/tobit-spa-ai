"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/shared";
import { PdfViewerModal } from "@/components/pdf/PdfViewerModal";
import { authenticatedFetch, fetchWithAuth } from "@/lib/apiClient";
import { useConfirm } from "@/hooks/use-confirm";

/**
 * Document category type
 */
type DocumentCategory = "manual" | "policy" | "technical" | "guide" | "report" | "other";

/**
 * Category labels
 */
const CATEGORY_LABELS: Record<DocumentCategory, string> = {
  manual: "매뉴얼",
  policy: "정책",
  technical: "기술문서",
  guide: "가이드",
  report: "보고서",
  other: "기타",
};

/**
 * Toast notification type
 */
interface Toast {
  id: string;
  type: "success" | "error" | "info";
  message: string;
}

/**
 * Document item from API
 */
interface DocumentItem {
  id: string;
  filename: string;
  format: string | null;
  status: string;
  size: number;
  total_chunks: number;
  created_at: string;
  category?: string;
  tags?: string[];
  selected?: boolean;
}

/**
 * Reference from search result
 */
interface Reference {
  document_id: string;
  document_title: string;
  chunk_id: string;
  page: number | null;
  snippet: string;
  score: number;
}

/**
 * Query history entry
 */
interface QueryHistoryEntry {
  id: string;
  query: string;
  answer: string;
  references: Reference[];
  timestamp: string;
  document_count: number;
}

/**
 * Query history entry from API
 */
interface QueryHistoryEntryAPI {
  id: string;
  query: string;
  answer: string;
  references: Reference[];
  document_count: number;
  reference_count: number;
  elapsed_ms: number;
  created_at: string;
}

/**
 * SSE Progress event
 */
interface ProgressEvent {
  stage: string;
  message: string;
  elapsed_ms: number;
}

export default function DocsQueryPage() {
  // Document state
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(false);

  // Filter state
  const [selectedCategories, setSelectedCategories] = useState<DocumentCategory[]>([]);
  const [showOnlySelected] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Upload state
  const [uploadingFile, setUploadingFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);

  // Query state
  const [query, setQuery] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [answer, setAnswer] = useState("");
  const [references, setReferences] = useState<Reference[]>([]);
  const [progress, setProgress] = useState<ProgressEvent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pdfViewerOpen, setPdfViewerOpen] = useState(false);
  const [pdfBlob, setPdfBlob] = useState<Blob | null>(null);
  const [pdfFilename, setPdfFilename] = useState("document.pdf");
  const [pdfInitialPage, setPdfInitialPage] = useState(1);
  const [pdfHighlightSnippet, setPdfHighlightSnippet] = useState<string | undefined>(undefined);
  const [pdfViewerHref, setPdfViewerHref] = useState<string | undefined>(undefined);

  // Toast notifications
  const [toasts, setToasts] = useState<Toast[]>([]);

  // Query history
  const [queryHistory, setQueryHistory] = useState<QueryHistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  // Left panel tabs
  const [leftPanelTab, setLeftPanelTab] = useState<"library" | "history">("library");

  // Confirm dialog
  const [confirmDialog, ConfirmDialogComponent] = useConfirm();

  // Refs
  const fileInputRef = useRef<HTMLInputElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const answerEndRef = useRef<HTMLDivElement>(null);

  // Fetch documents on mount
  useEffect(() => {
    void fetchDocuments();
    void fetchQueryHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Scroll to answer end when streaming
  useEffect(() => {
    answerEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [answer]);

  // Auto-remove toasts after 3 seconds
  useEffect(() => {
    if (toasts.length === 0) return;
    const timer = setTimeout(() => {
      setToasts((prev) => prev.slice(1));
    }, 3000);
    return () => clearTimeout(timer);
  }, [toasts]);

  /**
   * Show toast notification
   */
  const showToast = useCallback((type: Toast["type"], message: string) => {
    const id = Date.now().toString();
    setToasts((prev) => [...prev, { id, type, message }]);
  }, []);

  /**
   * Fetch documents from API
   */
  const fetchDocuments = async () => {
    setLoadingDocs(true);
    try {
      const payload = await authenticatedFetch<{ data?: { documents?: DocumentItem[] } }>("/api/documents/");
      const docs = payload?.data?.documents ?? [];
      setDocuments(docs.map((doc: DocumentItem) => ({ ...doc, selected: true })));
    } catch (err) {
      console.error("Failed to fetch documents:", err);
      showToast("error", "문서 목록을 불러오지 못했습니다.");
    } finally {
      setLoadingDocs(false);
    }
  };

  /**
   * Fetch query history from API
   */
  const fetchQueryHistory = async () => {
    try {
      const payload = await authenticatedFetch<{ data?: { history?: QueryHistoryEntryAPI[] } }>(
        "/api/documents/query-history?per_page=50"
      );
      const history = payload?.data?.history ?? [];
      setQueryHistory(
        history.map((h: QueryHistoryEntryAPI) => ({
          id: h.id,
          query: h.query,
          answer: h.answer,
          references: h.references || [],
          timestamp: h.created_at,
          document_count: h.document_count,
        }))
      );
    } catch (err) {
      console.error("Failed to fetch query history:", err);
    }
  };

  /**
   * Save query history to API
   */
  const saveQueryHistory = async (
    queryText: string,
    answerText: string,
    refs: Reference[],
    docCount: number,
    elapsedMs: number
  ) => {
    try {
      await authenticatedFetch("/api/documents/query-history", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: queryText,
          answer: answerText,
          references: refs,
          document_count: docCount,
          elapsed_ms: elapsedMs,
        }),
      });
    } catch (err) {
      console.error("Failed to save query history:", err);
    }
  };

  /**
   * Upload document with progress
   */
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Validate file size (max 50MB)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      showToast("error", "파일 크기는 50MB 이하여야 합니다.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setUploadingFile(file);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append("file", file);

    try {
      // Simulate progress (XMLHttpRequest for real progress would be better)
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => Math.min(prev + 10, 90));
      }, 200);

      const uploadResponse = await fetchWithAuth("/api/documents/upload", {
        method: "POST",
        body: formData,
      });
      const payload = (await uploadResponse.json()) as { data?: { document?: DocumentItem } };

      clearInterval(progressInterval);
      setUploadProgress(100);
      const newDoc = payload?.data?.document;
      
      if (newDoc) {
        setDocuments((prev) => [{ ...newDoc, selected: true }, ...prev]);
        showToast("success", `"${file.name}" 업로드 완료`);
      } else {
        throw new Error("Upload failed");
      }
    } catch (err) {
      console.error("Upload failed:", err);
      showToast("error", "문서 업로드에 실패했습니다.");
    } finally {
      setTimeout(() => {
        setUploadingFile(null);
        setUploadProgress(0);
      }, 500);
      
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  /**
   * Update document category
   */
  const updateCategory = async (docId: string, category: DocumentCategory) => {
    try {
      const url = `/api/documents/${docId}/category?category=${category}`;
      console.log(`[updateCategory] Sending PATCH to: ${url}`, { docId, category });

      await authenticatedFetch(url, {
        method: "PATCH",
      });
      console.log("[updateCategory] Success");

      // Only update local state after successful API call
      setDocuments((prev) =>
        prev.map((doc) => (doc.id === docId ? { ...doc, category } : doc))
      );
      showToast("success", "카테고리가 변경되었습니다.");
    } catch (err) {
      console.error("[updateCategory] Error:", err);
      showToast("error", `카테고리 변경 실패: ${err instanceof Error ? err.message : "알 수 없는 오류"}`);
    }
  };

  /**
   * Toggle document selection
   */
  const toggleDocument = (docId: string) => {
    setDocuments((prev) =>
      prev.map((doc) =>
        doc.id === docId ? { ...doc, selected: !doc.selected } : doc
      )
    );
  };

  /**
   * Select all / deselect all
   */
  const toggleAllDocuments = (select: boolean) => {
    setDocuments((prev) => prev.map((doc) => ({ ...doc, selected: select })));
  };

  /**
   * Delete document
   */
  const deleteDocument = async (docId: string) => {
    const doc = documents.find((d) => d.id === docId);
    if (!doc) return;

    const ok = await confirmDialog({
      title: "Delete Document",
      description: `"${doc.filename}" 문서를 삭제하시겠습니까?`,
      confirmLabel: "Delete",
    });
    if (!ok) return;

    try {
      await authenticatedFetch(`/api/documents/${docId}`, {
        method: "DELETE",
      });
      setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
      showToast("success", "문서가 삭제되었습니다.");
    } catch (err) {
      console.error("Delete failed:", err);
      showToast("error", "문서 삭제에 실패했습니다.");
    }
  };

  /**
   * Stream query to all selected documents
   */
  const streamQuery = async () => {
    const queryText = query.trim();
    console.log("[streamQuery] Starting query:", { queryText, selectedCount });

    if (!queryText) {
      showToast("error", "질의를 입력해주세요.");
      return;
    }

    if (selectedCount === 0) {
      showToast("error", "최소 하나의 문서를 선택해주세요.");
      console.log("[streamQuery] No documents selected:", { documents: documents.length, selected: documents.filter(d => d.selected).length });
      return;
    }

    // Abort any existing stream
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    setIsStreaming(true);
    setAnswer("");
    setReferences([]);
    setProgress(null);
    setError(null);

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // Get selected document IDs
    const selectedDocIds = documents
      .filter((doc) => doc.selected)
      .map((doc) => doc.id);

    // Get categories to filter
    const categories = selectedCategories.length > 0 ? selectedCategories : undefined;

    const requestBody = {
      query: queryText,
      document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
      categories,
      top_k: 10,
      min_relevance: 0.05,
    };

    console.log("[streamQuery] Request body:", requestBody);
    let finalAnswer = "";
    let finalReferences: Reference[] = [];
    let finalProgress: ProgressEvent | null = null;

    try {
      const response = await fetchWithAuth("/api/documents/query-all/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify(requestBody),
        signal: abortController.signal,
      });

      console.log("[streamQuery] Response status:", response.status);

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No reader");

      const decoder = new TextDecoder();
      let buffer = "";
      let eventCount = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log("[streamQuery] Stream completed, total events:", eventCount);
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let eventType = "";
        let data = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            data = line.slice(6);
          } else if (line === "" && eventType && data) {
            eventCount++;
            console.log(`[streamQuery] Event ${eventCount}:`, { eventType, dataLength: data.length });

            try {
              const parsed = JSON.parse(data);

              switch (eventType) {
                case "progress":
                  console.log("[streamQuery] Progress:", parsed);
                  setProgress(parsed);
                  finalProgress = parsed;
                  break;
                case "answer":
                  console.log("[streamQuery] Answer chunk:", parsed);
                  finalAnswer += parsed.text;
                  setAnswer(finalAnswer);
                  break;
                case "summary":
                  console.log("[streamQuery] Summary:", parsed);
                  finalAnswer = parsed.text;
                  setAnswer(finalAnswer);
                  break;
                case "detail":
                  console.log("[streamQuery] Detail:", parsed);
                  finalAnswer += "\n\n" + parsed.text;
                  setAnswer(finalAnswer);
                  break;
                case "done":
                  console.log("[streamQuery] Done event:", parsed);
                  finalReferences = parsed.meta?.references || [];
                  setReferences(finalReferences);
                  setProgress(null);
                  break;
                case "error":
                  console.log("[streamQuery] Error event:", parsed);
                  setError(parsed.message);
                  setProgress(null);
                  break;
              }
            } catch (e) {
              console.error("[streamQuery] Failed to parse event:", { eventType, data, error: e });
            }

            eventType = "";
            data = "";
          }
        }
      }

      // Save to backend
      if (finalAnswer) {
        await saveQueryHistory(
          queryText,
          finalAnswer,
          finalReferences,
          selectedDocIds.length,
          finalProgress?.elapsed_ms || 0
        );
        
        // Refresh history from backend
        fetchQueryHistory();
        showToast("success", "질의가 완료되었습니다.");
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") {
        showToast("info", "질의가 중단되었습니다.");
        return;
      }
      console.error("Stream error:", err);
      setError("질의 처리 중 오류가 발생했습니다.");
      showToast("error", "질의 처리 중 오류가 발생했습니다.");
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  /**
   * Abort streaming
   */
  const abortStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setIsStreaming(false);
  };

  /**
   * Open reference in PDF viewer (new window/tab)
   */
  const openReference = async (ref: Reference) => {
    try {
      let targetPage = ref.page ?? 1;

      if (!ref.page && ref.chunk_id) {
        const chunkPayload = await authenticatedFetch<{ data?: { chunk?: { page?: number | null; page_number?: number | null } } }>(
          `/api/documents/${ref.document_id}/chunks/${ref.chunk_id}`,
        );
        const chunk = chunkPayload?.data?.chunk;
        targetPage = chunk?.page ?? chunk?.page_number ?? targetPage;
      }

      const response = await fetchWithAuth(`/api/documents/${ref.document_id}/viewer`);
      const blob = await response.blob();
      const params = new URLSearchParams();
      params.set("chunkId", ref.chunk_id);
      params.set("page", String(targetPage || 1));
      setPdfBlob(blob);
      setPdfFilename(ref.document_title || "document.pdf");
      setPdfInitialPage(targetPage || 1);
      setPdfHighlightSnippet(ref.snippet || undefined);
      setPdfViewerHref(`/documents/${ref.document_id}/viewer?${params.toString()}`);
      setPdfViewerOpen(true);
    } catch (err) {
      console.error("Failed to open PDF:", err);
      showToast("error", "PDF를 열 수 없습니다.");
    }
  };

  /**
   * Load history entry
   */
  const loadHistoryEntry = (entry: QueryHistoryEntry) => {
    setQuery(entry.query);
    setAnswer(entry.answer);
    setReferences(entry.references);
    setShowHistory(false);
    showToast("info", "이전 질의가 로드되었습니다.");
  };

  const deleteHistoryEntry = async (historyId: string) => {
    try {
      await authenticatedFetch(`/api/documents/query-history/${historyId}`, {
        method: "DELETE",
      });
      setQueryHistory((prev) => prev.filter((entry) => entry.id !== historyId));
      showToast("success", "이력이 삭제되었습니다.");
    } catch (err) {
      console.error("Failed to delete history:", err);
      showToast("error", "이력 삭제에 실패했습니다.");
    }
  };

  /**
   * Copy answer to clipboard
   */
  const copyAnswer = async () => {
    if (!answer) return;
    
    try {
      await navigator.clipboard.writeText(answer);
      showToast("success", "답변이 클립보드에 복사되었습니다.");
    } catch (err) {
      console.error("Copy failed:", err);
      showToast("error", "복사에 실패했습니다.");
    }
  };

  // Filter documents by category, selection, and search query
  const filteredDocuments = documents.filter((doc) => {
    if (showOnlySelected && !doc.selected) return false;
    if (selectedCategories.length > 0 && doc.category && !selectedCategories.includes(doc.category as DocumentCategory)) {
      return false;
    }
    if (searchQuery && !doc.filename.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  const selectedCount = documents.filter((doc) => doc.selected).length;

  return (
    <div className="flex flex-col h-screen bg-surface-base">
      {/* Page Header */}
      <PageHeader
        title="문서 질의"
        description="전체 문서에서 질의하고 응답받기"
      />

      {/* Toast Notifications */}
      <div className="fixed top-4 right-4 z-40 flex flex-col gap-2">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={cn(
              "rounded-lg px-4 py-3 shadow-lg transition-all duration-300",
              toast.type === "success" && "bg-emerald-600 text-white",
              toast.type === "error" && "bg-rose-600 text-white",
              toast.type === "info" && "bg-sky-600 text-white"
            )}
          >
            {toast.type === "success" && "✓ "}
            {toast.type === "error" && "✕ "}
            {toast.type === "info" && "ℹ "}
            {toast.message}
          </div>
        ))}
      </div>

      {/* Confirm Dialog */}
      <ConfirmDialogComponent />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Panel: Document Management */}
        <div className="flex w-80 flex-col border-r border-border overflow-y-auto">

        {/* Left Panel Tabs */}
        <div className="border-b border-border flex">
          <button
            onClick={() => setLeftPanelTab("library")}
            className={cn(
              "flex-1 px-4 py-2 text-sm font-medium transition border-b-2",
              leftPanelTab === "library"
                ? "border-b-sky-500 text-sky-500"
                : "border-b-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            📚 라이브러리
          </button>
          <button
            onClick={() => setLeftPanelTab("history")}
            className={cn(
              "flex-1 px-4 py-2 text-sm font-medium transition border-b-2",
              leftPanelTab === "history"
                ? "border-b-sky-500 text-sky-500"
                : "border-b-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            📜 이력 ({queryHistory.length})
          </button>
        </div>

        {/* Input file hidden */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.xlsx,.pptx,.txt"
          onChange={handleUpload}
          className="hidden"
          disabled={!!uploadingFile}
        />

        {/* Library Tab Content */}
        {leftPanelTab === "library" && (
          <>
            {/* Upload Section */}
            <div className="border-b border-border p-3">
              {uploadingFile ? (
                <div className="rounded-lg border border-sky-500/30 bg-sky-500/5 p-2">
                  <div className="flex items-center gap-2">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-sky-500 border-t-transparent" />
                    <span className="text-xs text-foreground truncate">
                      {uploadingFile.name}
                    </span>
                    <span className="text-xs text-muted-foreground">{uploadProgress}%</span>
                  </div>
                  <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface-elevated">
                    <div
                      className="h-full bg-sky-500 transition-all duration-300"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full rounded-lg border border-dashed border-sky-500 p-2 text-sm text-sky-500 transition hover:bg-sky-500/10"
                >
                  📄 업로드
                </button>
              )}
            </div>

            {/* Search Documents */}
            <div className="border-b border-border p-3">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="🔍 문서 검색..."
                className="w-full rounded-lg border border-border bg-surface-elevated px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-sky-500 focus:outline-none"
              />
            </div>

            {/* Category Filter */}
            <div className="border-b border-border p-3">
              <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                카테고리 필터
              </p>
              <div className="flex flex-wrap gap-1">
                {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                  <button
                    key={value}
                    onClick={() => {
                      setSelectedCategories((prev) =>
                        prev.includes(value as DocumentCategory)
                          ? prev.filter((c) => c !== value)
                          : [...prev, value as DocumentCategory]
                      );
                    }}
                    className={cn(
                      "rounded px-2 py-1 text-xs transition",
                      selectedCategories.includes(value as DocumentCategory)
                        ? "bg-sky-500 text-white"
                        : "bg-surface-elevated text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {/* Document Selection */}
            <div className="flex items-center justify-between border-b border-border px-3 py-2">
              <span className="text-xs text-muted-foreground">
                {selectedCount}/{documents.length} 선택됨
              </span>
              <div className="flex gap-2">
            <button
              onClick={() => toggleAllDocuments(true)}
              className="text-xs text-sky-500 hover:underline"
            >
              전체선택
            </button>
            <button
              onClick={() => toggleAllDocuments(false)}
              className="text-xs text-muted-foreground hover:underline"
            >
              선택해제
            </button>
          </div>
        </div>

            {/* Document List */}
            <div className="flex-1 overflow-y-auto p-2">
          {loadingDocs ? (
            // Skeleton loading
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="animate-pulse rounded-lg border border-border p-3">
                  <div className="h-4 bg-surface-elevated rounded w-3/4" />
                  <div className="mt-2 h-3 bg-surface-elevated rounded w-1/2" />
                  <div className="mt-2 h-5 bg-surface-elevated rounded w-1/3" />
                </div>
              ))}
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="p-4 text-center">
              <p className="text-4xl mb-2">📭</p>
              <p className="text-sm text-muted-foreground">
                {searchQuery ? "검색 결과가 없습니다." : "문서가 없습니다."}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                문서를 업로드해주세요.
              </p>
            </div>
          ) : (
            filteredDocuments.map((doc) => (
              <div
                key={doc.id}
                className={cn(
                  "group mb-2 rounded-lg border p-2 transition",
                  doc.selected
                    ? "border-sky-500/50 bg-sky-500/5"
                    : "border-border bg-surface-elevated"
                )}
              >
                <div className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    checked={doc.selected}
                    onChange={() => toggleDocument(doc.id)}
                    className="mt-1"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="truncate text-sm font-medium text-foreground">
                      {doc.filename}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {doc.total_chunks} 청크 • {formatBytes(doc.size)}
                    </p>
                    <div className="mt-1 flex items-center gap-2">
                      <select
                        value={doc.category || "other"}
                        onChange={(e) =>
                          updateCategory(doc.id, e.target.value as DocumentCategory)
                        }
                        className="rounded border border-border bg-surface-base px-1 py-0.5 text-xs"
                      >
                        {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <button
                    onClick={() => deleteDocument(doc.id)}
                    className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-rose-500 transition"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))
            )}
            </div>
          </>
        )}

        {/* History Tab Content */}
        {leftPanelTab === "history" && (
          <div className="flex-1 overflow-y-auto p-3">
            {queryHistory.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-4xl mb-2">📭</p>
                <p className="text-muted-foreground">이력이 없습니다.</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  질의를 시작해보세요!
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {queryHistory.map((entry) => (
                  <div
                    key={entry.id}
                    onClick={() => {
                      setQuery(entry.query);
                      setAnswer(entry.answer);
                      setReferences(entry.references);
                      setLeftPanelTab("library");
                    }}
                    className="group relative w-full cursor-pointer rounded-lg border border-border bg-surface-elevated p-2 text-left transition hover:border-sky-500/50 hover:bg-sky-500/5"
                  >
                    <p className="truncate text-sm font-medium text-foreground">
                      {entry.query}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(entry.timestamp).toLocaleString('ko-KR')}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                      {entry.answer}
                    </p>
                    <button
                      className="absolute right-2 bottom-2 flex h-5 w-5 items-center justify-center rounded-full border border-rose-400 text-tiny text-rose-600 opacity-0 transition duration-200 group-hover:opacity-100 group-hover:pointer-events-auto hover:bg-rose-50 dark:border-rose-500 dark:text-rose-400 dark:hover:bg-rose-950/30"
                      onClick={(event) => {
                        event.stopPropagation();
                        void deleteHistoryEntry(entry.id);
                      }}
                      aria-label="Delete history"
                    >
                      X
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right Panel: Query & Response */}
      <div className="flex flex-1 flex-col">
        {/* Query Input */}
        <div className="border-b border-border p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !isStreaming && streamQuery()}
              placeholder="전체 문서에 질의를 입력하세요..."
              className="flex-1 rounded-lg border border-border bg-surface-elevated px-4 py-3 text-foreground placeholder:text-muted-foreground focus:border-sky-500 focus:outline-none"
              disabled={isStreaming}
            />
            {isStreaming ? (
              <button
                onClick={abortStream}
                className="rounded-lg bg-rose-500 px-6 py-3 text-white transition hover:bg-rose-600"
              >
                중단
              </button>
            ) : (
              <button
                onClick={streamQuery}
                disabled={!query.trim() || selectedCount === 0}
                className="rounded-lg bg-sky-500 px-6 py-3 text-white transition hover:bg-sky-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                질의
              </button>
            )}
          </div>
          {error && (
            <p className="mt-2 text-sm text-rose-500">{error}</p>
          )}
        </div>

        {/* Progress */}
        {progress && (
          <div className="border-b border-border bg-sky-500/5 p-3">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 animate-pulse rounded-full bg-sky-500/20 flex items-center justify-center text-lg">
                ⚙️
              </div>
              <div className="flex-1">
                <p className="font-medium text-sky-400">{progress.message}</p>
                <p className="text-xs text-muted-foreground">
                  경과: {progress.elapsed_ms}ms
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <div className="flex flex-1 overflow-hidden">
          {/* Answer Section */}
          <div className="flex-1 overflow-y-auto p-4">
            {answer ? (
              <div className="space-y-4">
                {/* Copy Button */}
                <div className="flex justify-end">
                  <button
                    onClick={copyAnswer}
                    className="flex items-center gap-1 rounded-lg bg-surface-elevated px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground transition"
                  >
                    📋 복사
                  </button>
                </div>
                
                {/* Answer Content */}
                <div className="prose prose-sm max-w-none dark:prose-invert">
                  <div className="whitespace-pre-wrap rounded-lg bg-surface-elevated p-4 text-foreground">
                    {answer}
                  </div>
                </div>
                <div ref={answerEndRef} />
              </div>
            ) : (
              <div className="flex h-full items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <p className="text-6xl mb-4">📚</p>
                  <p className="text-lg font-medium">문서에서 정보를 검색하세요</p>
                  <p className="mt-2 text-sm">
                    선택된 문서: <span className="font-medium text-sky-500">{selectedCount}</span>개
                  </p>
                  <p className="mt-4 text-xs text-muted-foreground">
                    질문을 입력하고 [질의] 버튼을 클릭하세요
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* References Panel */}
          {references.length > 0 && (
            <div className="w-96 border-l border-border flex flex-col">
              <div className="border-b border-border p-3">
                <h3 className="font-medium text-foreground">📎 근거 문서</h3>
                <p className="text-xs text-muted-foreground">
                  {references.length}개 참조 (클릭하면 팝업으로 열기)
                </p>
              </div>
              <div className="flex-1 overflow-y-auto p-2">
                {references.map((ref, index) => (
                  <button
                    key={`${ref.document_id}-${ref.chunk_id}-${index}`}
                    onClick={() => openReference(ref)}
                    className="w-full mb-2 rounded-lg border p-3 text-left transition border-border bg-surface-elevated hover:border-sky-500/50 hover:bg-sky-500/5"
                  >
                    <p className="text-sm font-medium text-foreground">
                      {ref.document_title}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {`${ref.page ?? 1}페이지`} •
                      점수: {ref.score.toFixed(2)}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                      {ref.snippet}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
      </div>

      <PdfViewerModal
        isOpen={pdfViewerOpen}
        onClose={() => {
          setPdfViewerOpen(false);
          setPdfBlob(null);
          setPdfHighlightSnippet(undefined);
          setPdfViewerHref(undefined);
        }}
        pdfBlob={pdfBlob}
        filename={pdfFilename}
        initialPage={pdfInitialPage}
        highlightSnippet={pdfHighlightSnippet}
        viewerHref={pdfViewerHref}
      />

      {/* History Drawer */}
      {showHistory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="max-h-[80vh] w-[600px] overflow-hidden rounded-2xl bg-surface-base border border-border shadow-xl">
            <div className="flex items-center justify-between border-b border-border p-4">
              <h3 className="font-semibold text-foreground">📜 질의 이력</h3>
              <button
                onClick={() => setShowHistory(false)}
                className="text-muted-foreground hover:text-foreground"
              >
                ✕
              </button>
            </div>
            <div className="max-h-[60vh] overflow-y-auto p-4">
              {queryHistory.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-4xl mb-2">📭</p>
                  <p className="text-muted-foreground">
                    질의 이력이 없습니다.
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    첫 질의를 시작해보세요!
                  </p>
                </div>
              ) : (
                queryHistory.map((entry) => (
                  <button
                    key={entry.id}
                    onClick={() => loadHistoryEntry(entry)}
                    className="mb-3 w-full rounded-lg border border-border bg-surface-elevated p-3 text-left hover:border-sky-500/50 transition"
                  >
                    <p className="font-medium text-foreground">{entry.query}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {new Date(entry.timestamp).toLocaleString()} •
                      {entry.document_count}개 문서 •
                      {entry.references.length}개 참조
                    </p>
                    <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
                      {entry.answer.slice(0, 100)}...
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Format bytes to human readable
 */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
