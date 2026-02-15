"use client";

import { useState, useEffect, useCallback } from "react";
import { authenticatedFetch } from "@/lib/apiClient/index";
import { PdfViewerModal } from "@/components/pdf/PdfViewerModal";

interface AnswerBlock {
  type: string;
  title?: string;
  content?: string;
  summary?: string;
  columns?: string[];
  rows?: unknown[][];
  node_count?: number;
  edge_count?: number;
}

interface QuestionAnswer {
  question: string;
  timestamp: string;
  mode: string;
  summary?: string;
  blocks?: AnswerBlock[];
  references?: Array<{ title?: string; text?: string }>;
}

interface SummaryData {
  title: string;
  topic: string;
  date: string;
  created_at: string;
  question_count: number;
  questions_and_answers: QuestionAnswer[];
}

interface ConversationSummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  threadId: string | null;
  historyId: string | null;
}

export default function ConversationSummaryModal({
  isOpen,
  onClose,
  threadId,
  historyId,
}: ConversationSummaryModalProps) {
  const [summaryData, setSummaryData] = useState<SummaryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  // PDF viewer modal state
  const [pdfViewerOpen, setPdfViewerOpen] = useState(false);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfFilename, setPdfFilename] = useState<string>("conversation_report.pdf");

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await authenticatedFetch<{
        code?: number;
        message?: string;
        data?: SummaryData;
      }>("/ops/conversation/summary", {
        method: "POST",
        body: JSON.stringify({
          history_id: historyId,
          summary_type: "individual",
        }),
      });

      const data = payload?.data;
      if (data) {
        setSummaryData(data);
      } else {
        setError(payload?.message || "요약 데이터를 가져올 수 없습니다.");
      }
    } catch (err) {
      console.error("Failed to fetch conversation summary:", err);
      setError("요약 데이터를 가져오는데 실패했습니다.");
    } finally {
      setLoading(false);
    }
  }, [historyId]);

  useEffect(() => {
    if (isOpen && (threadId || historyId)) {
      fetchSummary();
    }
  }, [isOpen, threadId, historyId, fetchSummary]);

  const exportToPDF = async () => {
    setExporting(true);
    setError(null);
    try {
      const payload = await authenticatedFetch<{
        code?: number;
        message?: string;
        data?: { filename: string; content: string; content_type: string };
      }>("/ops/conversation/export/pdf", {
        method: "POST",
        body: JSON.stringify({
          history_id: historyId,
          title: summaryData?.title,
          topic: summaryData?.topic,
          summary_type: "individual",
        }),
      });

      const result = payload?.data;
      if (result?.content) {
        // Decode base64 and show in viewer modal
        const binaryString = atob(result.content);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const blob = new Blob([bytes], { type: result.content_type });
        const url = URL.createObjectURL(blob);
        setPdfBlobUrl(url);
        setPdfFilename(result.filename || "conversation_report.pdf");
        setPdfViewerOpen(true);
      } else {
        setError(payload?.message || "PDF 생성에 실패했습니다.");
      }
    } catch (err) {
      console.error("Failed to export PDF:", err);
      setError("PDF 생성에 실패했습니다.");
    } finally {
      setExporting(false);
    }
  };

  // Cleanup PDF blob URL when modal closes
  const handleClosePdfViewer = useCallback(() => {
    if (pdfBlobUrl) {
      URL.revokeObjectURL(pdfBlobUrl);
    }
    setPdfViewerOpen(false);
    setPdfBlobUrl(null);
  }, [pdfBlobUrl]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="container-panel mx-4 max-h-[80vh] w-full max-w-2xl overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b px-6 py-4 border-variant bg-surface-elevated">
          <div className="flex items-center gap-3">
            <span className="text-2xl">📋</span>
            <h2 className="text-lg font-semibold text-foreground">대화 요약</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-1 transition hover:text-foreground text-muted-standard bg-surface-elevated"
            aria-label="닫기"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto p-6 custom-scrollbar">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="mb-3 inline-block h-8 w-8 animate-spin rounded-full border-4 border-t-sky-500 border-variant" />
                <p className="text-sm text-muted-standard">요약을 불러오는 중...</p>
              </div>
            </div>
          ) : error ? (
            <div className="rounded-lg border border-rose-900 bg-rose-950/50 p-4">
              <p className="text-sm text-rose-300">{error}</p>
              <button
                onClick={fetchSummary}
                className="mt-3 rounded-lg border border-rose-700 bg-rose-900/50 px-3 py-2 text-xs text-rose-200 transition hover:bg-rose-900"
              >
                다시 시도
              </button>
            </div>
          ) : summaryData ? (
            <div className="space-y-4">
              {/* Metadata */}
              <div className="container-card p-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-label">제목:</span>
                    <p className="mt-1 font-medium text-foreground">{summaryData.title}</p>
                  </div>
                  <div>
                    <span className="text-label">주제:</span>
                    <p className="mt-1 text-foreground">{summaryData.topic}</p>
                  </div>
                  <div>
                    <span className="text-label">일자:</span>
                    <p className="mt-1 text-foreground">{summaryData.date}</p>
                  </div>
                  <div>
                    <span className="text-label">질문 수:</span>
                    <p className="mt-1 text-foreground">{summaryData.question_count}개</p>
                  </div>
                </div>
              </div>

              {/* Questions and Answers Preview */}
              <div>
                <h3 className="mb-3 text-sm font-semibold text-primary">질문-응답 내역</h3>
                <div className="space-y-3">
                  {summaryData.questions_and_answers.map((qa, idx) => (
                    <div
                      key={idx}
                      className="container-card p-3"
                    >
                      <div className="mb-2 flex items-start justify-between">
                        <span className="text-xs font-medium text-sky-400">
                          Q{idx + 1}. {qa.mode} 모드
                        </span>
                        {qa.timestamp && (
                          <span className="text-tiny text-muted-standard">
                            {new Date(qa.timestamp).toLocaleString("ko-KR", {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        )}
                      </div>
                      <p className="mb-2 line-clamp-2 text-sm text-foreground">{qa.question}</p>
                      {qa.summary && (
                        <p className="line-clamp-2 text-xs text-muted-standard">{qa.summary}</p>
                      )}
                      {qa.blocks && qa.blocks.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {qa.blocks.slice(0, 3).map((block, blockIdx) => (
                            <span
                              key={blockIdx}
                              className="badge-primary text-tiny"
                            >
                              {block.type === "table"
                                ? "📊 테이블"
                                : block.type === "chart"
                                ? "📈 차트"
                                : block.type === "graph"
                                ? "🕸️ 그래프"
                                : block.type === "text"
                                ? "📝 텍스트"
                                : block.type}
                            </span>
                          ))}
                          {qa.blocks.length > 3 && (
                            <span className="badge-primary text-tiny">
                              +{qa.blocks.length - 3}
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-6 py-4 border-variant bg-surface-elevated">
          <button
            onClick={onClose}
            className="btn-secondary rounded-lg px-4 py-2 text-sm"
          >
            닫기
          </button>
          {summaryData && (
            <button
              onClick={exportToPDF}
              disabled={exporting}
              className="flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {exporting ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                  내보내는 중...
                </>
              ) : (
                <>
                  <span>📄</span>
                  PDF 리포트 내보내기
                </>
              )}
            </button>
          )}
        </div>
      </div>

      {/* PDF Viewer Modal */}
      <PdfViewerModal
        isOpen={pdfViewerOpen}
        onClose={handleClosePdfViewer}
        pdfBlobUrl={pdfBlobUrl}
        filename={pdfFilename}
      />
    </div>
  );
}
