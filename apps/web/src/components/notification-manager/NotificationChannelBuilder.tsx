/**
 * NotificationChannelBuilder
 *
 * 다중 채널 알림 설정 폼 빌더
 * - Slack, Email, SMS, Webhook, PagerDuty 지원
 * - 각 채널별 설정 폼
 * - 테스트 발송 기능
 */

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import SlackChannelForm from "./SlackChannelForm";
import EmailChannelForm from "./EmailChannelForm";
import SmsChannelForm from "./SmsChannelForm";
import WebhookChannelForm from "./WebhookChannelForm";
import PagerDutyChannelForm from "./PagerDutyChannelForm";

export interface NotificationChannel {
  id: string;
  type: "slack" | "email" | "sms" | "webhook" | "pagerduty";
  enabled: boolean;
  config: Record<string, any>;
  name: string;
  lastTest?: Date;
}

interface NotificationChannelBuilderProps {
  channels?: NotificationChannel[];
  onChannelsChange?: (channels: NotificationChannel[]) => void;
  onTest?: (channelId: string) => Promise<boolean>;
}

export default function NotificationChannelBuilder({
  channels = [],
  onChannelsChange,
  onTest,
}: NotificationChannelBuilderProps) {
  const [activeTab, setActiveTab] = useState("slack");
  const [testingChannel, setTestingChannel] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});

  const channelTypes: Array<{
    id: string;
    label: string;
    description: string;
    icon: string;
  }> = [
    {
      id: "slack",
      label: "Slack",
      description: "Send alerts to Slack channels",
      icon: "📱",
    },
    {
      id: "email",
      label: "Email",
      description: "Send alerts via SMTP",
      icon: "📧",
    },
    {
      id: "sms",
      label: "SMS",
      description: "Send alerts via Twilio",
      icon: "📲",
    },
    {
      id: "webhook",
      label: "Webhook",
      description: "Send alerts to HTTP endpoints",
      icon: "🔗",
    },
    {
      id: "pagerduty",
      label: "PagerDuty",
      description: "Send incidents to PagerDuty",
      icon: "⚠️",
    },
  ];

  const handleChannelUpdate = (
    type: NotificationChannel["type"],
    config: Record<string, any>,
    name: string
  ) => {
    const channelId = `${type}-${Date.now()}`;
    const newChannel: NotificationChannel = {
      id: channelId,
      type,
      enabled: true,
      config,
      name: name || `${type.charAt(0).toUpperCase() + type.slice(1)}`,
    };

    const updated = [...channels, newChannel];
    onChannelsChange?.(updated);
  };

  const handleChannelRemove = (channelId: string) => {
    const updated = channels.filter((c) => c.id !== channelId);
    onChannelsChange?.(updated);
  };

  const handleChannelToggle = (channelId: string) => {
    const updated = channels.map((c) =>
      c.id === channelId ? { ...c, enabled: !c.enabled } : c
    );
    onChannelsChange?.(updated);
  };

  const handleTestChannel = async (channelId: string) => {
    setTestingChannel(channelId);
    try {
      if (onTest) {
        const success = await onTest(channelId);
        setTestResults((prev) => ({
          ...prev,
          [channelId]: {
            success,
            message: success
              ? "Test notification sent successfully!"
              : "Failed to send test notification",
          },
        }));
      }
    } catch (error) {
      setTestResults((prev) => ({
        ...prev,
        [channelId]: {
          success: false,
          message: `Error: ${error instanceof Error ? error.message : "Unknown error"}`,
        },
      }));
    } finally {
      setTestingChannel(null);
    }
  };

  const getChannelIcon = (type: string) => {
    const channel = channelTypes.find((c) => c.id === type);
    return channel?.icon || "🔔";
  };

  return (
    <div className="w-full space-y-6">
      {/* 활성화된 채널 목록 */}
      {channels.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Active Notification Channels</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {channels.map((channel) => (
                <div
                  key={channel.id}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{getChannelIcon(channel.type)}</span>
                    <div>
                      <p className="font-medium">{channel.name}</p>
                      <p className="text-sm text-slate-500">
                        {channelTypes.find((c) => c.id === channel.type)?.description}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {!channel.enabled && (
                      <Badge variant="secondary">Disabled</Badge>
                    )}
                    {testResults[channel.id] && (
                      <Badge
                        variant={testResults[channel.id].success ? "default" : "destructive"}
                      >
                        {testResults[channel.id].message.split("!")[0]}
                      </Badge>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleTestChannel(channel.id)}
                      disabled={testingChannel === channel.id || !channel.enabled}
                    >
                      {testingChannel === channel.id ? "Testing..." : "Test"}
                    </Button>
                    <Button
                      size="sm"
                      variant={channel.enabled ? "default" : "secondary"}
                      onClick={() => handleChannelToggle(channel.id)}
                    >
                      {channel.enabled ? "Enabled" : "Disabled"}
                    </Button>
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={() => handleChannelRemove(channel.id)}
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 채널 설정 탭 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Add New Channel</CardTitle>
          <CardDescription>
            Configure a new notification channel to receive alerts
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-5">
              {channelTypes.map((type) => (
                <TabsTrigger key={type.id} value={type.id}>
                  {type.icon} {type.label}
                </TabsTrigger>
              ))}
            </TabsList>

            <TabsContent value="slack" className="mt-6">
              <SlackChannelForm
                onSubmit={(config, name) =>
                  handleChannelUpdate("slack", config, name)
                }
              />
            </TabsContent>

            <TabsContent value="email" className="mt-6">
              <EmailChannelForm
                onSubmit={(config, name) =>
                  handleChannelUpdate("email", config, name)
                }
              />
            </TabsContent>

            <TabsContent value="sms" className="mt-6">
              <SmsChannelForm
                onSubmit={(config, name) =>
                  handleChannelUpdate("sms", config, name)
                }
              />
            </TabsContent>

            <TabsContent value="webhook" className="mt-6">
              <WebhookChannelForm
                onSubmit={(config, name) =>
                  handleChannelUpdate("webhook", config, name)
                }
              />
            </TabsContent>

            <TabsContent value="pagerduty" className="mt-6">
              <PagerDutyChannelForm
                onSubmit={(config, name) =>
                  handleChannelUpdate("pagerduty", config, name)
                }
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* 정보 팁 */}
      <Alert>
        <AlertDescription>
          💡 <strong>Tip:</strong> You can add multiple channels of the same type with different
          configurations. For example, multiple Slack channels for different teams.
        </AlertDescription>
      </Alert>
    </div>
  );
}
