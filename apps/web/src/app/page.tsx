"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

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

const badgeStyles: Record<ChunkType, string> = {
  answer: "bg-blue-50 text-blue-700 border-blue-200",
  summary: "bg-amber-50 text-amber-800 border-amber-200",
  detail: "bg-slate-50 text-slate-700 border-slate-200",
  done: "bg-emerald-50 text-emerald-800 border-emerald-200",
  error: "bg-rose-50 text-rose-800 border-rose-200",
};

const sanitizeUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "http://localhost:8000";

const formatTimestamp = (value: string) => {
  try {
    return new Date(value).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" });
  } catch {
    return value;
  }
};

const normalizeHeaders = () => ({
  "Content-Type": "application/json",
  "X-Tenant-Id": "default",
  "X-User-Id": "default",
});

export default function Home() {
  const [inputValue, setInputValue] = useState("");
  const [chunks, setChunks] = useState<StreamChunk[]>([]);
  const eventSourceRef = useRef<EventSource>();
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
      const response = await fetch(`${apiBaseUrl}/threads`);
      if (!response.ok) {
        throw new Error("Failed to load threads");
      }
      const payload: ThreadRead[] = await response.json();
      setThreads(payload);
    } catch (error: any) {
      console.error("Failed to load threads", error);
      setThreadsError(error?.message || "Failed to load threads");
    } finally {
      setLoadingThreads(false);
    }
  }, [apiBaseUrl]);

  useEffect(() => {
    if (!activeThread && threads.length > 0) {
      selectThread(threads[0].id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [threads]);

  const fetchThreadDetail = useCallback(
    async (threadId: string) => {
      const response = await fetch(`${apiBaseUrl}/threads/${threadId}`);
      if (!response.ok) {
        throw new Error("Thread not found");
      }
    const detail: ThreadDetail = await response.json();
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
    [apiBaseUrl]
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
    setActiveThread((prev) => (prev?.id === threadId ? prev : null));
    fetchThreadDetail(threadId).catch(console.error);
  };

  const deleteThread = async (threadId: string) => {
    const response = await fetch(`${apiBaseUrl}/threads/${threadId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error("Failed to delete thread");
    }
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
    const response = await fetch(`${apiBaseUrl}/threads`, {
      method: "POST",
      headers: normalizeHeaders(),
      body: JSON.stringify({ title: "New conversation" }),
    });
    if (!response.ok) {
      throw new Error("Failed to create thread");
    }
    const thread: ThreadDetail = await response.json();
    setThreads((prev) => [thread, ...prev.filter((item) => item.id !== thread.id)]);
    setActiveThread(thread);
    setChunks([]);
    setStatus("idle");
    return thread;
  }, [apiBaseUrl]);

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
    const source = new EventSource(
      `${apiBaseUrl}/chat/stream?message=${encodedPrompt}${threadParam}`
    );
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
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <div className="flex flex-1 gap-6 py-6">
        {historyVisible ? (
          <aside className="w-[320px] space-y-4 rounded-3xl border border-slate-800 bg-slate-900/70 p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">History</p>
              {loadingThreads ? (
                <span className="text-xs text-slate-500">Loading...</span>
              ) : null}
              <button
                onClick={fetchThreads}
                className="rounded-md border border-slate-700 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-slate-300 transition hover:border-slate-500"
              >
                Refresh
              </button>
            </div>
            {threadsError ? (
              <p className="text-xs text-rose-400">로드 실패: {threadsError}</p>
            ) : null}
            <div className="space-y-3">
              {threads.length === 0 ? (
                <p className="text-sm text-slate-500">No conversations yet.</p>
              ) : null}
              {threads.map((thread) => (
                <div
                  key={thread.id}
                  className={`group relative flex w-full flex-col rounded-2xl border px-3 py-3 transition ${
                    activeThread?.id === thread.id
                      ? "border-sky-400 bg-sky-500/10 text-white"
                      : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-600"
                  }`}
                >
                  <button
                    className="text-left"
                    onClick={() => selectThread(thread.id)}
                  >
                    <p className="font-semibold text-sm">{thread.title}</p>
                    <p className="text-xs text-slate-500">{formatTimestamp(thread.updated_at)}</p>
                  </button>
                  <button
                    className="absolute right-3 top-3 opacity-0 transition duration-200 group-hover:opacity-100 group-hover:pointer-events-auto rounded-full border border-red-400 px-2 py-0.5 text-[10px] uppercase tracking-[0.3em] text-red-400 hover:bg-red-500/10 pointer-events-none"
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

        <main
          className={`flex flex-1 flex-col gap-6 transition-all ${
            historyVisible ? "" : "w-full"
          }`}
        >
          <div className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h1 className="text-lg font-semibold text-white">Streaming Assistant</h1>
                <p className="text-sm text-slate-400">
                  메시지 기반 대화 기록을 저장하고, SSE로 Assistant 답변을 받습니다.
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setHistoryVisible((prev) => !prev)}
                  className="rounded-2xl border border-slate-700 px-4 py-2 text-sm uppercase tracking-[0.3em] text-slate-200 transition hover:border-slate-400"
                >
                  {historyVisible ? "Hide history" : "Show history"}
                </button>
                <button
                  onClick={startNewConversation}
                  className="rounded-2xl border border-slate-700 px-4 py-2 text-sm uppercase tracking-[0.3em] text-slate-200 transition hover:border-slate-400"
                >
                  New conversation
                </button>
              </div>
            </div>
          </div>
          <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
            <form onSubmit={handleSubmit} className="space-y-4">
              <label className="flex flex-col gap-2 text-sm text-slate-300">
                질문 입력
                <input
                  value={inputValue}
                  onChange={(event) => setInputValue(event.target.value)}
                  className="w-full rounded-2xl border border-slate-800 bg-slate-950/50 px-4 py-3 text-base text-white outline-none transition focus:border-slate-500"
                  placeholder="예: 새 프로젝트의 방향성을 요약해줘"
                />
              </label>
              <div className="flex items-center justify-between gap-3">
                <button
                  type="submit"
                  className="inline-flex items-center justify-center rounded-2xl bg-sky-500 px-6 py-3 text-sm font-semibold uppercase tracking-wide text-white transition hover:bg-sky-400 disabled:bg-slate-700"
                  disabled={!inputValue.trim() || status === "streaming"}
                >
                  {status === "streaming" ? "Streaming…" : "메시지 전송"}
                </button>
                <span
                  className={`text-xs uppercase tracking-[0.3em] ${
                    status === "error" ? "text-rose-400" : "text-slate-500"
                  }`}
                >
                  {status === "streaming" ? "SSE live" : status === "idle" ? "Ready" : "Error"}
                </span>
              </div>
            </form>
            <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-400">
              <span>API: {apiBaseUrl}</span>
              <span>SSE</span>
              <span>chat/stream</span>
              {activeThread ? <span>Thread: {activeThread.title}</span> : null}
            </div>
          </section>

          <section className="flex flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">Stream feed</p>
            <div className="flex flex-col gap-3 divide-y divide-slate-800">
              {chunks.length === 0 ? (
                <p className="text-sm text-slate-500">Streaming responses will appear here.</p>
              ) : null}
              {chunks.map((chunk, index) => (
                <div
                  key={`${chunk.type}-${index}`}
                  className="space-y-1 rounded-2xl border border-slate-800/70 bg-slate-950/50 p-3 text-sm text-slate-100"
                >
                  <span
                    className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs ${badgeStyles[chunk.type]}`}
                  >
                    {chunk.type}
                  </span>
                  <p className="whitespace-pre-wrap text-base leading-relaxed text-white">{chunk.text}</p>
                  {chunk.thread_id ? (
                    <p className="text-xs text-slate-500">Thread: {chunk.thread_id}</p>
                  ) : null}
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">References</p>
              <button
                onClick={() => setReferences([])}
                className="text-[10px] uppercase tracking-[0.3em] text-slate-500 transition hover:text-white"
              >
                Clear
              </button>
            </div>
            <div className="mt-3 space-y-3">
              {references.length === 0 ? (
                <p className="text-sm text-slate-500">References from the latest document chat will appear here.</p>
              ) : (
                references.map((reference) => (
                  <button
                    key={reference.chunk_id}
                    onClick={() => openReference(reference)}
                    className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 p-4 text-left transition hover:border-sky-500"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-white">{reference.document_title}</p>
                      <span className="text-[10px] uppercase tracking-[0.3em] text-slate-400">
                        {reference.page ? `Page ${reference.page}` : "Page unknown"}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-slate-400">{reference.snippet}</p>
                    {reference.score !== undefined ? (
                      <p className="mt-1 text-[10px] uppercase tracking-[0.3em] text-slate-500">
                        Similarity {reference.score.toFixed(2)}
                      </p>
                    ) : null}
                  </button>
                ))
              )}
            </div>
          </section>

          <section className="rounded-3xl border border-slate-800 bg-slate-900/70 p-5">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-400">Conversation</p>
              {activeThread ? (
                <p className="text-xs text-slate-500">
                  {messageFeed.length} message{messageFeed.length === 1 ? "" : "s"}
                </p>
              ) : null}
            </div>
            <div className="mt-3 space-y-3">
              {messageFeed.length === 0 ? (
                <p className="text-sm text-slate-500">Select a thread or send a prompt to start.</p>
              ) : (
                messageFeed.map((message) =>
                  message.role === "user" ? (
                    <div
                      key={message.id}
                      className="flex justify-end"
                    >
                      <div className="max-w-[70%] rounded-2xl border border-slate-700 bg-sky-500/80 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-sky-900/40">
                        <p className="text-xs uppercase tracking-[0.3em] text-sky-100">
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
                      className="rounded-3xl border border-slate-800 bg-slate-900/80 p-4 text-sm text-white shadow-inner shadow-black/50"
                    >
                      <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                        {message.role} · {formatTimestamp(message.created_at)}
                      </p>
                      <p className="mt-2 whitespace-pre-wrap text-base leading-relaxed text-slate-100">
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
