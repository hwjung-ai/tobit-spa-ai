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

  useEffect(() => {
    const key = `${STORAGE_PREFIX}${builderSlug}`;
    if (messages.length === 0) {
      window.localStorage.removeItem(key);
    } else {
      window.localStorage.setItem(key, JSON.stringify(messages));
    }
  }, [messages, builderSlug]);

  const removeMessage = (id: string) => {
    setMessages((prev) => prev.filter((m) => m.id !== id));
  };

  const handleStream = (
    prompt: string,
    options?: { persistUserMessage?: boolean; isRepair?: boolean }
  ) => {
    const persistUserMessage = options?.persistUserMessage ?? true;
    const isRepair = options?.isRepair ?? false;

    // 1. Clear previous assistant tracking
    assistantMessageIdRef.current = null;
    assistantBufferRef.current = "";

    // 2. Add user message
    if (persistUserMessage) {
      const userMsgId = generateMessageId("user");
      const timestamp = getTimestamp();
      setMessages((prev) => [...prev, { id: userMsgId, role: "user", text: prompt, timestamp }]);
    }
    setStatus("streaming");

    eventSourceRef.current?.close();

    // 3. Prepare request
    const finalPrompt = instructionPrompt
      ? `${instructionPrompt}\n\nUser Query: ${prompt}`
      : prompt;

    // Build SSE URL - use Next.js API proxy for SSE to avoid firewall issues
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

    // Use a unified message handler to avoid missing chunks
    es.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data);
        const type = payload.type;

        console.log("[Chat] SSE payload type:", type);

        if (type === "answer" || type === "text") { // Handle both just in case
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
        // Sometimes payload is just a string? 
        if (event.data && typeof event.data === 'string') {
          // Fallback if the backend sends raw strings (unlikely given orch)
        }
      }
    });

    es.onerror = (err) => {
      console.error("[Chat] SSE connection error:", err);
      // Don't kill status if we already got some meaningful content, but usually we should
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

  const panelClass = inline
    ? "flex flex-col gap-3"
    : "fixed bottom-1 right-6 z-50 flex w-80 flex-col gap-2 rounded-3xl border border-[var(--border)] bg-[var(--surface-overlay)] p-3 shadow-2xl backdrop-blur-xl max-h-[calc(100vh-0.5rem)] overflow-y-auto";

  return (
    <div className={panelClass}>
      <p className="text-xs uppercase tracking-[0.3em]  shrink-0" style={{color: "var(--muted-foreground)"}}>AI Copilot</p>
      <div className="max-h-[min(440px,calc(100vh-14rem))] overflow-y-auto rounded-2xl border   p-3 text-xs  custom-scrollbar min-h-0" style={{borderColor: "var(--border)", color: "var(--foreground)", backgroundColor: "var(--surface-overlay)"}}>
        {messages.length === 0 ? (
          <p className="text-xs " style={{color: "var(--muted-foreground)"}}>질문을 입력하면 AI가 응답합니다.</p>
        ) : (
          messages.map((message) => (
            <div key={message.id} className="group mb-2 relative flex items-start gap-2 pr-8">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase tracking-[0.3em] " style={{color: "var(--muted-foreground)"}}>
                    {message.role === "user" ? "User" : "Assistant"}
                  </span>
                  <span className="text-[9px] " style={{color: "var(--muted-foreground)"}}>
                    {new Date(message.timestamp).toLocaleString("ko-KR", {
                      year: "numeric",
                      month: "numeric",
                      day: "numeric",
                      hour: "numeric",
                      minute: "numeric",
                      second: "numeric",
                      hour12: true,
                    })}
                  </span>
                </div>
                <p className="text-sm  break-words whitespace-pre-wrap" style={{color: "var(--foreground-secondary)"}}>{message.text}</p>
              </div>
              <button
                type="button"
                onClick={() => removeMessage(message.id)}
                className="absolute right-0 top-0 hidden h-5 w-5 items-center justify-center rounded-full border border-rose-400  text-[10px] text-rose-300 transition hover:bg-rose-500/10 group-hover:flex" style={{backgroundColor: "var(--surface-base)"}}
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
          className="w-full rounded-2xl border   px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500" style={{borderColor: "var(--border)", backgroundColor: "var(--surface-overlay)"}}
          placeholder={inputPlaceholder}
        />
        <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.3em]  pt-1" style={{color: "var(--muted-foreground)"}}>
          <span className={status === "streaming" ? "animate-pulse text-sky-400 font-bold" : ""}>
            {status === "streaming" ? "Streaming…" : status === "error" ? "Error" : "Ready"}
          </span>
          <button
            type="submit"
            className="rounded-full border px-4 py-1 text-white transition disabled:opacity-50"
            style={{borderColor: "var(--border)", backgroundColor: "var(--primary)"}}
            disabled={!inputValue.trim() || status === "streaming"}
            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = "var(--primary-foreground)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = "var(--primary)"; }}
          >
            Send
          </button>
        </div>
      </form>

      <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
        .animate-pulse {
          animation: pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
      `}</style>
    </div>
  );
}
