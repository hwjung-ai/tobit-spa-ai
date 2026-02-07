"use client";

import type { ScreenSchemaV1 } from "./screen.schema";

export interface CollaborationPresence {
  session_id: string;
  user_id: string;
  user_label: string;
  updated_at: string;
}

export interface CRDTCollaborationOptions {
  screenId: string;
  userId: string;
  userLabel: string;
  tenantId: string;
  sessionId: string;
  onRemoteScreen?: (screen: ScreenSchemaV1, updatedAt?: string | null) => void;
  onPresence?: (presence: CollaborationPresence[]) => void;
  onConnectionChange?: (connected: boolean) => void;
  onError?: (error: Error) => void;
}

type WsMessage =
  | { type: "hello"; session_id: string; user_id: string; user_label: string }
  | { type: "screen_update"; session_id: string; screen: ScreenSchemaV1; updated_at?: string }
  | { type: "presence"; sessions: CollaborationPresence[] };

export class CRDTCollaboration {
  private ws: WebSocket | null = null;
  private disposed = false;
  private options: CRDTCollaborationOptions;
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 3;

  constructor(options: CRDTCollaborationOptions) {
    this.options = options;
    this.connect();
  }

  private resolveWsUrl(): string {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const rawBase = process.env.NEXT_PUBLIC_API_BASE_URL || "";
    if (rawBase) {
      const httpUrl = new URL(rawBase);
      const wsProtocol = httpUrl.protocol === "https:" ? "wss:" : "ws:";
      const endpoint = `${wsProtocol}//${httpUrl.host}/ops/ui-editor/collab/ws`;
      const params = new URLSearchParams({
        screen_id: this.options.screenId,
        tenant_id: this.options.tenantId,
        session_id: this.options.sessionId,
      });
      if (token) params.set("token", token);
      return `${endpoint}?${params.toString()}`;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const params = new URLSearchParams({
      screen_id: this.options.screenId,
      tenant_id: this.options.tenantId,
      session_id: this.options.sessionId,
    });
    if (token) params.set("token", token);
    return `${protocol}//localhost:8000/ops/ui-editor/collab/ws?${params.toString()}`;
  }

  private connect() {
    if (this.disposed) return;
    try {
      this.ws = new WebSocket(this.resolveWsUrl());
      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.options.onConnectionChange?.(true);
        this.send({
          type: "hello",
          session_id: this.options.sessionId,
          user_id: this.options.userId,
          user_label: this.options.userLabel,
        });
      };
      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(String(event.data)) as WsMessage;
          if (msg.type === "screen_update") {
            if (msg.session_id === this.options.sessionId) return;
            this.options.onRemoteScreen?.(msg.screen, msg.updated_at || null);
            return;
          }
          if (msg.type === "presence") {
            this.options.onPresence?.(msg.sessions || []);
          }
        } catch (err) {
          this.options.onError?.(err instanceof Error ? err : new Error(String(err)));
        }
      };
      this.ws.onerror = () => {
        this.options.onConnectionChange?.(false);
      };
      this.ws.onclose = () => {
        this.options.onConnectionChange?.(false);
        if (this.disposed) return;
        this.reconnectAttempts += 1;
        if (this.reconnectAttempts > this.maxReconnectAttempts) {
          return;
        }
        const waitMs = Math.min(10000, 1000 * 2 ** this.reconnectAttempts);
        this.reconnectTimer = window.setTimeout(() => this.connect(), waitMs);
      };
    } catch (err) {
      this.options.onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  }

  private send(payload: unknown) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify(payload));
  }

  sendScreenUpdate(screen: ScreenSchemaV1) {
    this.send({
      type: "screen_update",
      session_id: this.options.sessionId,
      screen,
      updated_at: new Date().toISOString(),
    });
  }

  isConnected(): boolean {
    return !!this.ws && this.ws.readyState === WebSocket.OPEN;
  }

  dispose() {
    this.disposed = true;
    if (this.reconnectTimer) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
