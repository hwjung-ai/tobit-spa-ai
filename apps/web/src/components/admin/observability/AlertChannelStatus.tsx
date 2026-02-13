"use client";

import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/apiClient";

interface ChannelStatus {
  type: string;
  display_name: string;
  active: number;
  inactive: number;
  total_sent: number;
  total_failed: number;
  failure_rate: number;
  last_sent_at: string | null;
  recent_logs: Array<{
    log_id: string;
    fired_at: string;
    status: string;
    response_status: number | null;
  }>;
}

const channelIcons: Record<string, string> = {
  slack: "📱",
  email: "📧",
  sms: "📲",
  webhook: "🔗",
  pagerduty: "⚠️",
};

export default function AlertChannelStatus() {
  const [channels, setChannels] = useState<ChannelStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchChannels = async () => {
      try {
        setLoading(true);
        const response = await authenticatedFetch("/cep/channels/status");
        setChannels(response.data?.channels || []);
        setError(null);
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Failed to fetch channels";
        setError(errorMsg);
      } finally {
        setLoading(false);
      }
    };

    fetchChannels();
    // Refresh every 30 seconds
    const interval = setInterval(fetchChannels, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (failureRate: number) => {
    if (failureRate === 0) return "bg-emerald-500/20 text-emerald-400 border-emerald-500/50";
    if (failureRate < 0.1) return "bg-amber-500/20 text-amber-400 border-amber-500/50";
    return "bg-rose-500/20 text-rose-400 border-rose-500/50";
  };

  if (loading) {
    return (
      <div className="rounded-2xl border border-variant bg-surface-overlay p-6 text-sm text-muted-foreground">
        Loading channel status...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-rose-800/70 bg-rose-900/60 p-6 text-rose-400 text-sm">
        Error: {error}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-variant bg-surface-overlay p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-foreground dark:text-foreground">Alert Channels</h3>
        <span className="text-sm uppercase tracking-wider text-muted-foreground">Last 24h</span>
      </div>

      <div className="space-y-4">
        {channels.length === 0 ? (
          <p className="text-sm text-muted-foreground">No channels configured</p>
        ) : (
          channels.map((channel) => (
            <div
              key={channel.type}
              className="p-4 rounded-lg border border-variant bg-surface-base transition"
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{channelIcons[channel.type] || "📬"}</span>
                  <div>
                    <h4 className="text-foreground dark:text-foreground font-semibold">{channel.display_name}</h4>
                    <p className="text-xs text-muted-foreground">
                      {channel.active} active • {channel.inactive} inactive
                    </p>
                  </div>
                </div>
                <div
                  className={`px-3 py-1 rounded-full text-xs font-semibold border ${getStatusColor(
                    channel.failure_rate
                  )}`}
                >
                  {channel.failure_rate === 0
                    ? "Healthy"
                    : channel.failure_rate < 0.1
                    ? "Degraded"
                    : "Failing"}
                </div>
              </div>

              {/* Stats */}
              <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Total Sent</p>
                  <p className="text-foreground dark:text-foreground font-semibold">{channel.total_sent}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Failed</p>
                  <p className={channel.total_failed > 0 ? "text-rose-400 font-semibold" : "text-muted-foreground"}>
                    {channel.total_failed}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Failure Rate</p>
                  <p className="text-foreground dark:text-foreground font-semibold">
                    {(channel.failure_rate * 100).toFixed(1)}%
                  </p>
                </div>
              </div>

              {/* Progress bar */}
              <div className="mb-4">
                <div className="h-2 rounded-full bg-surface-elevated overflow-hidden">
                  <div
                    className={`h-full ${
                      channel.failure_rate === 0
                        ? "bg-emerald-500"
                        : channel.failure_rate < 0.1
                        ? "bg-amber-500"
                        : "bg-rose-500"
                    }`}
                    style={{width: `${Math.min(channel.failure_rate * 100, 100)}%`}}
                  />
                </div>
              </div>

              {/* Last sent */}
              <div className="text-xs text-muted-foreground">
                Last sent:{" "}
                <span className="text-foreground">
                  {channel.last_sent_at
                    ? new Date(channel.last_sent_at).toLocaleTimeString()
                    : "Never"}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
