"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { getAuthHeaders } from "@/lib/apiClient/index";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

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

export default function PdfViewerPage() {
  const searchParams = useSearchParams();
  const documentId = searchParams?.get("documentId") || "";
  const initialPageParam = searchParams?.get("page") || "1";
  const highlightText = searchParams?.get("highlight") || "";

  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(parseInt(initialPageParam) || 1);
  const [pageWidth, setPageWidth] = useState<number>(900);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pdfFile, setPdfFile] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Fetch PDF blob
  useEffect(() => {
    const fetchPdf = async () => {
      if (!documentId) {
        setError("문서 ID가 없습니다.");
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`/api/documents/${documentId}/viewer`, {
          headers: getAuthHeaders(),
        });

        if (!response.ok) {
          throw new Error(`PDF 로드 실패: ${response.statusText}`);
        }

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        setPdfFile(url);
      } catch (err) {
        setError(err instanceof Error ? err.message : "PDF 로드 실패");
      } finally {
        setLoading(false);
      }
    };

    fetchPdf();
  }, [documentId]);

  // Highlight text on page
  useEffect(() => {
    if (!highlightText) return;

    const highlightSearchText = () => {
      const pageContainer = document.querySelector('[data-page-number]');
      if (!pageContainer) return;

      // Get all text nodes
      const walker = document.createTreeWalker(
        pageContainer,
        NodeFilter.SHOW_TEXT,
        null
      );

      const nodesToReplace: Array<{ node: Node; parent: Node }> = [];
      let node;

      while ((node = walker.nextNode())) {
        if (node.textContent?.toLowerCase().includes(highlightText.toLowerCase())) {
          nodesToReplace.push({ node, parent: node.parentNode! });
        }
      }

      // Replace text with highlighted version
      nodesToReplace.forEach(({ node, parent }) => {
        const text = node.textContent || "";
        const regex = new RegExp(`(${highlightText})`, "gi");
        const highlighted = text.replace(regex, "<mark>$1</mark>");

        if (text !== highlighted) {
          const span = document.createElement("span");
          span.innerHTML = highlighted;
          parent.replaceChild(span, node);
        }
      });
    };

    // Use setTimeout to ensure DOM is ready
    const timer = setTimeout(highlightSearchText, 500);
    return () => clearTimeout(timer);
  }, [highlightText, currentPage, pdfFile]);

  // Handle window resize for responsive sizing
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const width = Math.max(400, containerRef.current.clientWidth - 40);
        setPageWidth(width);
      }
    };

    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    // Ensure current page is within range
    if (parseInt(initialPageParam) > numPages) {
      setCurrentPage(Math.max(1, numPages));
    }
  };

  const onRenderTextLayerError = useCallback((error: Error) => {
    if (error?.name === "AbortException") {
      return;
    }
    console.warn("PDF text layer render error:", error);
  }, []);

  return (
    <div className="min-h-screen bg-surface-base flex flex-col">
      {/* Header */}
      <div className="flex flex-col gap-3 border-b border-border bg-surface-elevated p-3 md:p-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="text-lg font-semibold text-foreground whitespace-nowrap">문서 보기</h1>
          <p className="truncate text-xs text-muted-foreground md:text-sm">
            {loading && "로딩 중..."}
            {error && `오류: ${error}`}
            {!loading && !error && `${currentPage} / ${numPages} 페이지`}
          </p>
        </div>

        {/* Controls */}
        <div className="flex w-full flex-wrap items-center gap-2 lg:w-auto lg:justify-end">
          {highlightText && (
            <div className="max-w-full truncate rounded bg-yellow-500/20 px-3 py-1 text-xs text-yellow-700 dark:text-yellow-400 md:max-w-[36rem] md:text-sm">
              하이라이트: "{highlightText}"
            </div>
          )}

          <div className="flex shrink-0 items-center gap-2">
            <button
              onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
              disabled={currentPage <= 1 || loading}
              className="whitespace-nowrap rounded bg-surface-base px-3 py-1 text-foreground hover:bg-surface-elevated disabled:opacity-50"
            >
              ← 이전
            </button>

            <input
              type="number"
              min="1"
              max={numPages}
              value={currentPage}
              onChange={(e) => {
                const page = parseInt(e.target.value) || 1;
                setCurrentPage(Math.max(1, Math.min(page, numPages)));
              }}
              className="w-16 rounded border border-border bg-surface-base px-2 py-1 text-center text-foreground"
              disabled={loading}
            />

            <button
              onClick={() => setCurrentPage(Math.min(numPages, currentPage + 1))}
              disabled={currentPage >= numPages || loading}
              className="whitespace-nowrap rounded bg-surface-base px-3 py-1 text-foreground hover:bg-surface-elevated disabled:opacity-50"
            >
              다음 →
            </button>
          </div>

          <button
            onClick={() => window.close()}
            className="shrink-0 whitespace-nowrap rounded bg-rose-500/20 px-3 py-1 text-rose-600 hover:bg-rose-500/30 dark:text-rose-400"
          >
            닫기
          </button>
        </div>
      </div>

      {/* PDF Content */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto flex items-center justify-center p-5 bg-surface-base"
      >
        {loading && (
          <div className="text-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-sky-500 border-t-transparent mx-auto mb-4" />
            <p className="text-muted-foreground">PDF 로딩 중...</p>
          </div>
        )}

        {error && (
          <div className="text-center">
            <p className="text-rose-600 dark:text-rose-400 mb-4">
              ❌ {error}
            </p>
            <button
              onClick={() => window.close()}
              className="px-4 py-2 bg-surface-elevated hover:bg-sky-500/10 rounded text-foreground"
            >
              창 닫기
            </button>
          </div>
        )}

        {pdfFile && !loading && !error && (
          <ReactPdfDocument file={pdfFile} onLoadSuccess={onDocumentLoadSuccess}>
            <ReactPdfPage
              pageNumber={currentPage}
              width={pageWidth}
              renderTextLayer
              renderAnnotationLayer
              onRenderTextLayerError={onRenderTextLayerError}
            />
          </ReactPdfDocument>
        )}
      </div>
    </div>
  );
}
