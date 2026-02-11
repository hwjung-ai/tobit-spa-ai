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
interface PdfViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  /** PDF blob (pass Blob directly instead of blob URL for better reliability) */
  pdfBlob?: Blob | null;
  /** Backward compatibility: blob URL or PDF URL string */
  pdfBlobUrl?: string | null;
  /** Optional filename for download */
  filename?: string;
  /** Optional initial page number (1-indexed) */
  initialPage?: number;
  /** Optional full-page viewer URL (for switching viewer mode) */
  viewerHref?: string;
  /** Optional snippet text to highlight on current page */
  highlightSnippet?: string;
}

type ResizeDirection = "n" | "s" | "e" | "w" | "ne" | "nw" | "se" | "sw";

interface ModalRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

const MIN_MODAL_WIDTH = 720;
const MIN_MODAL_HEIGHT = 520;
const VIEWPORT_MARGIN = 8;

/**
 * Reusable PDF viewer modal component.
 * Displays PDF in a modal with download support.
 *
 * Usage:
 * 1. Fetch PDF blob using fetchWithAuth
 * 2. Pass blob directly (not blob URL) to this component
 * 3. Component handles creating and cleaning up blob URL
 */
export function PdfViewerModal({
  isOpen,
  onClose,
  pdfBlob = null,
  pdfBlobUrl,
  filename = "document.pdf",
  initialPage,
  viewerHref,
  highlightSnippet,
}: PdfViewerModalProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(initialPage || 1);
  const [pageWidth, setPageWidth] = useState<number>(800);
  const [pdfLoading, setPdfLoading] = useState<boolean>(true);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [pdfFile, setPdfFile] = useState<File | string | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [modalRect, setModalRect] = useState<ModalRect>({ x: 0, y: 0, width: 0, height: 0 });
  const containerRef = useRef<HTMLDivElement>(null);
  const previousRectRef = useRef<ModalRect | null>(null);
  const interactionRef = useRef<{
    mode: "move" | "resize";
    direction?: ResizeDirection;
    startX: number;
    startY: number;
    startRect: ModalRect;
  } | null>(null);

  const removeHighlightClasses = useCallback(() => {
    document.querySelectorAll(".codex-pdf-highlight").forEach((element) => {
      element.classList.remove("codex-pdf-highlight");
    });
  }, []);

  const applySnippetHighlight = useCallback(() => {
    if (!highlightSnippet?.trim() || pdfLoading || pdfError) {
      return false;
    }
    const textLayer = document.querySelector(
      `.react-pdf__Page[data-page-number="${currentPage}"] .react-pdf__Page__textContent`
    );
    if (!textLayer) {
      return false;
    }
    const spans = Array.from(textLayer.querySelectorAll<HTMLSpanElement>("span"));
    if (!spans.length) {
      return false;
    }

    const normalize = (value: string) => value.replace(/\s+/g, " ").trim().toLowerCase();
    const snippetNormalized = normalize(highlightSnippet);
    if (!snippetNormalized) {
      return false;
    }
    const candidates = [
      snippetNormalized,
      snippetNormalized.slice(0, 60),
      snippetNormalized.slice(0, 24),
    ].filter((item) => item.length > 3);

    removeHighlightClasses();
    let targetSpan: HTMLSpanElement | undefined;
    for (const span of spans) {
      const spanText = span.textContent ? normalize(span.textContent) : "";
      if (!spanText) {
        continue;
      }
      if (candidates.some((candidate) => spanText.includes(candidate))) {
        targetSpan = span;
        break;
      }
    }
    if (!targetSpan) {
      return false;
    }
    const startIdx = spans.indexOf(targetSpan);
    const highlightRange = spans.slice(startIdx, Math.min(spans.length, startIdx + 3));
    highlightRange.forEach((span) => span.classList.add("codex-pdf-highlight"));
    targetSpan.scrollIntoView({ block: "center", behavior: "smooth" });
    return true;
  }, [highlightSnippet, pdfLoading, pdfError, currentPage, removeHighlightClasses]);

  const getInitialRect = useCallback((): ModalRect => {
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const width = Math.min(viewportWidth * 0.95, 1400);
    const height = Math.min(viewportHeight * 0.9, 1000);
    return {
      x: Math.max(VIEWPORT_MARGIN, (viewportWidth - width) / 2),
      y: Math.max(VIEWPORT_MARGIN, (viewportHeight - height) / 2),
      width,
      height,
    };
  }, []);

  const clampRect = useCallback((rect: ModalRect): ModalRect => {
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const maxWidth = Math.max(320, viewportWidth - VIEWPORT_MARGIN * 2);
    const maxHeight = Math.max(280, viewportHeight - VIEWPORT_MARGIN * 2);
    const minWidth = Math.min(MIN_MODAL_WIDTH, maxWidth);
    const minHeight = Math.min(MIN_MODAL_HEIGHT, maxHeight);

    const width = Math.min(Math.max(rect.width, minWidth), maxWidth);
    const height = Math.min(Math.max(rect.height, minHeight), maxHeight);
    const x = Math.min(
      Math.max(rect.x, VIEWPORT_MARGIN),
      Math.max(VIEWPORT_MARGIN, viewportWidth - width - VIEWPORT_MARGIN)
    );
    const y = Math.min(
      Math.max(rect.y, VIEWPORT_MARGIN),
      Math.max(VIEWPORT_MARGIN, viewportHeight - height - VIEWPORT_MARGIN)
    );

    return { x, y, width, height };
  }, []);

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

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const initial = getInitialRect();
    setModalRect(clampRect(initial));
    setIsFullscreen(false);
  }, [isOpen, getInitialRect, clampRect]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handleViewportResize = () => {
      if (isFullscreen) {
        setModalRect({
          x: VIEWPORT_MARGIN,
          y: VIEWPORT_MARGIN,
          width: Math.max(320, window.innerWidth - VIEWPORT_MARGIN * 2),
          height: Math.max(280, window.innerHeight - VIEWPORT_MARGIN * 2),
        });
        return;
      }
      setModalRect((prev) => clampRect(prev));
    };

    window.addEventListener("resize", handleViewportResize);
    return () => window.removeEventListener("resize", handleViewportResize);
  }, [isOpen, isFullscreen, clampRect]);

  // Convert blob to File and manage state
  useEffect(() => {
    if (!isOpen) {
      setPdfLoading(true);
      setPdfError(null);
      setNumPages(0);
      setPdfFile(null);
      return;
    }

    if (!pdfBlob && !pdfBlobUrl) {
      setPdfFile(null);
      return;
    }

    if (pdfBlob) {
      // Convert blob to File (react-pdf handles File objects better)
      const file = new File([pdfBlob], filename, { type: pdfBlob.type || "application/pdf" });
      setPdfFile(file);
    } else if (pdfBlobUrl) {
      setPdfFile(pdfBlobUrl);
    }

    setCurrentPage(initialPage || 1);
    setPdfLoading(true);
    setPdfError(null);
    setNumPages(0);
  }, [isOpen, pdfBlob, pdfBlobUrl, filename, initialPage]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    if (!highlightSnippet?.trim()) {
      removeHighlightClasses();
      return;
    }
    let cancelled = false;
    let retries = 0;
    const maxRetries = 6;
    const run = () => {
      if (cancelled) {
        return;
      }
      const done = applySnippetHighlight();
      if (done) {
        return;
      }
      if (retries >= maxRetries) {
        return;
      }
      retries += 1;
      const delay = Math.min(100 * Math.pow(1.5, retries), 1000);
      window.setTimeout(run, delay);
    };
    const timer = window.setTimeout(run, 120);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      removeHighlightClasses();
    };
  }, [isOpen, currentPage, highlightSnippet, applySnippetHighlight, removeHighlightClasses]);

  // Handle PDF load success
  const onDocumentLoadSuccess = useCallback(({ numPages: pages }: { numPages: number }) => {
    console.log("PDF loaded successfully, pages:", pages);
    setNumPages(pages);
    // Set loading to false immediately when document is loaded
    // The page will render asynchronously
    setPdfLoading(false);
    setPdfError(null);
  }, []);

  // Handle PDF load error
  const onDocumentLoadError = useCallback((error: Error) => {
    console.error("PDF load error:", error);
    setPdfError(`PDF 로드 실패: ${error.message || error.name || '알 수 없는 오류'}`);
    setPdfLoading(false);
  }, []);

  const toggleFullscreen = useCallback(() => {
    if (isFullscreen) {
      setIsFullscreen(false);
      if (previousRectRef.current) {
        setModalRect(clampRect(previousRectRef.current));
      } else {
        setModalRect(clampRect(getInitialRect()));
      }
      return;
    }
    previousRectRef.current = modalRect;
    setIsFullscreen(true);
    setModalRect({
      x: VIEWPORT_MARGIN,
      y: VIEWPORT_MARGIN,
      width: Math.max(320, window.innerWidth - VIEWPORT_MARGIN * 2),
      height: Math.max(280, window.innerHeight - VIEWPORT_MARGIN * 2),
    });
  }, [isFullscreen, modalRect, clampRect, getInitialRect]);

  const startMove = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (isFullscreen) {
        return;
      }
      event.preventDefault();
      interactionRef.current = {
        mode: "move",
        startX: event.clientX,
        startY: event.clientY,
        startRect: modalRect,
      };
    },
    [isFullscreen, modalRect]
  );

  const startResize = useCallback(
    (direction: ResizeDirection) => (event: React.MouseEvent<HTMLDivElement>) => {
      if (isFullscreen) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      interactionRef.current = {
        mode: "resize",
        direction,
        startX: event.clientX,
        startY: event.clientY,
        startRect: modalRect,
      };
    },
    [isFullscreen, modalRect]
  );

  useEffect(() => {
    const onMouseMove = (event: MouseEvent) => {
      if (!interactionRef.current) {
        return;
      }
      const { mode, direction, startX, startY, startRect } = interactionRef.current;
      const dx = event.clientX - startX;
      const dy = event.clientY - startY;

      if (mode === "move") {
        setModalRect(
          clampRect({
            ...startRect,
            x: startRect.x + dx,
            y: startRect.y + dy,
          })
        );
        return;
      }

      if (!direction) {
        return;
      }

      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const maxWidth = Math.max(320, viewportWidth - VIEWPORT_MARGIN * 2);
      const maxHeight = Math.max(280, viewportHeight - VIEWPORT_MARGIN * 2);
      const minWidth = Math.min(MIN_MODAL_WIDTH, maxWidth);
      const minHeight = Math.min(MIN_MODAL_HEIGHT, maxHeight);

      const startLeft = startRect.x;
      const startTop = startRect.y;
      const startRight = startRect.x + startRect.width;
      const startBottom = startRect.y + startRect.height;

      let left = startLeft;
      let right = startRight;
      let top = startTop;
      let bottom = startBottom;

      if (direction.includes("e")) right = startRight + dx;
      if (direction.includes("w")) left = startLeft + dx;
      if (direction.includes("s")) bottom = startBottom + dy;
      if (direction.includes("n")) top = startTop + dy;

      if (right - left < minWidth) {
        if (direction.includes("w")) left = right - minWidth;
        else right = left + minWidth;
      }
      if (bottom - top < minHeight) {
        if (direction.includes("n")) top = bottom - minHeight;
        else bottom = top + minHeight;
      }

      if (left < VIEWPORT_MARGIN) {
        left = VIEWPORT_MARGIN;
      }
      if (top < VIEWPORT_MARGIN) {
        top = VIEWPORT_MARGIN;
      }
      if (right > viewportWidth - VIEWPORT_MARGIN) {
        right = viewportWidth - VIEWPORT_MARGIN;
      }
      if (bottom > viewportHeight - VIEWPORT_MARGIN) {
        bottom = viewportHeight - VIEWPORT_MARGIN;
      }

      // Re-apply minimum size after bounds clamping.
      if (right - left < minWidth) {
        if (direction.includes("w")) left = Math.max(VIEWPORT_MARGIN, right - minWidth);
        else right = Math.min(viewportWidth - VIEWPORT_MARGIN, left + minWidth);
      }
      if (bottom - top < minHeight) {
        if (direction.includes("n")) top = Math.max(VIEWPORT_MARGIN, bottom - minHeight);
        else bottom = Math.min(viewportHeight - VIEWPORT_MARGIN, top + minHeight);
      }

      setModalRect({
        x: left,
        y: top,
        width: Math.max(minWidth, right - left),
        height: Math.max(minHeight, bottom - top),
      });
    };

    const onMouseUp = () => {
      interactionRef.current = null;
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [clampRect]);

  // Handle download
  const handleDownload = useCallback(() => {
    if (!pdfBlob && !pdfBlobUrl) return;

    const link = document.createElement("a");
    const url = pdfBlob ? URL.createObjectURL(pdfBlob) : pdfBlobUrl!;
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    if (pdfBlob) {
      setTimeout(() => URL.revokeObjectURL(url), 100);
    }
  }, [pdfBlob, pdfBlobUrl, filename]);

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
        className={`absolute overflow-hidden bg-slate-900 shadow-2xl ${isFullscreen ? "rounded-lg" : "rounded-2xl"}`}
        style={{
          left: modalRect.x,
          top: modalRect.y,
          width: modalRect.width,
          height: modalRect.height,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {!isFullscreen && (
          <>
            <div className="absolute inset-y-0 left-0 z-20 w-2 cursor-w-resize" onMouseDown={startResize("w")} />
            <div className="absolute inset-y-0 right-0 z-20 w-2 cursor-e-resize" onMouseDown={startResize("e")} />
            <div className="absolute inset-x-0 top-0 z-20 h-2 cursor-n-resize" onMouseDown={startResize("n")} />
            <div className="absolute inset-x-0 bottom-0 z-20 h-2 cursor-s-resize" onMouseDown={startResize("s")} />
            <div className="absolute left-0 top-0 z-20 h-3 w-3 cursor-nw-resize" onMouseDown={startResize("nw")} />
            <div className="absolute right-0 top-0 z-20 h-3 w-3 cursor-ne-resize" onMouseDown={startResize("ne")} />
            <div className="absolute bottom-0 left-0 z-20 h-3 w-3 cursor-sw-resize" onMouseDown={startResize("sw")} />
            <div className="absolute bottom-0 right-0 z-20 h-3 w-3 cursor-se-resize" onMouseDown={startResize("se")} />
          </>
        )}

        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-700 bg-slate-800 px-4 py-3">
          <div
            className="flex cursor-move select-none items-center gap-2"
            onMouseDown={startMove}
            onDragStart={(e) => e.preventDefault()}
          >
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

            {/* Switch to full-page viewer */}
            {viewerHref ? (
              <button
                type="button"
                onClick={() => window.open(viewerHref, "_blank", "noopener,noreferrer")}
                className="rounded-lg border border-slate-600 bg-slate-700 p-1.5 text-slate-200 transition hover:bg-slate-600"
                aria-label="페이지 뷰어로 전환"
                title="페이지 뷰어로 전환"
              >
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M5 12h10" />
                  <path d="M11 6l6 6-6 6" />
                  <path d="M19 5v14" />
                </svg>
              </button>
            ) : null}

            {/* Fullscreen toggle */}
            <button
              type="button"
              onClick={toggleFullscreen}
              className="rounded-lg border border-slate-600 bg-slate-700 p-1.5 text-slate-200 transition hover:bg-slate-600"
              aria-label={isFullscreen ? "창 크기 복원" : "전체 화면"}
              title={isFullscreen ? "복원" : "전체 화면"}
            >
              {isFullscreen ? (
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 3H3v6" />
                  <path d="M3 3l7 7" />
                  <path d="M15 21h6v-6" />
                  <path d="M21 21l-7-7" />
                </svg>
              ) : (
                <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="4" y="4" width="16" height="16" rx="1" />
                </svg>
              )}
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
        <div className="relative flex h-[calc(100%-60px)] items-center justify-center overflow-auto bg-slate-950 p-4">

          {pdfError && (
            <div className="text-center">
              <div className="mb-3 text-4xl">⚠️</div>
              <p className="text-red-400">{pdfError}</p>
            </div>
          )}

          {!pdfError && pdfFile && (
            <div className="flex h-full flex-col items-center">
              <ReactPdfDocument
                file={pdfFile}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                error={<div className="text-red-400">PDF 로드 실패</div>}
                className="flex flex-col items-center"
              >
                <ReactPdfPage
                  pageNumber={currentPage}
                  width={pageWidth}
                  error={<div className="text-red-400">페이지 로드 실패</div>}
                />
              </ReactPdfDocument>
            </div>
          )}

          {/* Loading overlay */}
          {pdfLoading && (pdfBlob || pdfBlobUrl || pdfFile) && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-slate-950/90">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-slate-600 border-t-sky-500" />
              <p className="text-sm text-slate-400">PDF를 불러오는 중...</p>
            </div>
          )}
        </div>

        {/* Footer hints */}
        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full bg-slate-800/80 px-4 py-1.5 text-xs text-slate-400 backdrop-blur-sm">
          ESC로 닫기 • 방향키로 페이지 이동
        </div>
      </div>
      <style jsx global>{`
        .codex-pdf-highlight {
          background: rgba(14, 165, 233, 0.34);
          border-radius: 3px;
          box-shadow: 0 0 0 1px rgba(14, 165, 233, 0.52);
        }
      `}</style>
    </div>
  );
}
