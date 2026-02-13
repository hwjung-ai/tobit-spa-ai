"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { authenticatedFetch } from "@/lib/apiClient/index";
import { cn } from "@/lib/utils";

type ChunkType = "answer" | "summary" | "detail" | "done" | "error";

interface StreamChunk {
  type: ChunkType;
  text: string;
  thread_id?: string;
  meta?: {
    document_id?: string;
    chunks?: { chunk_id: string; page: number | null; snippet?: string }[];
    references?: ReferenceItem[];
  };
}

interface ThreadRead {
  id: string;
  title: string;
  tenant_id: string;
  user_id: string;
  created_at: string;
  updated_at: string;
}

interface MessageRead {
  id: string;
  thread_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  token_in?: number;
  token_out?: number;
}

interface ThreadDetail extends ThreadRead {
  messages: MessageRead[];
}

interface ReferenceItem {
  document_id: string;
  document_title: string;
  chunk_id: string;
  page: number | null;
  snippet: string;
  score?: number;
}

// Badge style helper using Tailwind classes for dark mode support
const getBadgeClasses = (type: ChunkType): string => {
  switch (type) {
    case "answer":
      return "bg-sky-600 text-white border-sky-700";
    case "summary":
      return "bg-amber-100 text-amber-900 border-amber-200 dark:bg-amber-900/30 dark:text-amber-200 dark:border-amber-800";
    case "detail":
      return "bg-slate-100 text-slate-900 border-slate-300 dark:bg-slate-950 dark:text-slate-900 dark:border-slate-300";
    case "done":
      return "bg-emerald-100 text-emerald-900 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-200 dark:border-emerald-800";
    case "error":
      return "bg-rose-100 text-rose-900 border-rose-200 dark:bg-rose-900/30 dark:text-rose-200 dark:border-rose-800";
    default:
      return "bg-slate-100 text-slate-900 border-slate-300 dark:bg-slate-950 dark:text-slate-900 dark:border-slate-300";
  }
};

const sanitizeUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "";

const formatTimestamp = (value: string) => {
  try {
    return new Date(value).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
  } catch {
    return value;
  }
};

export default function Home() {
  const [inputValue, setInputValue] = useState("");
  const [chunks, setChunks] = useState<StreamChunk[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  const [threads, setThreads] = useState<ThreadRead[]>([]);
  const [activeThread, setActiveThread] = useState<ThreadDetail | null>(null);
  const [loadingThreads, setLoadingThreads] = useState(false);
  const [status, setStatus] = useState<"idle" | "streaming" | "error">("idle");
  const [historyVisible, setHistoryVisible] = useState(true);
  const [leftPanelWidth, setLeftPanelWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(false);
  const [threadsError, setThreadsError] = useState<string | null>(null);
  const apiBaseUrl = sanitizeUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  const [references, setReferences] = useState<ReferenceItem[]>([]);
  const router = useRouter();
  const contentRef = useRef<HTMLDivElement>(null);

  const fetchThreads = useCallback(async () => {
    setLoadingThreads(true);
    setThreadsError(null);
    try {
      const payload = await authenticatedFetch<ThreadRead[] | { data: ThreadRead[] }>(`/threads`);
      const threadList = Array.isArray(payload) ? payload : (payload.data ?? []);
      setThreads(threadList);
    } catch (error: unknown) {
      console.error("Failed to load threads", error);
      setThreadsError(error instanceof Error ? error.message : "Failed to load threads");
    } finally {
      setLoadingThreads(false);
    }
  }, []);

  useEffect(() => {
    if (!activeThread && threads.length > 0) {
      selectThread(threads[0].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threads]);

  useEffect(() => {
    if (!isResizing || !historyVisible) return;

    const handleMouseMove = (event: MouseEvent) => {
      if (!contentRef.current) return;
      const rect = contentRef.current.getBoundingClientRect();
      const nextWidth = event.clientX - rect.left;
      setLeftPanelWidth(Math.max(260, Math.min(520, nextWidth)));
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [historyVisible, isResizing]);

  const fetchThreadDetail = useCallback(async (threadId: string) => {
    const payload = await authenticatedFetch<ThreadDetail | { data: ThreadDetail }>(
      `/threads/${threadId}`,
    );
    const detail = (payload as { data?: ThreadDetail }).data ?? (payload as ThreadDetail);
    setActiveThread(detail);
    setThreads((prev) => {
      const existing = prev.find((thread) => thread.id === detail.id);
      const updated = existing?.updated_at !== detail.updated_at;
      const filtered = prev.filter((thread) => thread.id !== detail.id);
      if (updated) {
        return [detail, ...filtered];
      }
      return prev.map((thread) => (thread.id === detail.id ? detail : thread));
    });
  }, []);

  useEffect(() => {
    fetchThreads();
  }, [fetchThreads]);

  useEffect(() => {
    if (!activeThread && threads.length > 0) {
      selectThread(threads[0].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threads]);

  const selectThread = (threadId: string) => {
    if (activeThread?.id !== threadId) {
      setChunks([]);
      setReferences([]);
      setStatus("idle");
      eventSourceRef.current?.close();
    }
    setActiveThread((prev) => (prev?.id === threadId ? prev : null));
    fetchThreadDetail(threadId).catch(console.error);
  };

  const deleteThread = async (threadId: string) => {
    await authenticatedFetch(`/threads/${threadId}`, {
      method: "DELETE",
    });
    setThreads((prev) => prev.filter((thread) => thread.id !== threadId));
    setActiveThread((prev) => (prev?.id === threadId ? null : prev));
  };

  const openReference = (reference: ReferenceItem) => {
    if (!reference.document_id) {
      return;
    }
    const params = new URLSearchParams();
    params.set("chunkId", reference.chunk_id);
    if (reference.page != null) {
      params.set("page", reference.page.toString());
    }
    router.push(`/documents/${reference.document_id}/viewer?${params.toString()}`);
  };

  const createThreadResource = useCallback(async (): Promise<ThreadDetail> => {
    const payload = await authenticatedFetch<ThreadDetail | { data: ThreadDetail }>(`/threads`, {
      method: "POST",
      body: JSON.stringify({ title: "New conversation" }),
    });
    const thread = (payload as { data?: ThreadDetail }).data ?? (payload as ThreadDetail);
    setThreads((prev) => [thread, ...prev.filter((item) => item.id !== thread.id)]);
    setActiveThread(thread);
    setChunks([]);
    setStatus("idle");
    return thread;
  }, []);

  const startNewConversation = useCallback(() => {
    createThreadResource().catch(console.error);
  }, [createThreadResource]);

  const streamChat = async (prompt: string) => {
    setChunks([]);
    setStatus("streaming");
    setReferences([]);
    eventSourceRef.current?.close();
    const encodedPrompt = encodeURIComponent(prompt);
    let thread = activeThread;
    if (!thread) {
      thread = await createThreadResource();
    }
    const threadParam = `&thread_id=${thread.id}`;
    const token = localStorage.getItem("access_token");

    let streamUrl: string;
    if (!apiBaseUrl) {
      streamUrl = `/sse-proxy/chat/stream?message=${encodedPrompt}${threadParam}${token ? `&token=${token}` : ""}`;
    } else {
      streamUrl = `${apiBaseUrl}/chat/stream?message=${encodedPrompt}${threadParam}${token ? `&token=${token}` : ""}`;
    }

    const source = new EventSource(streamUrl);
    eventSourceRef.current = source;

    source.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data) as StreamChunk;
        setChunks((prev) => {
          if (
            payload.type === "answer" &&
            prev.length > 0 &&
            prev[prev.length - 1].type === "answer"
          ) {
            const merged = {
              ...prev[prev.length - 1],
              text: prev[prev.length - 1].text + payload.text,
            };
            return [...prev.slice(0, -1), merged];
          }
          return [...prev, payload];
        });
        if (payload.thread_id && (!activeThread || activeThread.id !== payload.thread_id)) {
          fetchThreadDetail(payload.thread_id).catch(console.error);
        }
        if (payload.type === "done") {
          setStatus("idle");
          source.close();
          if (payload.meta?.references) {
            const validRefs = (payload.meta.references as ReferenceItem[]).filter((ref) => {
              const id = ref.document_id?.trim();
              return Boolean(id) && id !== "undefined";
            });
            setReferences(validRefs);
          }
          if (payload.thread_id) {
            fetchThreadDetail(payload.thread_id).catch(console.error);
          }
        }
        if (payload.type === "error") {
          setStatus("error");
          source.close();
        }
      } catch (error) {
        console.error("Failed to parse chunk", error);
        setStatus("error");
        source.close();
      }
    });

    source.addEventListener("error", () => {
      if (source.readyState === EventSource.OPEN) {
        setStatus("error");
      }
      source.close();
    });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!inputValue.trim()) return;
    const trimmedMessage = inputValue.trim();
    void streamChat(trimmedMessage);
    setInputValue("");
    if (activeThread) {
      setActiveThread((prev) =>
        prev
          ? {
              ...prev,
              messages: [
                ...(prev.messages ?? []),
                {
                  id: `local-${Date.now()}`,
                  thread_id: prev.id,
                  role: "user",
                  content: trimmedMessage,
                  created_at: new Date().toISOString(),
                },
              ],
            }
          : prev,
      );
    }
  };

  const messageFeed = useMemo(() => {
    if (!activeThread) {
      return [];
    }
    return activeThread.messages ?? [];
  }, [activeThread]);

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-50">
      {/* Page Header - Standard */}
      <header className="page-header">
        <div className="page-header-wrapper">
          <div className="page-header-title-group">
            <h1 className="page-header-title">Chat Assistant</h1>
            <p className="page-header-description">
              메시지 기반 대화 기록을 저장하고, SSE로 도우미 답변을 받습니다.
            </p>
          </div>
          <div className="page-header-actions">
            <button onClick={() => setHistoryVisible((prev) => !prev)} className="btn-secondary">
              {historyVisible ? "Hide history" : "Show history"}
            </button>
            <button onClick={startNewConversation} className="btn-primary">
              New conversation
            </button>
          </div>
        </div>
      </header>

      <div
        ref={contentRef}
        className="flex flex-1 overflow-hidden py-6"
        style={{ userSelect: isResizing ? "none" : "auto" }}
      >
        {historyVisible ? (
          <aside
            className="space-y-4 container-panel h-full overflow-y-auto custom-scrollbar"
            style={{ width: `${leftPanelWidth}px` }}
          >
            <div className="flex items-center justify-between">
              <p className="left-panel-title">History</p>
              {loadingThreads ? (
                <span className="text-sm text-muted-standard">Loading...</span>
              ) : null}
              <button onClick={fetchThreads} className="btn-secondary">
                Refresh
              </button>
            </div>
            {threadsError ? <p className="text-xs">로드 실패: {threadsError}</p> : null}
            <div className="space-y-3">
              {threads.length === 0 ? <p className="text-sm">No conversations yet.</p> : null}
              {threads.map((thread) => (
                <div
                  key={thread.id}
                  className={cn(
                    "group relative flex w-full cursor-pointer flex-col br-card border px-3 py-3 transition",
                    activeThread?.id === thread.id
                      ? "border-sky-600 bg-sky-50 dark:border-sky-500 dark:bg-sky-900/20"
                      : "border-border bg-surface-base hover:bg-surface-elevated dark:hover:bg-slate-800/80",
                  )}
                  onClick={() => selectThread(thread.id)}
                >
                  <div className="text-left">
                    <p className="font-semibold text-sm">{thread.title}</p>
                    <p className="text-xs text-muted-standard">
                      {formatTimestamp(thread.updated_at)}
                    </p>
                  </div>
                  <button
                    className="absolute right-3 bottom-2 opacity-0 transition duration-200 group-hover:opacity-100 group-hover:pointer-events-auto flex h-5 w-5 items-center justify-center rounded-full border text-tiny text-rose-600 border-rose-400 hover:bg-rose-50 dark:text-rose-400 dark:border-rose-500 dark:hover:bg-rose-950/30"
                    onClick={(event) => {
                      event.stopPropagation();
                      deleteThread(thread.id);
                    }}
                    aria-label="Delete thread"
                  >
                    X
                  </button>
                </div>
              ))}
            </div>
          </aside>
        ) : null}

        {historyVisible ? (
          <div
            onMouseDown={(event) => {
              event.preventDefault();
              setIsResizing(true);
            }}
            className={cn("resize-handle-col", isResizing && "is-active")}
            onDoubleClick={() => setLeftPanelWidth(320)}
            aria-label="Resize history panel"
            role="separator"
            aria-orientation="vertical"
            data-testid="chat-history-resize-handle"
          >
            <div className="resize-handle-grip" />
          </div>
        ) : null}

        <main
          className={cn(
            "flex min-w-0 flex-1 flex-col gap-6 transition-all",
            historyVisible ? "pl-2" : "w-full",
          )}
        >
          {/* Input Section */}
          <section className="container-section">
            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="form-field-label min-w-[72px] shrink-0">질문 입력</span>
                <input
                  value={inputValue}
                  onChange={(event) => setInputValue(event.target.value)}
                  className="input-container flex-1"
                  placeholder="예: 새 프로젝트의 방향성을 요약해줘"
                />
                <button
                  type="submit"
                  className="btn-primary shrink-0"
                  disabled={!inputValue.trim() || status === "streaming"}
                >
                  <span className={status === "streaming" ? "animate-pulse" : ""}>
                    {status === "streaming" ? "Streaming…" : "메시지 전송"}
                  </span>
                </button>
              </div>
              <div className="flex justify-end">
                <span
                  className={cn(
                    "text-xs uppercase tracking-wider",
                    status === "streaming" && "animate-pulse",
                  )}
                >
                  {status === "streaming" ? (
                    <span className="text-sky-600 dark:text-sky-400">SSE live</span>
                  ) : status === "idle" ? (
                    <span className="text-muted-standard">Ready</span>
                  ) : (
                    <span className="text-rose-600 dark:text-rose-400">Error</span>
                  )}
                </span>
              </div>
            </form>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-muted-standard">
              <span>API: {apiBaseUrl}</span>
              <span>SSE</span>
              <span>chat/stream</span>
              {activeThread ? <span>Thread: {activeThread.title}</span> : null}
            </div>
          </section>

          {/* Stream Feed Section */}
          <section className="container-section">
            <p className="section-title-sub">Stream feed</p>
            <div className="mt-3 flex flex-col gap-3 border-t border-border pt-3">
              {chunks.length === 0 ? (
                <p className="text-sm text-muted-standard">Streaming responses will appear here.</p>
              ) : null}
              {chunks.map((chunk, index) => (
                <div
                  key={`${chunk.type}-${index}`}
                  className={cn(
                    "space-y-1 br-card border p-3 text-sm",
                    getBadgeClasses(chunk.type),
                  )}
                >
                  <span
                    className={cn(
                      "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs",
                      getBadgeClasses(chunk.type),
                    )}
                  >
                    {chunk.type}
                  </span>
                  <p className="whitespace-pre-wrap text-base leading-relaxed text-foreground">
                    {chunk.text}
                  </p>
                  {chunk.thread_id ? (
                    <p className="text-xs text-muted-standard">Thread: {chunk.thread_id}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </section>

          {/* References Section */}
          <section className="container-section">
            <div className="flex items-center justify-between">
              <p className="section-title-sub">References</p>
              <button
                onClick={() => setReferences([])}
                className="text-tiny uppercase tracking-wider text-foreground transition hover:text-sky-600 dark:hover:text-sky-400"
              >
                Clear
              </button>
            </div>
            <div className="mt-3 space-y-3">
              {references.length === 0 ? (
                <p className="text-sm text-muted-standard">
                  References from latest document chat will appear here.
                </p>
              ) : (
                references.map((reference) => (
                  <button
                    key={reference.chunk_id}
                    onClick={() => openReference(reference)}
                    className="w-full br-card border bg-surface-elevated p-4 text-left transition hover:border-sky-500 dark:hover:border-sky-400"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-foreground">
                        {reference.document_title}
                      </p>
                      <span className="text-tiny uppercase tracking-wider text-muted-standard">
                        {reference.page ? `Page ${reference.page}` : "Page unknown"}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-muted-standard">{reference.snippet}</p>
                    {reference.score !== undefined ? (
                      <p className="mt-1 text-tiny uppercase tracking-wider text-muted-standard">
                        Similarity {reference.score.toFixed(2)}
                      </p>
                    ) : null}
                  </button>
                ))
              )}
            </div>
          </section>

          {/* Conversation Section */}
          <section className="container-card">
            <div className="flex items-center justify-between">
              <p className="section-title-sub">Conversation</p>
              {activeThread ? (
                <p className="text-xs text-muted-standard">
                  {messageFeed.length} message{messageFeed.length === 1 ? "" : "s"}
                </p>
              ) : null}
            </div>
            <div className="mt-3 space-y-3">
              {messageFeed.length === 0 ? (
                <p className="text-sm text-muted-standard">
                  Select a thread or send a prompt to start.
                </p>
              ) : (
                messageFeed.map((message) =>
                  message.role === "user" ? (
                    <div key={message.id} className="flex justify-end">
                      <div className="max-w-[70%] br-card border px-4 py-2 text-sm font-medium shadow-lg bg-sky-600 border-sky-500 text-white">
                        <p className="text-xs uppercase tracking-wider text-sky-100">
                          {message.role} · {formatTimestamp(message.created_at)}
                        </p>
                        <p className="whitespace-pre-wrap text-base leading-relaxed text-white">
                          {message.content}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div
                      key={message.id}
                      className="br-card border bg-surface-elevated p-4 text-sm shadow-sm"
                    >
                      <p className="text-xs uppercase tracking-wider text-muted-standard">
                        {message.role} · {formatTimestamp(message.created_at)}
                      </p>
                      <p className="mt-2 whitespace-pre-wrap text-base leading-relaxed text-foreground">
                        {message.content}
                      </p>
                    </div>
                  ),
                )
              )}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
