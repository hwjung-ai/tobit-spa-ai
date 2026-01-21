"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams, useParams } from "next/navigation";
import { Document, Page, pdfjs } from "react-pdf";
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

const sanitizeUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "http://localhost:8000";

interface ChunkInfo {
  chunk_id: string;
  document_id: string;
  page: number | null;
  text: string;
  snippet: string;
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

export default function DocumentViewerPage() {
  const apiBaseUrl = sanitizeUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  const params = useParams();
  const documentId = params?.documentId;
  const router = useRouter();
  const searchParams = useSearchParams();
  const chunkId = searchParams?.get("chunkId") ?? undefined;
  const initialPageParam = Number(searchParams?.get("page") ?? 1) || 1;

  const [currentPage, setCurrentPage] = useState(initialPageParam);
  const [numPages, setNumPages] = useState<number | null>(null);
  const [chunkInfo, setChunkInfo] = useState<ChunkInfo | null>(null);
  const [documentMeta, setDocumentMeta] = useState<DocumentMeta | null>(null);
  const [pageWidth, setPageWidth] = useState(800);

  // Derive currentPage from searchParams and chunkInfo
  const derivedCurrentPage = Number(searchParams?.get("page") ?? chunkInfo?.page ?? 1) || 1;

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
      const params = new URLSearchParams(searchParams?.toString() ?? "");
      params.set("page", page.toString());
      if (chunkId) {
        params.set("chunkId", chunkId);
      }
      router.replace(`/documents/${documentId}/viewer?${params.toString()}`);
    },
    [chunkId, documentId, router, searchParams]
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
        return;
      }
      const response = await fetch(
        `${apiBaseUrl}/documents/${documentId}/chunks/${chunkId}`,
        {
          headers: {
            "X-Tenant-Id": "default",
            "X-User-Id": "default",
          },
        }
      );
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      setChunkInfo(payload.data.chunk);
    };
    void fetchChunk();
  }, [apiBaseUrl, chunkId, documentId]);

  // Sync currentPage with derived value when it changes from external source
  useEffect(() => {
    setCurrentPage(derivedCurrentPage);
  }, [derivedCurrentPage]);

  useEffect(() => {
    if (!chunkInfo || !highlightVisible) {
      removeHighlightClasses();
      return;
    }
    const timeout = window.setTimeout(() => {
      highlightSnippet();
    }, 100);
    return () => {
      window.clearTimeout(timeout);
      removeHighlightClasses();
    };
  }, [chunkInfo, highlightSnippet, highlightVisible, removeHighlightClasses]);

  useEffect(() => {
    const fetchDocument = async () => {
      const response = await fetch(`${apiBaseUrl}/documents/${documentId}`, {
        headers: {
          "X-Tenant-Id": "default",
          "X-User-Id": "default",
        },
      });
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      setDocumentMeta(payload.data.document);
    };
    void fetchDocument();
  }, [apiBaseUrl, documentId]);

  const handlePrevious = () => {
    if (currentPage <= 1) return;
    const previous = currentPage - 1;
    setCurrentPage(previous);
    updatePageParam(previous);
  };

  const handleNext = () => {
    if (numPages !== null && currentPage >= numPages) return;
    const next = currentPage + 1;
    setCurrentPage(next);
    updatePageParam(next);
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
        Document ID is unavailable. Please navigate from the document list.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Document Viewer</p>
          <h2 className="text-2xl font-semibold text-white">
            {documentMeta?.filename ?? "Loading document..."}
          </h2>
          {chunkInfo ? (
            <p className="text-xs text-slate-400">
              Highlighting reference chunk {chunkInfo.chunk_id} · Page {chunkInfo.page ?? "?"}
            </p>
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
            className="rounded-2xl border border-slate-700 px-4 py-2 text-xs uppercase tracking-[0.3em] text-slate-200 transition hover:border-slate-400"
          >
            Back to Document List
          </button>
          <div className="flex gap-2">
            <button
              onClick={handlePrevious}
              className="rounded-2xl border border-slate-700 px-4 py-2 text-xs uppercase tracking-[0.3em] text-slate-200 transition hover:border-slate-400 disabled:opacity-50"
              disabled={currentPage <= 1}
            >
              Previous
            </button>
            <button
              onClick={handleNext}
              className="rounded-2xl border border-slate-700 px-4 py-2 text-xs uppercase tracking-[0.3em] text-slate-200 transition hover:border-slate-400 disabled:opacity-50"
              disabled={numPages !== null && currentPage >= numPages}
            >
              Next
            </button>
          </div>
        </div>
      </header>

      <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="mb-4 flex items-center justify-between text-xs text-slate-400">
          <span>Page {currentPage}</span>
          {numPages ? <span>{numPages} pages</span> : <span>Loading pages...</span>}
        </div>
        <div className="relative flex justify-center">
          <div className="relative">
            {highlightVisible && (
              <div className="pointer-events-none absolute inset-0">
                <div className="absolute inset-3 rounded-3xl border-2 border-amber-400 bg-amber-500/20" />
                <p className="absolute left-4 top-4 max-w-[60vw] text-[10px] text-amber-100">
                  {highlightInfo?.label}
                </p>
              </div>
            )}
            <Document
              file={`${apiBaseUrl}/documents/${documentId}/viewer`}
              onLoadSuccess={handleDocumentLoadSuccess}
            >
              <Page pageNumber={currentPage} width={pageWidth} />
            </Document>
          </div>
        </div>
      </section>
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
