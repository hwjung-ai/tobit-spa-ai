"use client";

import React, { useEffect, useId, useMemo, useRef, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import VisualEditor from "./visual/VisualEditor";
import JsonEditor from "./json/JsonEditor";
import BindingTab from "./binding/BindingTab";
import ActionTab from "./actions/ActionTab";
import PreviewTab from "./preview/PreviewTab";
import DiffTab from "./diff/DiffTab";
import { useEditorState } from "@/lib/ui-screen/editor-state";
import { fetchApi } from "@/lib/adminUtils";
import { CRDTCollaboration } from "@/lib/ui-screen/crdt-collaboration";

interface PresenceSession {
  session_id: string;
  user_id: string;
  user_label: string;
  tab_name?: string;
  last_seen_at: string;
}

export default function ScreenEditorTabs() {
  const disableRealtime = process.env.NEXT_PUBLIC_E2E_DISABLE_REALTIME === "true";
  const [activeTab, setActiveTab] = useState("visual");
  const [hasEditorConflict, setHasEditorConflict] = useState(false);
  const [lockOwner, setLockOwner] = useState<string>("");
  const [activeEditors, setActiveEditors] = useState<string[]>([]);
  const [serverEditors, setServerEditors] = useState<PresenceSession[]>([]);
  const [presenceConnected, setPresenceConnected] = useState(false);
  const [collabConnected, setCollabConnected] = useState(false);
  const stableTabId = useId();
  const [tabSessionId] = useState(() => `tab-${stableTabId.replace(/[:]/g, "")}`);
  const screenId = useEditorState((state) => state.screen?.screen_id || "");
  const screen = useEditorState((state) => state.screen);
  const applyRemoteScreen = useEditorState((state) => state.applyRemoteScreen);
  const collabRef = useRef<CRDTCollaboration | null>(null);
  const collabSendTimerRef = useRef<number | null>(null);
  const applyingRemoteRef = useRef(false);
  const lockKey = useMemo(
    () => (screenId ? `screen_editor_lock:${screenId}` : ""),
    [screenId]
  );
  const presenceKey = useMemo(
    () => (screenId ? `screen_editor_presence:${screenId}` : ""),
    [screenId]
  );

  useEffect(() => {
    if (!lockKey || typeof window === "undefined") {
      return;
    }

    const isFresh = (ts: number) => Date.now() - ts < 15000;
    const readPresence = () => {
      if (!presenceKey) return {};
      const raw = window.localStorage.getItem(presenceKey);
      if (!raw) return {};
      try {
        return JSON.parse(raw) as Record<string, number>;
      } catch {
        return {};
      }
    };
    const writePresence = (presence: Record<string, number>) => {
      if (!presenceKey) return;
      window.localStorage.setItem(presenceKey, JSON.stringify(presence));
    };
    const compactPresence = (presence: Record<string, number>) => {
      const next: Record<string, number> = {};
      for (const [id, ts] of Object.entries(presence)) {
        if (isFresh(ts)) {
          next[id] = ts;
        }
      }
      return next;
    };
    const refreshPresenceState = () => {
      const compacted = compactPresence(readPresence());
      const ids = Object.keys(compacted).sort();
      setActiveEditors(ids);
      writePresence(compacted);
    };

    const claimLock = (force = false) => {
      const raw = window.localStorage.getItem(lockKey);
      let current: { owner: string; ts: number } | null = null;
      if (raw) {
        try {
          current = JSON.parse(raw) as { owner: string; ts: number };
        } catch {
          current = null;
        }
      }

      if (
        force ||
        !current ||
        !isFresh(current.ts) ||
        current.owner === tabSessionId
      ) {
        const next = { owner: tabSessionId, ts: Date.now() };
        window.localStorage.setItem(lockKey, JSON.stringify(next));
        setHasEditorConflict(false);
        setLockOwner("");
        return true;
      }

      setHasEditorConflict(true);
      setLockOwner(current.owner);
      return false;
    };

    const heartbeat = () => {
      const now = Date.now();
      const currentPresence = compactPresence(readPresence());
      currentPresence[tabSessionId] = now;
      writePresence(currentPresence);
      setActiveEditors(Object.keys(currentPresence).sort());

      const raw = window.localStorage.getItem(lockKey);
      if (!raw) return;
      try {
        const current = JSON.parse(raw) as { owner: string; ts: number };
        if (current.owner === tabSessionId) {
          window.localStorage.setItem(
            lockKey,
            JSON.stringify({ owner: tabSessionId, ts: now })
          );
        }
      } catch {
        // ignore malformed lock payload
      }
    };

    const onStorage = (event: StorageEvent) => {
      if (event.key === presenceKey) {
        refreshPresenceState();
        return;
      }
      if (event.key === lockKey && event.newValue) {
        try {
          const next = JSON.parse(event.newValue) as { owner: string; ts: number };
          if (next.owner !== tabSessionId && isFresh(next.ts)) {
            setHasEditorConflict(true);
            setLockOwner(next.owner);
          } else if (next.owner === tabSessionId) {
            setHasEditorConflict(false);
            setLockOwner("");
          }
        } catch {
          // ignore malformed update
        }
      }
    };

    const onBeforeUnload = () => {
      const currentPresence = compactPresence(readPresence());
      delete currentPresence[tabSessionId];
      writePresence(currentPresence);

      const raw = window.localStorage.getItem(lockKey);
      if (!raw) return;
      try {
        const current = JSON.parse(raw) as { owner: string; ts: number };
        if (current.owner === tabSessionId) {
          window.localStorage.removeItem(lockKey);
        }
      } catch {
        // ignore malformed lock payload
      }
    };

    claimLock(false);
    heartbeat();
    refreshPresenceState();
    const timer = window.setInterval(() => {
      if (!hasEditorConflict) {
        heartbeat();
      } else {
        refreshPresenceState();
      }
    }, 5000);
    window.addEventListener("storage", onStorage);
    window.addEventListener("beforeunload", onBeforeUnload);

    return () => {
      window.clearInterval(timer);
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("beforeunload", onBeforeUnload);
      onBeforeUnload();
    };
  }, [hasEditorConflict, lockKey, presenceKey, tabSessionId]);

  useEffect(() => {
    if (disableRealtime || !screenId || typeof window === "undefined") {
      return;
    }

    const sessionId = tabSessionId;
    let disposed = false;
    let source: EventSource | null = null;

    const applySessions = (sessions: unknown) => {
      if (!Array.isArray(sessions)) return;
      const parsed = sessions
        .map((item) => item as Record<string, unknown>)
        .filter((item) => typeof item.session_id === "string" && typeof item.user_label === "string")
        .map(
          (item) =>
            ({
              session_id: String(item.session_id),
              user_id: String(item.user_id || ""),
              user_label: String(item.user_label || "unknown"),
              tab_name: item.tab_name ? String(item.tab_name) : "",
              last_seen_at: String(item.last_seen_at || ""),
            }) satisfies PresenceSession
        );
      setServerEditors(parsed);
      const others = parsed.filter((item) => item.session_id !== sessionId);
      if (others.length > 0) {
        setHasEditorConflict(true);
        setLockOwner(others[0].user_label || others[0].session_id);
      } else {
        setHasEditorConflict(false);
        setLockOwner("");
      }
    };

    const sendHeartbeat = async () => {
      try {
        const envelope = await fetchApi<{
          sessions?: PresenceSession[];
        }>("/ops/ui-editor/presence/heartbeat", {
          method: "POST",
          body: JSON.stringify({
            screen_id: screenId,
            session_id: sessionId,
            tab_name: activeTab,
          }),
        });
        if (disposed) return;
        applySessions(envelope?.data?.sessions);
      } catch {
        // Keep local fallback presence when server heartbeat fails.
      }
    };

    const openStream = () => {
      const token =
        typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
      const params = new URLSearchParams({
        screen_id: screenId,
        session_id: sessionId,
        tab_name: activeTab,
      });
      if (token) {
        params.set("token", token);
      }
      source = new EventSource(`/sse-proxy/ops/ui-editor/presence/stream?${params.toString()}`);
      source.addEventListener("open", () => {
        if (disposed) return;
        setPresenceConnected(true);
      });
      source.addEventListener("presence", (event) => {
        if (disposed) return;
        try {
          const payload = JSON.parse((event as MessageEvent).data || "{}") as {
            sessions?: PresenceSession[];
          };
          applySessions(payload.sessions);
        } catch {
          // ignore malformed event payload
        }
      });
      source.addEventListener("error", () => {
        if (disposed) return;
        setPresenceConnected(false);
      });
    };

    void sendHeartbeat();
    openStream();
    const heartbeatTimer = window.setInterval(() => {
      void sendHeartbeat();
    }, 5000);

    return () => {
      disposed = true;
      window.clearInterval(heartbeatTimer);
      if (source) {
        source.close();
      }
      void fetchApi("/ops/ui-editor/presence/leave", {
        method: "POST",
        body: JSON.stringify({
          screen_id: screenId,
          session_id: sessionId,
          tab_name: activeTab,
        }),
      });
    };
  }, [activeTab, disableRealtime, screenId, tabSessionId]);

  useEffect(() => {
    if (disableRealtime || !screenId || typeof window === "undefined") return;
    const tenantId =
      localStorage.getItem("tenant_id") ||
      process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID ||
      "default";
    const userId = localStorage.getItem("user_id") || `local-${tabSessionId}`;
    const userLabel = localStorage.getItem("username") || userId;

    const collab = new CRDTCollaboration({
      screenId,
      tenantId,
      sessionId: tabSessionId,
      userId,
      userLabel,
      onConnectionChange: setCollabConnected,
      onRemoteScreen: (remoteScreen, updatedAt) => {
        applyingRemoteRef.current = true;
        applyRemoteScreen(remoteScreen, updatedAt ?? null);
        window.setTimeout(() => {
          applyingRemoteRef.current = false;
        }, 0);
      },
      onError: () => {
        setCollabConnected(false);
      },
    });
    collabRef.current = collab;

    return () => {
      if (collabSendTimerRef.current) {
        window.clearTimeout(collabSendTimerRef.current);
        collabSendTimerRef.current = null;
      }
      collabRef.current?.dispose();
      collabRef.current = null;
      setCollabConnected(false);
    };
  }, [applyRemoteScreen, disableRealtime, screenId, tabSessionId]);

  useEffect(() => {
    if (!screen || !screenId || applyingRemoteRef.current) return;
    if (!collabRef.current) return;
    if (collabSendTimerRef.current) {
      window.clearTimeout(collabSendTimerRef.current);
    }
    collabSendTimerRef.current = window.setTimeout(() => {
      collabRef.current?.sendScreenUpdate(screen);
    }, 300);
  }, [screen, screenId]);

  const presenceRows =
    presenceConnected && serverEditors.length > 0
      ? serverEditors.map((editor) => {
          const you = editor.session_id === tabSessionId ? " (you)" : "";
          const tab = editor.tab_name ? ` · ${editor.tab_name}` : "";
          return `${editor.user_label}${you}${tab}`;
        })
      : activeEditors;
  const presenceCount =
    presenceConnected && serverEditors.length > 0 ? serverEditors.length : activeEditors.length;

  return (
    <Tabs
      value={activeTab}
      onValueChange={setActiveTab}
      className="w-full h-full flex flex-col"
      data-testid="editor-tabs"
    >
      {hasEditorConflict && (
        <div
          className="mx-6 mt-3 rounded-md border border-amber-700/70 bg-amber-900/30 px-3 py-2 text-xs text-amber-100"
          data-testid="screen-editor-lock-warning"
        >
          <div className="flex items-center justify-between gap-3">
            <span>
              Another editor session is active ({lockOwner || "unknown"}). Changes may conflict.
            </span>
            <button
              type="button"
              className="rounded border border-amber-500/60 px-2 py-1 text-[10px] uppercase tracking-[0.15em]"
              onClick={() => {
                if (!lockKey) return;
                window.localStorage.setItem(
                  lockKey,
                  JSON.stringify({ owner: tabSessionId, ts: Date.now() })
                );
                setHasEditorConflict(false);
                setLockOwner("");
              }}
            >
              Take Over
            </button>
          </div>
        </div>
      )}
      <TabsList className="mx-6 mt-4 bg-slate-800 border-b border-slate-700 rounded-none gap-1">
        <TabsTrigger value="visual" data-testid="tab-visual" className="data-[state=active]:!bg-sky-600 data-[state=active]:!text-white text-slate-400 hover:text-slate-200">
          Visual Editor
        </TabsTrigger>
        <TabsTrigger value="json" data-testid="tab-json" className="data-[state=active]:!bg-sky-600 data-[state=active]:!text-white text-slate-400 hover:text-slate-200">
          JSON
        </TabsTrigger>
        <TabsTrigger value="binding" data-testid="tab-binding" className="data-[state=active]:!bg-sky-600 data-[state=active]:!text-white text-slate-400 hover:text-slate-200">
          Binding
        </TabsTrigger>
        <TabsTrigger value="action" data-testid="tab-action" className="data-[state=active]:!bg-sky-600 data-[state=active]:!text-white text-slate-400 hover:text-slate-200">
          Action
        </TabsTrigger>
        <TabsTrigger value="preview" data-testid="tab-preview" className="data-[state=active]:!bg-sky-600 data-[state=active]:!text-white text-slate-400 hover:text-slate-200">
          Preview
        </TabsTrigger>
        <TabsTrigger value="diff" data-testid="tab-diff" className="data-[state=active]:!bg-sky-600 data-[state=active]:!text-white text-slate-400 hover:text-slate-200">
          Diff
        </TabsTrigger>
      </TabsList>
      {(presenceCount > 0 || collabConnected) && (
        <div
          className="mx-6 mt-2 flex items-center justify-between rounded border border-slate-700/70 bg-slate-900/50 px-3 py-2 text-[11px] text-slate-300"
          data-testid="screen-editor-presence"
        >
          <span>
            Active editors: {presenceCount}
            <span className={`ml-3 ${collabConnected ? "text-emerald-400" : "text-slate-500"}`}>
              {collabConnected ? "Live sync connected" : "Live sync disconnected"}
            </span>
          </span>
          <span className="truncate text-slate-400">
            {presenceRows.join(", ") || "No active peer sessions"}
          </span>
        </div>
      )}

      <div className="flex-1 overflow-hidden px-6 py-4">
        <TabsContent
          value="visual"
          className="h-full"
          data-testid="visual-editor-content"
        >
          <VisualEditor />
        </TabsContent>

        <TabsContent
          value="json"
          className="h-full"
          data-testid="json-editor-content"
        >
          <JsonEditor />
        </TabsContent>

        <TabsContent
          value="binding"
          className="h-full"
          data-testid="binding-editor-content"
        >
          <BindingTab />
        </TabsContent>

        <TabsContent
          value="action"
          className="h-full"
          data-testid="action-editor-content"
        >
          <ActionTab />
        </TabsContent>

        <TabsContent
          value="preview"
          className="h-full"
          data-testid="preview-content"
        >
          <PreviewTab />
        </TabsContent>

        <TabsContent
          value="diff"
          className="h-full"
          data-testid="diff-content"
        >
          <DiffTab />
        </TabsContent>
      </div>
    </Tabs>
  );
}
