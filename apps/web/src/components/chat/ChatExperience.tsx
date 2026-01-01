"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

const STORAGE_PREFIX = "chat:tobit:";

type ChatRole = "user" | "assistant";

interface Message {
  id: string;
  role: ChatRole;
  text: string;
}

interface ChatExperienceProps {
  builderSlug?: string;
  inline?: boolean;
  onAssistantMessage?: (text: string) => void;
  onAssistantMessageComplete?: (text: string) => void;
  instructionPrompt?: string;
}

const normalizeBaseUrl = (value: string | undefined) => value?.replace(/\/+$/, "") ?? "http://localhost:8000";

export default function ChatExperience({
  builderSlug = "api-manager",
  inline = false,
  onAssistantMessage,
  onAssistantMessageComplete,
}: ChatExperienceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [status, setStatus] = useState<"idle" | "streaming" | "error">("idle");
  const eventSourceRef = useRef<EventSource | null>(null);

  const storageKey = `${STORAGE_PREFIX}${builderSlug}`;

  useEffect(() => {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) {
      return;
    }
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed.messages)) {
        return;
      }
      setMessages(parsed.messages);
    } catch {
      window.localStorage.removeItem(storageKey);
    }
  }, [storageKey]);

  useEffect(() => {
    const payload = { messages };
    if (messages.length === 0) {
      window.localStorage.removeItem(storageKey);
      return;
    }
    window.localStorage.setItem(storageKey, JSON.stringify(payload));
  }, [messages, storageKey]);

  useEffect(() => {
    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  const addAssistantMessage = useRef<string | null>(null);
  const lastAssistantText = useRef<string>("");

  const handleStream = (prompt: string) => {
    const key = Date.now().toString();
    setMessages((prev) => [...prev, { id: key, role: "user", text: prompt }]);
    setStatus("streaming");
    eventSourceRef.current?.close();
    const finalPrompt = instructionPrompt
      ? `${instructionPrompt}\n\n${prompt}`
      : prompt;
    const encoded = encodeURIComponent(finalPrompt);
    const source = new EventSource(
      `${normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL)}/chat/stream?message=${encoded}&builder=${encodeURIComponent(builderSlug)}`
    );
    lastAssistantText.current = "";
    eventSourceRef.current = source;
    addAssistantMessage.current = null;

    source.addEventListener("message", (event) => {
      try {
        const payload = JSON.parse(event.data);
      if (payload.type === "answer") {
        setMessages((prev) => {
          const lastAssistantIdx = prev.findIndex(
            (item) => item.role === "assistant" && item.id === addAssistantMessage.current
          );
          if (lastAssistantIdx >= 0) {
            const updated = [...prev];
            updated[lastAssistantIdx] = {
              ...updated[lastAssistantIdx],
              text: updated[lastAssistantIdx].text + payload.text,
            };
            onAssistantMessage?.(updated[lastAssistantIdx].text);
            lastAssistantText.current = updated[lastAssistantIdx].text;
            return updated;
          }
          const id = `${payload.thread_id ?? "assistant"}-${Date.now()}`;
          addAssistantMessage.current = id;
          const newMessage = { id, role: "assistant" as ChatRole, text: payload.text };
          lastAssistantText.current = payload.text;
          onAssistantMessage?.(newMessage.text);
          return [...prev, newMessage];
        });
      }
      if (payload.type === "done") {
        setStatus("idle");
        onAssistantMessageComplete?.(lastAssistantText.current);
        source.close();
      }
        if (payload.type === "error") {
          setStatus("error");
          source.close();
        }
      } catch (error) {
        console.error("Chat stream parse error", error);
        setStatus("error");
        source.close();
      }
    });

    source.addEventListener("error", () => {
      setStatus("error");
      source.close();
    });
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!inputValue.trim()) {
      return;
    }
    handleStream(inputValue.trim());
    setInputValue("");
  };

  const panelClass = inline
    ? "space-y-3 rounded-3xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300"
    : "space-y-4 rounded-3xl border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-300";

  return (
    <div className={panelClass}>
      <p className="text-xs uppercase tracking-[0.3em] text-slate-500">AI Copilot</p>
      <div className="max-h-[220px] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950/60 p-3 text-[12px] text-slate-100">
        {messages.length === 0 ? (
          <p className="text-xs text-slate-500">질문을 입력하면 AI가 응답합니다.</p>
        ) : (
          messages.map((message) => (
            <div key={message.id} className="mb-2">
              <span className="text-[10px] uppercase tracking-[0.3em] text-slate-500">
                {message.role === "user" ? "User" : "Assistant"}
              </span>
              <p className="text-sm text-slate-200">{message.text}</p>
            </div>
          ))
        )}
      </div>
      <form onSubmit={handleSubmit} className="space-y-2">
        <textarea
          rows={3}
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          className="w-full rounded-2xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-sm text-white outline-none transition focus:border-sky-500"
          placeholder="Ask about API drafts..."
        />
        <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.3em] text-slate-400">
          <span>{status === "streaming" ? "Streaming…" : status === "error" ? "Error" : "Ready"}</span>
          <button
            type="submit"
            className="rounded-full border border-slate-800 bg-sky-500/80 px-4 py-1 text-white transition hover:bg-sky-400 disabled:bg-slate-700"
            disabled={!inputValue.trim() || status === "streaming"}
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
