/**
 * SSE Stream Binding for UI Screen Renderer
 * Manages EventSource connections for real-time data updates
 * Features:
 *   - Auto-reconnect with exponential backoff
 *   - Connection state tracking
 *   - Multiple concurrent streams per screen
 *   - State patch application on message
 *   - Backpressure: drops messages if handler is still processing
 */

export type StreamStatus = "disconnected" | "connecting" | "connected" | "error";

export interface StreamConfig {
  /** Unique stream identifier */
  id: string;
  /** SSE endpoint URL (relative or absolute) */
  url: string;
  /** State path to write incoming data to (e.g. "metrics.cpu") */
  targetPath: string;
  /** Optional: apply state_patch from message payload */
  applyPatch?: boolean;
  /** Transform incoming event data before applying to state */
  transform?: (data: unknown) => unknown;
  /** SSE event name to listen for (default: "message") */
  eventName?: string;
  /** Max reconnect attempts (default: 10) */
  maxReconnects?: number;
  /** Initial reconnect delay in ms (default: 1000) */
  reconnectDelayMs?: number;
  /** Max reconnect delay in ms (default: 30000) */
  maxReconnectDelayMs?: number;
}

export interface StreamState {
  status: StreamStatus;
  reconnectCount: number;
  lastMessageAt: number | null;
  lastError: string | null;
}

type StateUpdater = (path: string, value: unknown) => void;
type StatusChangeCallback = (streamId: string, state: StreamState) => void;

const DEFAULT_MAX_RECONNECTS = 10;
const DEFAULT_RECONNECT_DELAY_MS = 1000;
const DEFAULT_MAX_RECONNECT_DELAY_MS = 30000;

export class StreamManager {
  private streams = new Map<string, {
    config: StreamConfig;
    eventSource: EventSource | null;
    state: StreamState;
    reconnectTimer: ReturnType<typeof setTimeout> | null;
    processing: boolean;
  }>();

  private onStateUpdate: StateUpdater;
  private onStatusChange: StatusChangeCallback | null;
  private disposed = false;

  constructor(onStateUpdate: StateUpdater, onStatusChange?: StatusChangeCallback) {
    this.onStateUpdate = onStateUpdate;
    this.onStatusChange = onStatusChange ?? null;
  }

  subscribe(config: StreamConfig): void {
    if (this.disposed) return;

    // Close existing stream with same id
    if (this.streams.has(config.id)) {
      this.unsubscribe(config.id);
    }

    const entry = {
      config,
      eventSource: null as EventSource | null,
      state: {
        status: "disconnected" as StreamStatus,
        reconnectCount: 0,
        lastMessageAt: null as number | null,
        lastError: null as string | null,
      },
      reconnectTimer: null as ReturnType<typeof setTimeout> | null,
      processing: false,
    };

    this.streams.set(config.id, entry);
    this.connect(config.id);
  }

  unsubscribe(streamId: string): void {
    const entry = this.streams.get(streamId);
    if (!entry) return;

    if (entry.reconnectTimer) {
      clearTimeout(entry.reconnectTimer);
    }
    if (entry.eventSource) {
      entry.eventSource.close();
    }
    entry.state.status = "disconnected";
    this.notifyStatusChange(streamId, entry.state);
    this.streams.delete(streamId);
  }

  unsubscribeAll(): void {
    for (const id of Array.from(this.streams.keys())) {
      this.unsubscribe(id);
    }
  }

  dispose(): void {
    this.disposed = true;
    this.unsubscribeAll();
  }

  getStreamState(streamId: string): StreamState | null {
    return this.streams.get(streamId)?.state ?? null;
  }

  getAllStreamStates(): Record<string, StreamState> {
    const result: Record<string, StreamState> = {};
    this.streams.forEach((entry, id) => {
      result[id] = { ...entry.state };
    });
    return result;
  }

  private connect(streamId: string): void {
    const entry = this.streams.get(streamId);
    if (!entry || this.disposed) return;

    const { config } = entry;

    // Build URL with SSE proxy if relative
    let url = config.url;
    if (url.startsWith("/")) {
      // Route through SSE proxy to avoid CORS/firewall issues
      const token = typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;
      const proxyUrl = `/sse-proxy${url}`;
      const params = new URLSearchParams();
      if (token) params.set("token", token);
      url = params.toString() ? `${proxyUrl}?${params.toString()}` : proxyUrl;
    }

    entry.state.status = "connecting";
    this.notifyStatusChange(streamId, entry.state);

    try {
      const es = new EventSource(url);
      entry.eventSource = es;

      es.onopen = () => {
        if (this.disposed) return;
        entry.state.status = "connected";
        entry.state.reconnectCount = 0;
        entry.state.lastError = null;
        this.notifyStatusChange(streamId, entry.state);
      };

      const eventName = config.eventName || "message";
      const handler = (event: MessageEvent) => {
        if (this.disposed) return;

        // Backpressure: skip if still processing previous message
        if (entry.processing) return;

        entry.processing = true;
        try {
          entry.state.lastMessageAt = Date.now();
          const data = JSON.parse(event.data);

          // Apply transform if provided
          const transformed = config.transform ? config.transform(data) : data;

          // Write to target state path
          this.onStateUpdate(config.targetPath, transformed);

          // Apply state_patch if enabled and present
          if (config.applyPatch && data && typeof data === "object" && data.state_patch) {
            const patch = data.state_patch as Record<string, unknown>;
            for (const [key, value] of Object.entries(patch)) {
              this.onStateUpdate(key, value);
            }
          }
        } catch {
          // Ignore parse errors silently
        } finally {
          entry.processing = false;
        }
      };

      if (eventName === "message") {
        es.onmessage = handler;
      } else {
        es.addEventListener(eventName, handler as EventListener);
      }

      es.onerror = () => {
        if (this.disposed) return;
        entry.state.status = "error";
        entry.state.lastError = "Connection lost";
        this.notifyStatusChange(streamId, entry.state);

        // Close current connection
        es.close();
        entry.eventSource = null;

        // Attempt reconnect
        this.scheduleReconnect(streamId);
      };
    } catch (err) {
      entry.state.status = "error";
      entry.state.lastError = err instanceof Error ? err.message : "Connection failed";
      this.notifyStatusChange(streamId, entry.state);
      this.scheduleReconnect(streamId);
    }
  }

  private scheduleReconnect(streamId: string): void {
    const entry = this.streams.get(streamId);
    if (!entry || this.disposed) return;

    const maxReconnects = entry.config.maxReconnects ?? DEFAULT_MAX_RECONNECTS;
    if (entry.state.reconnectCount >= maxReconnects) {
      entry.state.status = "error";
      entry.state.lastError = `Max reconnects (${maxReconnects}) exceeded`;
      this.notifyStatusChange(streamId, entry.state);
      return;
    }

    const baseDelay = entry.config.reconnectDelayMs ?? DEFAULT_RECONNECT_DELAY_MS;
    const maxDelay = entry.config.maxReconnectDelayMs ?? DEFAULT_MAX_RECONNECT_DELAY_MS;
    // Exponential backoff with jitter
    const delay = Math.min(
      baseDelay * Math.pow(2, entry.state.reconnectCount) + Math.random() * 500,
      maxDelay
    );

    entry.state.reconnectCount++;

    entry.reconnectTimer = setTimeout(() => {
      if (!this.disposed && this.streams.has(streamId)) {
        this.connect(streamId);
      }
    }, delay);
  }

  private notifyStatusChange(streamId: string, state: StreamState): void {
    if (this.onStatusChange) {
      this.onStatusChange(streamId, { ...state });
    }
  }
}

/**
 * Parse stream bindings from screen schema.
 * Looks for components with `stream` property in their props:
 *
 *   {
 *     id: "comp_metrics",
 *     type: "chart",
 *     props: {
 *       stream: {
 *         url: "/api/metrics/stream?device_id={{inputs.device_id}}",
 *         target: "metrics.cpu",
 *         event: "metric_update"
 *       }
 *     }
 *   }
 */
export function extractStreamConfigs(
  components: Array<{ id: string; props?: Record<string, unknown> }>,
  resolveTemplate?: (template: string) => string
): StreamConfig[] {
  const configs: StreamConfig[] = [];

  for (const comp of components) {
    const streamProp = comp.props?.stream;
    if (streamProp && typeof streamProp === "object") {
      const s = streamProp as Record<string, unknown>;
      let url = String(s.url || "");

      // Resolve template expressions in URL if resolver provided
      if (resolveTemplate && url.includes("{{")) {
        url = resolveTemplate(url);
      }

      if (url) {
        configs.push({
          id: `stream_${comp.id}`,
          url,
          targetPath: String(s.target || `stream_${comp.id}`),
          applyPatch: Boolean(s.apply_patch),
          eventName: s.event ? String(s.event) : undefined,
          maxReconnects: typeof s.max_reconnects === "number" ? s.max_reconnects : undefined,
          reconnectDelayMs: typeof s.reconnect_delay_ms === "number" ? s.reconnect_delay_ms : undefined,
        });
      }
    }
  }

  return configs;
}
