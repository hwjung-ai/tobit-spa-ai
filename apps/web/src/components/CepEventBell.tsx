"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useQuery, useQueryClient } from "@tanstack/react-query";

type SummaryPayload = {
  unacked_count: number;
  by_severity: Record<string, number>;
};

const normalizeBaseUrl = (value?: string) => {
  if (!value) {
    return "";
  }
  return value.endsWith("/") ? value.slice(0, -1) : value;
};

const normalizeError = (error: unknown) => {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  try {
    return JSON.stringify(error);
  } catch {
    return "Unknown error";
  }
};

export default function CepEventBell() {
  const apiBaseUrl = normalizeBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
  const [pulse, setPulse] = useState(false);
  const previousCount = useRef<number>(0);
  const queryClient = useQueryClient();

  const summaryQuery = useQuery({
    queryKey: ["cep-events-summary"],
    queryFn: async () => {
      const response = await fetch(`${apiBaseUrl}/cep/events/summary`);
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "Failed to load summary");
      }
      return payload.data?.summary as SummaryPayload;
    },
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  useEffect(() => {
    const eventSource = new EventSource(`${apiBaseUrl}/cep/events/stream`);
    const handleSummary = (event: MessageEvent) => {
      const data = JSON.parse(event.data) as SummaryPayload;
      queryClient.setQueryData(["cep-events-summary"], data);
      const current = data?.unacked_count ?? 0;
      if (current > previousCount.current) {
        setPulse(true);
        window.setTimeout(() => setPulse(false), 1500);
      }
      previousCount.current = current;
    };
    eventSource.addEventListener("summary", handleSummary);
    eventSource.addEventListener("error", () => {
      // Error is handled by summaryQuery.error
    });
    return () => eventSource.close();
  }, [apiBaseUrl, queryClient]);

  const summary = summaryQuery.data ?? null;
  const error = summaryQuery.error ? normalizeError(summaryQuery.error) : null;
  const count = summary?.unacked_count ?? 0;

  return (
    <Link
      href="/cep-events"
      className="relative flex h-9 w-9 items-center justify-center rounded-full border border-slate-800 bg-slate-950/70 text-slate-200 transition hover:border-slate-600"
      title={error ? `Event summary error: ${error}` : "CEP Event Browser"}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="currentColor"
        className="h-4 w-4"
      >
        <path d="M12 2a7 7 0 0 0-7 7v3.2l-1.2 2.4A1 1 0 0 0 4.7 16h14.6a1 1 0 0 0 .9-1.4L19 12.2V9a7 7 0 0 0-7-7zm0 20a2.5 2.5 0 0 0 2.4-2H9.6A2.5 2.5 0 0 0 12 22z" />
      </svg>
      {count > 0 ? (
        <span
          className={`absolute -right-1 -top-1 flex h-5 min-w-[20px] items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-semibold text-white ${
            pulse ? "animate-pulse" : ""
          }`}
        >
          {count}
        </span>
      ) : null}
    </Link>
  );
}
