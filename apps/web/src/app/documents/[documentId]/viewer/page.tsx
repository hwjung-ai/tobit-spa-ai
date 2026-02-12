"use client";

import { Suspense } from "react";

import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams, useParams } from "next/navigation";
import dynamic from "next/dynamic";
import { getAuthHeaders } from "@/lib/apiClient/index";

// Lazy-load react-pdf to avoid SSR issues (uses browser-only APIs)
const ReactPdfDocument = dynamic(
  () => import("react-pdf").then((mod) => {
    mod.pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
    return mod.Document;
  }),
  { ssr: false }
);
const ReactPdfPage = dynamic(
  () => import("react-pdf").then((mod) => mod.Page),
  { ssr: false }
);

const sanitizeUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "";

interface ChunkInfo {
  chunk_id: string;
  document_id: string;
  page: number | null;
  text: string;
  snippet: string;
}

interface Reference {
  document_id: string;
  document_title: string;
  chunk_id: string;
  page: number | null;
  snippet: string;
  score?: number;
}

interface DocumentMeta {
  id: string;
  filename: string;
  tenant_id: string;
  user_id: string;
  status: string;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

interface Reference {
  document_id: string;
  document_title: string;
  chunk_id: string;
  page: number | null;
  snippet: string;
  score?: number;
}

function DocumentViewerContent() {
  const apiBaseUrl = sanitizeUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  const params = useParams();
  const documentId = params?.documentId;
  const router = useRouter();
  const searchParams = useSearchParams();
  const chunkId = searchParams?.get("chunkId") ?? undefined;
  const initialPageParam = Number(searchParams?.get("page") ?? 1) || 1;
  const referencesParam = searchParams?.get("references");

  const [currentPage, setCurrentPage] = useState(initialPageParam);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [chunkInfo, setChunkInfo] = useState<ChunkInfo | null>(null);
  const [chunkError, setChunkError] = useState<string | null>(null);
  const [documentMeta, setDocumentMeta] = useState<DocumentMeta | null>(null);
  const [pageWidth, setPageWidth] = useState(800);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(true);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [references, setReferences] = useState<Reference[]>([]);

  // Derive currentPage from searchParams and chunkInfo
  const derivedCurrentPage = Number(searchParams?.get("page") ?? chunkInfo?.page ?? 1) || 1;

  // Parse references from URL parameter
  useEffect(() => {
    if (referencesParam) {
      try {
        const decoded = decodeURIComponent(referencesParam);
        const parsedReferences = JSON.parse(decoded);
        if (Array.isArray(parsedReferences)) {
          setReferences(parsedReferences);
        }
      } catch (error) {
        console.error("Failed to parse references from URL:", error);
      }
    }
  }, [referencesParam]);

  // Restore references from sessionStorage on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = sessionStorage.getItem("codex-document-page-state");
      if (stored) {
        try {
          const parsed = JSON.parse(stored);
          if (parsed.references && Array.isArray(parsed.references)) {
            setReferences(parsed.references);
          }
        } catch (error) {
          console.error("Failed to restore references from sessionStorage:", error);
        }
      }
    }
  }, []);

  const highlightVisible = chunkInfo && chunkInfo.page === currentPage;

  const removeHighlightClasses = useCallback(() => {
    document.querySelectorAll(".codex-pdf-highlight").forEach((element) => {
      element.classList.remove("codex-pdf-highlight");
    });
  }, []);

  const highlightSnippet = useCallback(() => {
    if (!chunkInfo?.snippet || !highlightVisible) {
      return;
    }
    const textLayer = document.querySelector(
      `.react-pdf__Page[data-page-number="${currentPage}"] .react-pdf__Page__textContent`
    );
    if (!textLayer) {
      return;
    }
    const spans = Array.from(textLayer.querySelectorAll<HTMLSpanElement>("span"));
    if (!spans.length) {
      return;
    }
    removeHighlightClasses();
    const normalize = (value: string) => value.replace(/\s+/g, " ").trim().toLowerCase();
    const snippetNormalized = normalize(chunkInfo.snippet);
    const candidates = [
      snippetNormalized,
      snippetNormalized.slice(0, 60),
      snippetNormalized.slice(0, 20),
    ].filter((item) => item.length > 3);
    let targetSpan: HTMLSpanElement | undefined;
    for (const span of spans) {
      const spanText = span.textContent ? normalize(span.textContent) : "";
      if (!spanText) {
        continue;
      }
      for (const candidate of candidates) {
        if (spanText.includes(candidate)) {
          targetSpan = span;
          break;
        }
      }
      if (targetSpan) {
        break;
      }
    }
    if (!targetSpan) {
      targetSpan = spans[0];
    }
    const startIdx = spans.indexOf(targetSpan);
    const highlightRange = spans.slice(startIdx, Math.min(spans.length, startIdx + 3));
    highlightRange.forEach((span) => span.classList.add("codex-pdf-highlight"));
    targetSpan.scrollIntoView({ block: "center" });
  }, [chunkInfo, currentPage, highlightVisible, removeHighlightClasses]);

  const updatePageParam = useCallback(
    (page: number) => {
      const params = new URLSearchParams();
      params.set("page", page.toString());
      if (chunkId) {
        params.set("chunkId", chunkId);
      }
      if (references.length > 0) {
        params.set("references", encodeURIComponent(JSON.stringify(references)));
      }
      router.replace(`/documents/${documentId}/viewer?${params.toString()}`);
    },
    [chunkId, documentId, router, references]
  );

  useEffect(() => {
    const handleResize = () => {
      setPageWidth(Math.min(window.innerWidth - 64, 1024));
    };
    window.addEventListener("resize", handleResize);
    handleResize();
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    const fetchChunk = async () => {
      if (!chunkId) {
        setChunkInfo(null);
        setChunkError(null);
        return;
      }
      setChunkError(null);
      const response = await fetch(
        `${apiBaseUrl}/api/documents/${documentId}/chunks/${chunkId}`,
        { headers: getAuthHeaders() }
      );
      if (!response.ok) {
        setChunkError(
          response.status === 404
            ? "해당 근거 청크를 찾을 수 없습니다. 문서가 재색인되었을 수 있습니다."
            : `청크 조회 실패 (${response.status})`
        );
        return;
      }
      const payload = await response.json();
      setChunkInfo(payload.data.chunk);
    };
    void fetchChunk();
  }, [apiBaseUrl, chunkId, documentId]);

  // Update URL when chunkId changes
  useEffect(() => {
    if (chunkId) {
      const params = new URLSearchParams();
      params.set("chunkId", chunkId);
      if (currentPage) {
        params.set("page", currentPage.toString());
      }
      if (references.length > 0) {
        params.set("references", encodeURIComponent(JSON.stringify(references)));
      }
      router.replace(`/documents/${documentId}/viewer?${params.toString()}`, { scroll: false });
    }
  }, [chunkId, currentPage, documentId, router, references]);

  // Sync currentPage with derived value when it changes from external source
  useEffect(() => {
    setCurrentPage(derivedCurrentPage);
  }, [derivedCurrentPage]);

  useEffect(() => {
    if (!chunkInfo || !highlightVisible) {
      removeHighlightClasses();
      return;
    }

    // Retry highlighting up to 5 times with exponential backoff
    // This accounts for slow PDF rendering
    let retries = 0;
    const maxRetries = 5;
    const attemptHighlight = () => {
      const textLayer = document.querySelector(
        `.react-pdf__Page[data-page-number="${currentPage}"] .react-pdf__Page__textContent`
      );
      if (textLayer) {
        highlightSnippet();
        return true;
      }
      if (retries < maxRetries) {
        retries += 1;
        const delay = Math.min(100 * Math.pow(1.5, retries), 1000);
        window.setTimeout(attemptHighlight, delay);
      }
      return false;
    };

    const timeout = window.setTimeout(attemptHighlight, 100);
    return () => {
      window.clearTimeout(timeout);
      removeHighlightClasses();
    };
  }, [chunkInfo, highlightSnippet, highlightVisible, removeHighlightClasses, currentPage]);

  useEffect(() => {
    const fetchDocument = async () => {
      const response = await fetch(`${apiBaseUrl}/api/documents/${documentId}`, {
        headers: getAuthHeaders(),
      });
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      setDocumentMeta(payload.data.document);
    };
    void fetchDocument();
  }, [apiBaseUrl, documentId]);

  useEffect(() => {
    let revoked = false;
    setPdfLoading(true);
    setPdfError(null);
    const fetchPdf = async () => {
      const response = await fetch(
        `${apiBaseUrl}/api/documents/${documentId}/viewer`,
        { headers: getAuthHeaders() }
      );
      if (!response.ok) {
        if (!revoked) {
          setPdfError(`PDF 로드 실패 (${response.status})`);
          setPdfLoading(false);
        }
        return;
      }
      const blob = await response.blob();
      if (revoked) return;
      const url = URL.createObjectURL(blob);
      setPdfBlobUrl(url);
      setPdfLoading(false);
    };
    void fetchPdf();
    return () => {
      revoked = true;
      setPdfBlobUrl((prev) => {
        if (prev) URL.revokeObjectURL(prev);
        return null;
      });
    };
  }, [apiBaseUrl, documentId]);

  // Update URL when page changes
  useEffect(() => {
    if (currentPage) {
      const params = new URLSearchParams();
      params.set("page", currentPage.toString());
      if (chunkId) {
        params.set("chunkId", chunkId);
      }
      if (references.length > 0) {
        params.set("references", encodeURIComponent(JSON.stringify(references)));
      }
      router.replace(`/documents/${documentId}/viewer?${params.toString()}`, { scroll: false });
    }
  }, [currentPage, chunkId, documentId, router, references]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        if (currentPage > 1) {
          const prev = currentPage - 1;
          setCurrentPage(prev);
        }
      } else if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        if (numPages !== null && currentPage < numPages) {
          const next = currentPage + 1;
          setCurrentPage(next);
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [currentPage, numPages]);

  const handlePrevious = () => {
    if (currentPage <= 1) return;
    const previous = currentPage - 1;
    setCurrentPage(previous);
  };

  const handleNext = () => {
    if (numPages !== null && currentPage >= numPages) return;
    const next = currentPage + 1;
    setCurrentPage(next);
  };

  const handleDownload = () => {
    if (!pdfBlobUrl) return;
    const a = window.document.createElement("a");
    a.href = pdfBlobUrl;
    a.download = documentMeta?.filename ?? "document.pdf";
    a.click();
  };

  const handleDocumentLoadSuccess = ({ numPages: total }: { numPages: number }) => {
    setNumPages(total);
    if (currentPage > total) {
      setCurrentPage(total);
      updatePageParam(total);
    }
  };

  const highlightInfo = useMemo(() => {
    if (!chunkInfo) {
      return null;
    }
    return {
      label: chunkInfo.snippet,
    };
  }, [chunkInfo]);

  if (!documentId) {
    return (
      <div className="p-6 text-sm text-rose-400">
        문서 ID가 없습니다. 문서 목록에서 선택해 주세요.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between rounded-2xl border dark: dark:/70 p-6" style={{backgroundColor: "var(--surface-base)", borderColor: "var(--border)"}}>
        <div>
          <p className="text-xs uppercase tracking-[0.3em] " style={{color: "var(--muted-foreground)"}}>문서 뷰어</p>
          <h2 className="text-2xl font-semibold dark:" style={{color: "var(--foreground)"}}>
            {documentMeta?.filename ?? "문서 불러오는 중..."}
          </h2>
          {chunkInfo ? (
            <p className="text-xs " style={{color: "var(--muted-foreground)"}}>
              근거 청크 하이라이트 중 · {chunkInfo.page != null ? `${chunkInfo.page}페이지` : "페이지 미확인"}
            </p>
          ) : null}
          {chunkError ? (
            <p className="text-xs text-amber-400">{chunkError}</p>
          ) : null}
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => {
              if (window.history.length > 1) {
                window.history.back();
                return;
              }
              router.push("/documents");
            }}
            className="rounded-2xl border  px-4 py-2 text-xs uppercase tracking-[0.3em]  transition hover:" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)"}}
          >
            문서 목록
          </button>
          {pdfBlobUrl && (
            <button
              onClick={handleDownload}
              className="rounded-2xl border  px-4 py-2 text-xs uppercase tracking-[0.3em]  transition hover:" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)"}}
            >
              다운로드
            </button>
          )}
          <div className="flex gap-2">
            <button
              onClick={handlePrevious}
              className="rounded-2xl border  px-4 py-2 text-xs uppercase tracking-[0.3em]  transition hover: disabled:opacity-50" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)"}}
              disabled={currentPage <= 1}
            >
              이전
            </button>
            <button
              onClick={handleNext}
              className="rounded-2xl border  px-4 py-2 text-xs uppercase tracking-[0.3em]  transition hover: disabled:opacity-50" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)"}}
              disabled={numPages !== null && currentPage >= numPages}
            >
              다음
            </button>
          </div>
        </div>
      </header>

      <section className="rounded-2xl border dark: dark:/70 p-6" style={{backgroundColor: "var(--surface-base)", borderColor: "var(--border)"}}>
        <div className="mb-4 flex items-center justify-between text-xs " style={{color: "var(--muted-foreground)"}}>
          <span>{currentPage}페이지</span>
          {numPages ? <span>전체 {numPages}페이지</span> : <span>페이지 로딩 중...</span>}
          <span className="text-[10px] " style={{color: "var(--muted-foreground)"}}>방향키(←→)로 페이지 이동</span>
        </div>
        <div className="relative flex justify-center">
          <div className="relative">
            {pdfLoading && (
              <div className="flex h-[600px] w-full items-center justify-center">
                <div className="flex flex-col items-center gap-3">
                  <div className="h-8 w-8 animate-spin rounded-full border-2 border-t-sky-400" style={{borderColor: "var(--border)"}} />
                  <span className="text-sm " style={{color: "var(--muted-foreground)"}}>PDF 불러오는 중...</span>
                </div>
              </div>
            )}
            {pdfError && (
              <div className="flex h-[400px] w-full items-center justify-center">
                <div className="text-center">
                  <p className="text-sm text-rose-400">{pdfError}</p>
                  <button
                    onClick={() => window.location.reload()}
                    className="mt-3 rounded-2xl border  px-4 py-2 text-xs  transition hover:" style={{borderColor: "var(--border)", color: "var(--foreground-secondary)"}}
                  >
                    다시 시도
                  </button>
                </div>
              </div>
            )}
            {highlightVisible && (
              <div className="pointer-events-none absolute inset-0 z-10">
                <div className="absolute inset-3 rounded-2xl border-2 border-amber-400 bg-amber-500/20" />
                <p className="absolute left-4 top-4 max-w-[60vw] text-[10px] text-amber-100">
                  {highlightInfo?.label}
                </p>
              </div>
            )}
            {pdfBlobUrl && (
              <ReactPdfDocument
                file={pdfBlobUrl}
                onLoadSuccess={handleDocumentLoadSuccess}
              >
                <ReactPdfPage pageNumber={currentPage} width={pageWidth} />
              </ReactPdfDocument>
            )}
          </div>
        </div>
      </section>

      {/* References Section */}
      {references.length > 0 && (
        <section className="rounded-2xl border dark: dark:/70 p-6" style={{backgroundColor: "var(--surface-base)", borderColor: "var(--border)"}}>
          <div className="mb-3 flex items-center justify-between text-[10px] uppercase tracking-[0.3em] " style={{color: "var(--muted-foreground)"}}>
            <span>근거 문서 ({references.length}건)</span>
          </div>
          <div className="space-y-3">
            {references.map((reference, index) => {
              const isCurrentDocument = reference.document_id === documentId;
              return (
                <div
                  key={`${reference.document_id}-${reference.chunk_id}-${index}`}
                  className={`block rounded-2xl border p-4 transition ${
                    isCurrentDocument
                      ? "border-amber-400 bg-amber-500/10"
                      : " dark:  hover:"
                  }`} style={{backgroundColor: "var(--surface-overlay)", borderColor: "var(--border)"}}
                >
                  <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.3em] " style={{color: "var(--muted-foreground)"}}>
                    <span>{reference.document_title}</span>
                    <span>{reference.page != null ? `${reference.page}페이지` : "페이지 미확인"}</span>
                  </div>
                  <p className="mt-2 text-xs  line-clamp-3" style={{color: "var(--foreground-secondary)"}}>{reference.snippet}</p>
                  {reference.score != null && (
                    <p className="mt-2 text-[10px] " style={{color: "var(--muted-foreground)"}}>유사도 {(reference.score * 100).toFixed(1)}%</p>
                  )}
                  {isCurrentDocument && (
                    <p className="mt-2 text-xs text-amber-400">현재 문서</p>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}

      <style jsx global>{`
        .codex-pdf-highlight {
          background-color: rgba(250, 208, 100, 0.6);
          border-radius: 2px;
          padding: 0;
        }
      `}</style>
    </div>
  );
}

export default function DocumentViewerPage() {
  return (
    <Suspense fallback={<div className="p-4 " style={{color: "var(--muted-foreground)"}}>불러오는 중...</div>}>
      <DocumentViewerContent />
    </Suspense>
  );
}
