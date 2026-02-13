"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  buildRepairPrompt,
  type CopilotContract,
  validateCopilotContract,
} from "@/lib/copilot/contract-utils";
import { recordCopilotMetric } from "@/lib/copilot/metrics";

const STORAGE_PREFIX = "chat:tobit:";
const getTimestamp = () => new Date().getTime();
const generateMessageId = (role: ChatRole) =>
  `${role}-${typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)}`;

type ChatRole = "user" | "assistant";

interface Message {
  id: string;
  role: ChatRole;
  text: string;
  timestamp: number;
}

interface ChatExperienceProps {
  builderSlug?: string;
  inline?: boolean;
  expectedContract?: CopilotContract;
  builderContext?: Record<string, unknown> | null;
  enableAutoRepair?: boolean;
  onAssistantMessage?: (text: string) => void;
  onAssistantMessageComplete?: (text: string) => void;
  onUserMessage?: (text: string) => void;
  instructionPrompt?: string;
  inputPlaceholder?: string;
}

const normalizeBaseUrl = (value: string | undefined) => {
  const baseUrl = value?.replace(/\/+$/, "") ?? "";
  return baseUrl;
};

const formatTimestamp = (ts: number) =>
  new Date(ts).toLocaleString("ko-KR", {
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
    hour12: true,
  });

export default function ChatExperience({
  builderSlug = "api-manager",
  inline = false,
  expectedContract,
  builderContext,
  enableAutoRepair = true,
  onAssistantMessage,
  onAssistantMessageComplete,
  onUserMessage,
  instructionPrompt,
  inputPlaceholder = "메시지를 입력하세요.",
}: ChatExperienceProps) {
  const [messages, setMessages] = useState<Message[]>(() => {
    if (typeof window === "undefined") return [];
    const key = `${STORAGE_PREFIX}${builderSlug}`;
    const raw = window.localStorage.getItem(key);
    if (raw) {
      try {
        return JSON.parse(raw);
      } catch {
        window.localStorage.removeItem(key);
        return [];
      }
    }
    return [];
  });
  const [inputValue, setInputValue] = useState("");
  const [status, setStatus] = useState<"idle" | "streaming" | "error">("idle");
  const eventSourceRef = useRef<EventSource | null>(null);

  const assistantMessageIdRef = useRef<string | null>(null);
  const assistantBufferRef = useRef<string>("");
  const lastUserPromptRef = useRef<string>("");
  const repairAttemptRef = useRef<number>(0);
  const apiBaseUrl = useMemo(() => normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL), []);

  // Resize handle state (full-page mode only)
  const [leftPanelWidth, setLeftPanelWidth] = useState(340);
  const [isResizing, setIsResizing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Selected message for highlighting in history
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);

  useEffect(() => {
    const key = `${STORAGE_PREFIX}${builderSlug}`;
    if (messages.length === 0) {
      window.localStorage.removeItem(key);
    } else {
      window.localStorage.setItem(key, JSON.stringify(messages));
    }
  }, [messages, builderSlug]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Resize handler
  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      setLeftPanelWidth(Math.max(250, Math.min(600, e.clientX - rect.left)));
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
  }, [isResizing]);

  const removeMessage = (id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  };

  const clearAllMessages = () => {
    setMessages([]);
    setSelectedMessageId(null);
  };

  const handleStream = (
    prompt: string,
    options?: { persistUserMessage?: boolean; isRepair?: boolean }
  ) => {
    const persistUserMessage = options?.persistUserMessage ?? true;
    const isRepair = options?.isRepair ?? false;

    assistantMessageIdRef.current = null;
    assistantBufferRef.current = "";

    if (persistUserMessage) {
      const userMsgId = generateMessageId("user");
      const timestamp = getTimestamp();
      setMessages((prev) => [...prev, { id: userMsgId, role: "user", text: prompt, timestamp }]);
    }
    setStatus("streaming");

    eventSourceRef.current?.close();

    const finalPrompt = instructionPrompt
      ? `${instructionPrompt}\n\nUser Query: ${prompt}`
      : prompt;

    let streamUrl: string;
    if (!apiBaseUrl) {
      const params = new URLSearchParams({
        message: finalPrompt,
        builder: builderSlug,
      });
      if (expectedContract) {
        params.set("expected_contract", expectedContract);
      }
      if (builderContext) {
        params.set("builder_context", JSON.stringify(builderContext));
      }
      streamUrl = `/sse-proxy/chat/stream?${params.toString()}`;

    } else {
      const url = new URL(`${apiBaseUrl}/chat/stream`);
      url.searchParams.set("message", finalPrompt);
      url.searchParams.set("builder", builderSlug);
      if (expectedContract) {
        url.searchParams.set("expected_contract", expectedContract);
      }
      if (builderContext) {
        url.searchParams.set("builder_context", JSON.stringify(builderContext));
      }
      streamUrl = url.toString();
    }

    console.log("[Chat] Opening SSE stream:", streamUrl);
    const es = new EventSource(streamUrl);
    eventSourceRef.current = es;

    es.onopen = () => {
      console.log("[Chat] SSE opened");
    };

    es.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data);
        const type = payload.type;

        console.log("[Chat] SSE payload type:", type);

        if (type === "answer" || type === "text") {
          const chunk = payload.text || "";
          assistantBufferRef.current += chunk;

          setMessages((prev) => {
            if (!assistantMessageIdRef.current) {
              console.log("[Chat] Creating new assistant message entry");
              const newId = generateMessageId("assistant");
              assistantMessageIdRef.current = newId;
              return [...prev, { id: newId, role: "assistant", text: chunk, timestamp: getTimestamp() }];
            }
            return prev.map((m) =>
              m.id === assistantMessageIdRef.current ? { ...m, text: m.text + chunk } : m
            );
          });

          if (onAssistantMessage) {
            onAssistantMessage(assistantBufferRef.current);
          }
        } else if (type === "done") {
          console.log("[Chat] SSE done");
          es.close();
          const finalText = assistantBufferRef.current;
          const validation = validateCopilotContract(expectedContract, finalText);

          if (expectedContract && validation.ok) {
            recordCopilotMetric(builderSlug, "contract_ok");
          } else if (expectedContract && !validation.ok) {
            recordCopilotMetric(builderSlug, "contract_violation", validation.reason);
          }

          if (
            expectedContract &&
            !validation.ok &&
            enableAutoRepair &&
            repairAttemptRef.current < 1
          ) {
            recordCopilotMetric(builderSlug, "auto_repair_attempt", validation.reason);
            const invalidAssistantMessageId = assistantMessageIdRef.current;
            if (invalidAssistantMessageId) {
              setMessages((prev) => prev.filter((msg) => msg.id !== invalidAssistantMessageId));
            }
            assistantMessageIdRef.current = null;
            assistantBufferRef.current = "";
            repairAttemptRef.current += 1;

            const repairPrompt = buildRepairPrompt({
              contract: expectedContract,
              originalUserPrompt: lastUserPromptRef.current || "(empty)",
              previousAssistantResponse: finalText,
            });
            handleStream(repairPrompt, { persistUserMessage: false, isRepair: true });
            return;
          }

          if (isRepair) {
            if (validation.ok) {
              recordCopilotMetric(builderSlug, "auto_repair_success");
            } else {
              recordCopilotMetric(builderSlug, "auto_repair_failed", validation.reason);
            }
          }

          setStatus("idle");
          if (onAssistantMessageComplete) {
            onAssistantMessageComplete(finalText);
          }
          assistantMessageIdRef.current = null;
          assistantBufferRef.current = "";
        } else if (type === "error") {
          console.error("[Chat] SSE payload error:", payload.text);
          setStatus("error");
          es.close();
        }
      } catch (err) {
        console.error("[Chat] SSE parse error:", err, event.data);
      }
    });

    es.onerror = (err) => {
      console.error("[Chat] SSE connection error:", err);
      if (!assistantBufferRef.current) {
        setStatus("error");
      } else {
        setStatus("idle");
      }
      es.close();
    };
  };

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (status === "streaming" || !inputValue.trim()) {
      return;
    }
    const val = inputValue.trim();
    setInputValue("");
    lastUserPromptRef.current = val;
    repairAttemptRef.current = 0;
    if (onUserMessage) {
      onUserMessage(val);
    }
    handleStream(val, { persistUserMessage: true });
  };

  // Group messages into conversation pairs (user + assistant)
  const conversationPairs = useMemo(() => {
    const pairs: { userMsg: Message; assistantMsg?: Message }[] = [];
    for (let i = 0; i < messages.length; i++) {
      const msg = messages[i];
      if (msg.role === "user") {
        const next = messages[i + 1];
        pairs.push({
          userMsg: msg,
          assistantMsg: next?.role === "assistant" ? next : undefined,
        });
        if (next?.role === "assistant") i++;
      }
    }
    return pairs;
  }, [messages]);

  // ── Inline / Floating mode (original) ──
  if (inline) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-xs uppercase tracking-wider text-muted-foreground shrink-0">AI Copilot</p>
        <div className="max-h-[min(440px,calc(100vh-14rem))] overflow-y-auto rounded-2xl border border-border p-3 text-xs custom-scrollbar min-h-0 bg-surface-overlay text-foreground">
          {messages.length === 0 ? (
            <p className="text-xs text-muted-foreground">질문을 입력하면 AI가 응답합니다.</p>
          ) : (
            messages.map((message) => (
              <div key={message.id} className="group mb-2 relative flex items-start gap-2 pr-8">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-tiny uppercase tracking-wider text-muted-foreground">
                      {message.role === "user" ? "User" : "Assistant"}
                    </span>
                    <span className="text-xs-9px text-muted-foreground">
                      {formatTimestamp(message.timestamp)}
                    </span>
                  </div>
                  <p className="text-sm break-words whitespace-pre-wrap text-foreground">{message.text}</p>
                </div>
                <button
                  type="button"
                  onClick={() => removeMessage(message.id)}
                  className="absolute right-0 top-0 hidden h-5 w-5 items-center justify-center rounded-full border border-rose-400 bg-surface-base text-tiny text-rose-300 transition hover:bg-rose-500/10 group-hover:flex"
                  aria-label="Delete message"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
        <form onSubmit={handleSubmit} className="space-y-1.5 shrink-0">
          <textarea
            rows={2}
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            className="w-full rounded-2xl border px-3 py-2 text-sm outline-none transition focus:border-primary input-container"
            placeholder={inputPlaceholder}
          />
          <div className="flex items-center justify-between text-tiny uppercase tracking-wider text-muted-foreground pt-1">
            <span className={status === "streaming" ? "animate-pulse text-sky-400 font-bold" : ""}>
              {status === "streaming" ? "Streaming…" : status === "error" ? "Error" : "Ready"}
            </span>
            <button
              type="submit"
              className="btn-primary rounded-full px-4 py-1 text-sm disabled:opacity-50"
              disabled={!inputValue.trim() || status === "streaming"}
            >
              Send
            </button>
          </div>
        </form>
      </div>
    );
  }

  // ── Full-page 2-panel mode (left history + resize handle + right chat) ──
  const builderLabel = builderSlug === "cep-builder" ? "CEP Builder" : "API Manager";

  return (
    <div
      ref={containerRef}
      className="flex h-full w-full gap-0 overflow-visible"

    >
      {/* ── Left Panel: Conversation History ── */}
      <div
        className="flex flex-shrink-0 flex-col rounded-3xl border p-4 bg-surface-base dark:border-border overflow-hidden"
        style={{ width: `${leftPanelWidth}px` }}
      >
        <div className="mb-3 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-wider text-muted-foreground">
              {builderLabel} Chat
            </p>
            <p className="text-lg font-semibold text-foreground">대화 이력</p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={clearAllMessages}
              className="rounded-full border border-rose-400 px-3 py-1 text-xs text-rose-400 transition hover:bg-rose-500/10"
            >
              전체 삭제
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar space-y-2">
          {conversationPairs.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              아직 대화 이력이 없습니다.
            </p>
          ) : (
            conversationPairs.map((pair) => (
              <div
                key={pair.userMsg.id}
                onClick={() => setSelectedMessageId(pair.userMsg.id)}
                className={`group relative cursor-pointer rounded-2xl border p-3 transition hover:bg-surface-elevated ${
                  selectedMessageId === pair.userMsg.id
                    ? "border-sky-500 bg-sky-500/5"
                    : "border-border"
                }`}
              >
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-tiny uppercase tracking-wider font-medium">
                    User
                  </span>
                  <span className="text-tiny tracking-normal">
                    {formatTimestamp(pair.userMsg.timestamp)}
                  </span>
                </div>
                <p className="mt-1 text-sm font-medium leading-snug line-clamp-2 text-foreground">
                  {pair.userMsg.text}
                </p>
                {pair.assistantMsg && (
                  <p className="mt-1 text-xs line-clamp-2 text-muted-foreground">
                    {pair.assistantMsg.text}
                  </p>
                )}
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    removeMessage(pair.userMsg.id);
                    if (pair.assistantMsg) removeMessage(pair.assistantMsg.id);
                  }}
                  className="absolute right-2 top-2 hidden h-5 w-5 items-center justify-center rounded-full border border-rose-400 bg-surface-base text-tiny text-rose-400 transition group-hover:flex"
                >
                  ✕
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ── Resize Handle ── */}
      <div
        onMouseDown={(event) => {
          event.preventDefault();
          setIsResizing(true);
        }}
        className={`resize-handle-col ${isResizing ? "is-active" : ""}`}
        onDoubleClick={() => setLeftPanelWidth(340)}
        aria-label="Resize panels"
        role="separator"
        aria-orientation="vertical"
        data-testid="chat-panel-resize-handle"
      >
        <div className="resize-handle-grip" />
      </div>

      {/* ── Right Panel: Active Chat ── */}
      <section className="flex flex-1 flex-col rounded-3xl border p-4 shadow-inner shadow-black/40 bg-surface-base dark:border-border overflow-hidden">
        <header className="mb-3 shrink-0">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">
            AI Copilot
          </p>
          <h1 className="text-lg font-semibold text-foreground">
            {builderLabel} Assistant
          </h1>
        </header>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto rounded-2xl border border-border p-4 custom-scrollbar bg-surface-overlay">
          {messages.length === 0 ? (
            <div className="flex h-full items-center justify-center">
              <p className="text-sm text-muted-foreground">질문을 입력하면 AI가 응답합니다.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  id={`msg-${message.id}`}
                  className={`group relative flex items-start gap-3 pr-8 ${
                    selectedMessageId === message.id ? "rounded-xl bg-sky-500/5 p-2 -m-2" : ""
                  }`}
                >
                  <div
                    className={`mt-1 h-7 w-7 shrink-0 rounded-full flex items-center justify-center text-tiny font-bold uppercase ${
                      message.role === "user"
                        ? "bg-sky-600 text-white"
                        : "bg-emerald-600 text-white"
                    }`}
                  >
                    {message.role === "user" ? "U" : "A"}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
                        {message.role === "user" ? "User" : "Assistant"}
                      </span>
                      <span className="text-tiny text-muted-foreground">
                        {formatTimestamp(message.timestamp)}
                      </span>
                    </div>
                    <p className="mt-1 text-sm break-words whitespace-pre-wrap leading-relaxed text-foreground">
                      {message.text}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeMessage(message.id)}
                    className="absolute right-0 top-0 hidden h-5 w-5 items-center justify-center rounded-full border border-rose-400 bg-surface-base text-tiny text-rose-300 transition hover:bg-rose-500/10 group-hover:flex"
                    aria-label="Delete message"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input area */}
        <form onSubmit={handleSubmit} className="mt-3 shrink-0 space-y-2">
          <textarea
            rows={3}
            value={inputValue}
            onChange={(event) => setInputValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleSubmit(event);
              }
            }}
            className="w-full resize-none rounded-2xl border px-4 py-3 text-sm outline-none transition focus:border-primary input-container"
            placeholder={inputPlaceholder}
          />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className={status === "streaming" ? "animate-pulse text-sky-400 font-bold" : ""}>
              {status === "streaming"
                ? "Streaming…"
                : status === "error"
                  ? "Error"
                  : "Ready"}
            </span>
            <div className="flex items-center gap-2">
              <span className="text-tiny text-muted-foreground">
                Shift+Enter: 줄바꿈
              </span>
              <button
                type="submit"
                className="btn-primary rounded-full px-5 py-2 text-sm disabled:opacity-50"
                disabled={!inputValue.trim() || status === "streaming"}
              >
                Send
              </button>
            </div>
          </div>
        </form>
      </section>
    </div>
  );
}
