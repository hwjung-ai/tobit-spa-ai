"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import dynamic from "next/dynamic";
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

import { getAuthHeaders } from "@/lib/apiClient/index";

interface PdfViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** PDF blob URL (already created with URL.createObjectURL) */
  pdfBlobUrl: string | null;
  /** Optional filename for download */
  filename?: string;
  /** Optional initial page number (1-indexed) */
  initialPage?: number;
}

/**
 * Reusable PDF viewer modal component.
 * Displays PDF in a modal with download support.
 *
 * Usage:
 * 1. Fetch PDF blob using fetchWithAuth
 * 2. Create blob URL with URL.createObjectURL(blob)
 * 3. Pass blobUrl and filename to this component
 * 4. Component handles cleanup on unmount
 */
export function PdfViewerModal({
  isOpen,
  onClose,
  pdfBlobUrl,
  filename = "document.pdf",
  initialPage,
}: PdfViewerModalProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(initialPage || 1);
  const [pageWidth, setPageWidth] = useState<number>(800);
  const [pdfLoading, setPdfLoading] = useState<boolean>(true);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const prevBlobUrlRef = useRef<string | null>(null);

  // Calculate page width based on container
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth - 64; // padding
        setPageWidth(Math.min(containerWidth, 1024));
      }
    };
    window.addEventListener("resize", handleResize);
    handleResize();
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Reset state when modal opens with new PDF
  useEffect(() => {
    if (!isOpen) {
      setNumPages(0);
      setPdfError(null);
      prevBlobUrlRef.current = null;
      return;
    }

    // Only reset loading state when blobUrl actually changes
    if (pdfBlobUrl !== prevBlobUrlRef.current) {
      prevBlobUrlRef.current = pdfBlobUrl;
      setCurrentPage(initialPage || 1);
      setPdfLoading(true);
      setPdfError(null);
    }
  }, [isOpen, pdfBlobUrl, initialPage]);

  // Calculate page width based on container
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const containerWidth = containerRef.current.clientWidth - 64; // padding
        setPageWidth(Math.min(containerWidth, 1024));
      }
    };
    window.addEventListener("resize", handleResize);
    handleResize();
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (!isOpen) {
      setNumPages(0);
      setPdfError(null);
    }
  }, [isOpen]);

  // Update page when initialPage or pdfBlobUrl changes
  useEffect(() => {
    if (isOpen && pdfBlobUrl) {
      setCurrentPage(initialPage || 1);
      setPdfLoading(true);
      setPdfError(null);
    }
  }, [isOpen, pdfBlobUrl, initialPage]);

  // Handle PDF load success
  const onDocumentLoadSuccess = useCallback(({ numPages: pages }: { numPages: number }) => {
    setNumPages(pages);
    setPdfLoading(false);
    setPdfError(null);
  }, []);

  // Handle PDF load error
  const onDocumentLoadError = useCallback((error: Error) => {
    console.error("PDF load error:", error);
    setPdfError("PDF를 불러오는데 실패했습니다.");
    setPdfLoading(false);
  }, []);

  // Handle download
  const handleDownload = useCallback(() => {
    if (!pdfBlobUrl) return;
    const link = document.createElement("a");
    link.href = pdfBlobUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }, [pdfBlobUrl, filename]);

  // Handle page navigation
  const goToPreviousPage = useCallback(() => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  }, []);

  const goToNextPage = useCallback(() => {
    setCurrentPage((prev) => Math.min(numPages, prev + 1));
  }, [numPages]);

  // Handle key events
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowLeft") {
        goToPreviousPage();
      } else if (e.key === "ArrowRight") {
        goToNextPage();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, goToPreviousPage, goToNextPage]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        ref={containerRef}
        className="relative h-[90vh] w-[95vw] max-w-6xl overflow-hidden rounded-2xl bg-slate-900 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-700 bg-slate-800 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="text-lg">📄</span>
            <span className="max-w-md truncate text-sm font-medium text-white">
              {filename}
            </span>
          </div>
          <div className="flex items-center gap-2">
            {/* Page navigation */}
            {numPages > 1 && (
              <div className="flex items-center gap-1 rounded-lg bg-slate-700 px-2 py-1">
                <button
                  type="button"
                  onClick={goToPreviousPage}
                  disabled={currentPage <= 1}
                  className="rounded p-1 text-slate-300 transition hover:bg-slate-600 disabled:opacity-30 disabled:hover:bg-transparent"
                  aria-label="이전 페이지"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                </button>
                <span className="min-w-[60px] text-center text-xs text-slate-300">
                  {currentPage} / {numPages}
                </span>
                <button
                  type="button"
                  onClick={goToNextPage}
                  disabled={currentPage >= numPages}
                  className="rounded p-1 text-slate-300 transition hover:bg-slate-600 disabled:opacity-30 disabled:hover:bg-transparent"
                  aria-label="다음 페이지"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </button>
              </div>
            )}

            {/* Download button */}
            <button
              type="button"
              onClick={handleDownload}
              className="rounded-lg bg-sky-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-sky-700 disabled:opacity-50"
              aria-label="PDF 다운로드"
            >
              다운로드
            </button>

            {/* Close button */}
            <button
              type="button"
              onClick={onClose}
              className="rounded-full p-1.5 text-slate-400 transition hover:bg-slate-700 hover:text-white"
              aria-label="닫기"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex h-[calc(100%-60px)] items-center justify-center overflow-auto bg-slate-950 p-4">
          {pdfLoading && (
            <div className="flex flex-col items-center gap-3">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-600 border-t-sky-500" />
              <p className="text-sm text-slate-400">PDF를 불러오는 중...</p>
            </div>
          )}

          {pdfError && (
            <div className="text-center">
              <div className="mb-3 text-4xl">⚠️</div>
              <p className="text-red-400">{pdfError}</p>
            </div>
          )}

          {!pdfLoading && !pdfError && pdfBlobUrl && (
            <div className="flex h-full flex-col items-center">
              <ReactPdfDocument
                file={pdfBlobUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                loading={<div className="text-slate-400">로딩 중...</div>}
                error={<div className="text-red-400">PDF 로드 실패</div>}
                className="flex flex-col items-center"
              >
                <ReactPdfPage
                  pageNumber={currentPage}
                  width={pageWidth}
                  loading={<div className="text-slate-400">페이지 로딩 중...</div>}
                  error={<div className="text-red-400">페이지 로드 실패</div>}
                />
              </ReactPdfDocument>
            </div>
          )}
        </div>

        {/* Footer hints */}
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full bg-slate-800/80 px-4 py-1.5 text-xs text-slate-400 backdrop-blur-sm">
          ESC로 닫기 • 방향키로 페이지 이동
        </div>
      </div>
    </div>
  );
}
