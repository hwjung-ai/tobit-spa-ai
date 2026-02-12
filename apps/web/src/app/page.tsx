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
      return "bg-[var(--surface-elevated)] text-[var(--foreground)] border-[var(--border)] dark:bg-[var(--surface-base)] dark:text-[var(--foreground)] dark:border-[var(--border)]";
    case "done":
      return "bg-emerald-100 text-emerald-900 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-200 dark:border-emerald-800";
    case "error":
      return "bg-rose-100 text-rose-900 border-rose-200 dark:bg-rose-900/30 dark:text-rose-200 dark:border-rose-800";
    default:
      return "bg-[var(--surface-elevated)] text-[var(--foreground)] border-[var(--border)] dark:bg-[var(--surface-base)] dark:text-[var(--foreground)] dark:border-[var(--border)]";
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
  const [threadsError, setThreadsError] = useState<string | null>(null);
  const apiBaseUrl = sanitizeUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  const [references, setReferences] = useState<ReferenceItem[]>([]);
  const router = useRouter();

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

  const fetchThreadDetail = useCallback(
    async (threadId: string) => {
      const payload = await authenticatedFetch<ThreadDetail | { data: ThreadDetail }>(`/threads/${threadId}`);
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
    },
    []
  );

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
      streamUrl = `/sse-proxy/chat/stream?message=${encodedPrompt}${threadParam}${token ? `&token=${token}` : ''}`;
    } else {
      streamUrl = `${apiBaseUrl}/chat/stream?message=${encodedPrompt}${threadParam}${token ? `&token=${token}` : ''}`;
    }

    const source = new EventSource(streamUrl);
    eventSourceRef.current = source;

    source.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data) as StreamChunk;
        setChunks((prev) => {
          if (payload.type === "answer" && prev.length > 0 && prev[prev.length - 1].type === "answer") {
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
          : prev
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
    <div className="min-h-screen flex flex-col dark: dark:" style={{backgroundColor: "var(--surface-base)", color: "var(--foreground)"}}>
      <div className="flex flex-1 gap-6 py-6">
        {historyVisible ? (
          <aside className="w-[320px] space-y-4 rounded-2xl border p-4 shadow-md dark: dark:" style={{backgroundColor: "var(--background)", borderColor: "var(--border)"}}>
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wider dark:" style={{color: "var(--foreground)"}}>History</p>
              {loadingThreads ? (
                <span className="text-xs 0 dark:" style={{color: "var(--muted-foreground)"}}>Loading...</span>
              ) : null}
              <button
                onClick={fetchThreads}
                className="rounded-md border px-2 py-1 text-[10px] uppercase tracking-wider transition hover: dark: dark: dark:hover:" style={{backgroundColor: "var(--surface-elevated)", color: "var(--foreground)", borderColor: "var(--border)"}}
              >
                Refresh
              </button>
            </div>
            {threadsError ? (
              <p className="text-xs">로드 실패: {threadsError}</p>
            ) : null}
            <div className="space-y-3">
              {threads.length === 0 ? (
                <p className="text-sm">No conversations yet.</p>
              ) : null}
              {threads.map((thread) => (
                <div
                  key={thread.id}
                  className={cn(
                    "group relative flex w-full flex-col rounded-2xl border px-3 py-3 transition cursor-pointer",
                    activeThread?.id === thread.id ? "border-sky-600 dark:border-sky-500" : ""
                  )}
                  style={{backgroundColor: activeThread?.id === thread.id
                      ? "var(--surface-elevated)"
                      : "var(--background)", borderColor: activeThread?.id === thread.id
                      ? ""
                      : "var(--border)"}}
                  onClick={() => selectThread(thread.id)}
                >
                  <div className="text-left">
                    <p className="font-semibold text-sm">{thread.title}</p>
                    <p className="text-xs dark:" style={{color: "var(--muted-foreground)"}}>{formatTimestamp(thread.updated_at)}</p>
                  </div>
                  <button
                    className="absolute right-3 bottom-2 opacity-0 transition duration-200 group-hover:opacity-100 group-hover:pointer-events-auto flex h-5 w-5 items-center justify-center rounded-full border text-[10px] text-rose-600 border-rose-400 hover:bg-rose-50 dark:text-rose-400 dark:border-rose-500 dark:hover:bg-rose-950/30"
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

        <main className={cn("flex flex-1 flex-col gap-6 transition-all", !historyVisible && "w-full")}>
          {/* Header Section */}
          <div className="rounded-2xl border p-5 shadow-sm dark: dark:" style={{backgroundColor: "var(--background)", borderColor: "var(--border)"}}>
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h1 className="text-lg font-semibold dark:" style={{color: "var(--foreground)"}}>Streaming Assistant</h1>
                <p className="text-sm dark:" style={{color: "var(--muted-foreground)"}}>
                  메시지 기반 대화 기록을 저장하고, SSE로 Assistant 답변을 받습니다.
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setHistoryVisible((prev) => !prev)}
                  className="rounded-2xl border px-4 py-2 text-sm uppercase tracking-wider transition hover: dark: dark: dark:hover:" style={{backgroundColor: "var(--surface-elevated)", color: "var(--foreground)", borderColor: "var(--border)"}}
                >
                  {historyVisible ? "Hide history" : "Show history"}
                </button>
                <button
                  onClick={startNewConversation}
                  className="rounded-2xl border px-4 py-2 text-sm uppercase tracking-wider transition hover: dark: dark: dark:hover:" style={{backgroundColor: "var(--surface-elevated)", color: "var(--foreground)", borderColor: "var(--border)"}}
                >
                  New conversation
                </button>
              </div>
            </div>
          </div>

          {/* Input Section */}
          <section className="rounded-2xl border p-5 shadow-sm dark: dark:" style={{backgroundColor: "var(--background)", borderColor: "var(--border)"}}>
            <form onSubmit={handleSubmit} className="space-y-4">
              <label className="flex flex-col gap-2 text-sm dark:" style={{color: "var(--foreground)"}}>
                질문 입력
                <input
                  value={inputValue}
                  onChange={(event) => setInputValue(event.target.value)}
                  className="w-full rounded-2xl border px-4 py-3 text-base outline-none transition focus:border-sky-500 dark: dark: dark:text-white dark:focus:border-sky-400" style={{backgroundColor: "var(--background)", borderColor: "var(--border)"}}
                  placeholder="예: 새 프로젝트의 방향성을 요약해줘"
                />
              </label>
              <div className="flex items-center justify-between gap-3">
                <button
                  type="submit"
                  className="inline-flex items-center justify-center rounded-2xl bg-sky-600 px-6 py-3 text-sm font-semibold uppercase tracking-wide text-white transition hover:bg-sky-500 disabled:opacity-40 dark:bg-sky-700 dark:hover:bg-sky-600"
                  disabled={!inputValue.trim() || status === "streaming"}
                >
                  <span className={status === "streaming" ? "animate-pulse" : ""}>
                    {status === "streaming" ? "Streaming…" : "메시지 전송"}
                  </span>
                </button>
                <span
                  className={cn(
                    "text-xs uppercase tracking-wider",
                    status === "streaming" && "animate-pulse"
                  )}
                >
                  {status === "streaming" ? (
                    <span className="text-sky-600 dark:text-sky-400">SSE live</span>
                  ) : status === "idle" ? (
                    <span className="0 dark:" style={{color: "var(--muted-foreground)"}}>Ready</span>
                  ) : (
                    <span className="text-rose-600 dark:text-rose-400">Error</span>
                  )}
                </span>
              </div>
            </form>
            <div className="mt-3 flex flex-wrap gap-2 text-xs 0 dark:" style={{color: "var(--muted-foreground)"}}>
              <span>API: {apiBaseUrl}</span>
              <span>SSE</span>
              <span>chat/stream</span>
              {activeThread ? <span>Thread: {activeThread.title}</span> : null}
            </div>
          </section>

          {/* Stream Feed Section */}
          <section className="rounded-2xl border p-5 shadow-sm dark: dark:" style={{backgroundColor: "var(--background)", borderColor: "var(--border)"}}>
            <p className="text-xs font-semibold uppercase tracking-wider 0 dark:" style={{color: "var(--muted-foreground)"}}>Stream feed</p>
            <div className="mt-3 flex flex-col gap-3 border-t pt-3 dark:" style={{borderColor: "var(--border)"}}>
              {chunks.length === 0 ? (
                <p className="text-sm 0 dark:" style={{color: "var(--muted-foreground)"}}>Streaming responses will appear here.</p>
              ) : null}
              {chunks.map((chunk, index) => (
                <div
                  key={`${chunk.type}-${index}`}
                  className={cn("space-y-1 rounded-2xl border p-3 text-sm", getBadgeClasses(chunk.type))}
                >
                  <span
                    className={cn("inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs", getBadgeClasses(chunk.type))}
                  >
                    {chunk.type}
                  </span>
                  <p className="whitespace-pre-wrap text-base leading-relaxed dark:" style={{color: "var(--foreground)"}}>{chunk.text}</p>
                  {chunk.thread_id ? (
                    <p className="text-xs 0 dark:" style={{color: "var(--muted-foreground)"}}>Thread: {chunk.thread_id}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </section>

          {/* References Section */}
          <section className="rounded-2xl border p-5 shadow-sm dark: dark:" style={{backgroundColor: "var(--background)", borderColor: "var(--border)"}}>
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wider 0 dark:" style={{color: "var(--muted-foreground)"}}>References</p>
              <button
                onClick={() => setReferences([])}
                className="text-[10px] uppercase tracking-wider transition 0 hover: dark: dark:hover:" style={{color: "var(--foreground)"}}
              >
                Clear
              </button>
            </div>
            <div className="mt-3 space-y-3">
              {references.length === 0 ? (
                <p className="text-sm 0 dark:" style={{color: "var(--muted-foreground)"}}>References from latest document chat will appear here.</p>
              ) : (
                references.map((reference) => (
                  <button
                    key={reference.chunk_id}
                    onClick={() => openReference(reference)}
                    className="w-full rounded-2xl border p-4 text-left transition hover:border-sky-500 dark: dark: dark:hover:border-sky-400" style={{backgroundColor: "var(--surface-base)", borderColor: "var(--border)"}}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold dark:" style={{color: "var(--foreground)"}}>{reference.document_title}</p>
                      <span className="text-[10px] uppercase tracking-wider 0 dark:" style={{color: "var(--muted-foreground)"}}>
                        {reference.page ? `Page ${reference.page}` : "Page unknown"}
                      </span>
                    </div>
                    <p className="mt-2 text-xs dark:" style={{color: "var(--muted-foreground)"}}>{reference.snippet}</p>
                    {reference.score !== undefined ? (
                      <p className="mt-1 text-[10px] uppercase tracking-wider 0 dark:" style={{color: "var(--muted-foreground)"}}>
                        Similarity {reference.score.toFixed(2)}
                      </p>
                    ) : null}
                  </button>
                ))
              )}
            </div>
          </section>

          {/* Conversation Section */}
          <section className="rounded-2xl border p-5 shadow-sm dark: dark:" style={{backgroundColor: "var(--background)", borderColor: "var(--border)"}}>
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-wider 0 dark:" style={{color: "var(--muted-foreground)"}}>Conversation</p>
              {activeThread ? (
                <p className="text-xs 0 dark:" style={{color: "var(--muted-foreground)"}}>
                  {messageFeed.length} message{messageFeed.length === 1 ? "" : "s"}
                </p>
              ) : null}
            </div>
            <div className="mt-3 space-y-3">
              {messageFeed.length === 0 ? (
                <p className="text-sm 0 dark:" style={{color: "var(--muted-foreground)"}}>Select a thread or send a prompt to start.</p>
              ) : (
                messageFeed.map((message) =>
                  message.role === "user" ? (
                    <div
                      key={message.id}
                      className="flex justify-end"
                    >
                      <div className="max-w-[70%] rounded-2xl border px-4 py-2 text-sm font-medium shadow-lg bg-sky-600 border-sky-500 text-white">
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
                      className="rounded-2xl border p-4 text-sm shadow-sm dark: dark:" style={{backgroundColor: "var(--surface-base)", borderColor: "var(--border)"}}
                    >
                      <p className="text-xs uppercase tracking-wider 0 dark:" style={{color: "var(--muted-foreground)"}}>
                        {message.role} · {formatTimestamp(message.created_at)}
                      </p>
                      <p className="mt-2 whitespace-pre-wrap text-base leading-relaxed dark:" style={{color: "var(--foreground)"}}>
                        {message.content}
                      </p>
                    </div>
                  )
                )
              )}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}