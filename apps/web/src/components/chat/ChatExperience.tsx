"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

const STORAGE_PREFIX = "chat:tobit:";

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

  const handleStream = (prompt: string) => {
    // 1. Clear previous assistant tracking
    assistantMessageIdRef.current = null;
    assistantBufferRef.current = "";

    // 2. Add user message
    const userMsgId = `user-${Date.now()}`;
    const timestamp = Date.now();
    setMessages((prev) => [...prev, { id: userMsgId, role: "user", text: prompt, timestamp }]);
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
      streamUrl = `/api/proxy-sse/chat/stream?${params.toString()}`;
    } else {
      const url = new URL(`${apiBaseUrl}/chat/stream`);
      url.searchParams.set("message", finalPrompt);
      url.searchParams.set("builder", builderSlug);
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
              const newId = `assistant-${Date.now()}`;
              assistantMessageIdRef.current = newId;
              return [...prev, { id: newId, role: "assistant", text: chunk, timestamp: Date.now() }];
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
          setStatus("idle");
          if (onAssistantMessageComplete) {
            onAssistantMessageComplete(assistantBufferRef.current);
          }
          assistantMessageIdRef.current = null;
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
    if (onUserMessage) {
      onUserMessage(val);
    }
    handleStream(val);
  };

  const panelClass = inline
    ? "flex flex-col gap-3"
    : "fixed bottom-1 right-6 z-50 flex w-80 flex-col gap-2 rounded-3xl border border-slate-800 bg-slate-900/90 p-3 shadow-2xl backdrop-blur-xl max-h-[calc(100vh-0.5rem)] overflow-y-auto";

  return (
    <div className={panelClass}>
      <p className="text-xs uppercase tracking-[0.3em] text-slate-500 shrink-0">AI Copilot</p>
      <div className="max-h-[min(440px,calc(100vh-14rem))] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950/60 p-3 text-[12px] text-slate-100 custom-scrollbar min-h-0">
        {messages.length === 0 ? (
          <p className="text-xs text-slate-500">질문을 입력하면 AI가 응답합니다.</p>
        ) : (
          messages.map((message) => (
            <div key={message.id} className="group mb-2 relative flex items-start gap-2 pr-8">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                    {message.role === "user" ? "User" : "Assistant"}
                  </span>
                  <span className="text-[9px] text-slate-600">
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
                <p className="text-sm text-slate-200 break-words whitespace-pre-wrap">{message.text}</p>
              </div>
              <button
                type="button"
                onClick={() => removeMessage(message.id)}
                className="absolute right-0 top-0 hidden h-5 w-5 items-center justify-center rounded-full border border-rose-400 bg-slate-950 text-[10px] text-rose-300 transition hover:bg-rose-500/10 group-hover:flex"
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
          className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
          placeholder={inputPlaceholder}
        />
        <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.3em] text-slate-400 pt-1">
          <span className={status === "streaming" ? "animate-pulse text-sky-400 font-bold" : ""}>
            {status === "streaming" ? "Streaming…" : status === "error" ? "Error" : "Ready"}
          </span>
          <button
            type="submit"
            className="rounded-full border border-slate-100/10 bg-sky-500/80 px-4 py-1 text-white transition hover:bg-sky-400 disabled:bg-slate-700"
            disabled={!inputValue.trim() || status === "streaming"}
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
