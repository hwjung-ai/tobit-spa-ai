/**
 * SlackChannelForm
 *
 * Slack 알림 채널 설정 폼
 * - Webhook URL 입력
 * - 채널명 설정
 */

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import FormFieldGroup from "../api-manager/FormFieldGroup";

interface SlackChannelFormProps {
  onSubmit: (config: Record<string, any>, name: string) => void;
}

export default function SlackChannelForm({ onSubmit }: SlackChannelFormProps) {
  const [webhookUrl, setWebhookUrl] = useState("");
  const [channelName, setChannelName] = useState("Slack");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    if (!webhookUrl) {
      newErrors.webhookUrl = "Webhook URL is required";
    } else if (
      !webhookUrl.startsWith("https://hooks.slack.com/")
    ) {
      newErrors.webhookUrl =
        "Invalid Slack webhook URL. Must start with https://hooks.slack.com/";
    }

    if (!channelName) {
      newErrors.channelName = "Channel name is required";
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      onSubmit(
        {
          webhook_url: webhookUrl,
        },
        channelName
      );
      setWebhookUrl("");
      setChannelName("Slack");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Alert>
        <AlertDescription>
          📌 <strong>Setup Instructions:</strong>
          <ol className="list-decimal list-inside mt-2 text-sm space-y-1">
            <li>Go to your Slack workspace settings</li>
            <li>Navigate to "Integrations" → "Apps"</li>
            <li>Search for "Incoming Webhooks" and install</li>
            <li>Create a new webhook and copy the URL below</li>
          </ol>
        </AlertDescription>
      </Alert>

      <FormFieldGroup
        label="Channel Name"
        error={errors.channelName}
        required
        help="A friendly name for this Slack integration"
      >
        <Input
          value={channelName}
          onChange={(e) => setChannelName(e.target.value)}
          placeholder="e.g., Engineering Alerts, DevOps Slack"
        />
      </FormFieldGroup>

      <FormFieldGroup
        label="Webhook URL"
        error={errors.webhookUrl}
        required
        help="The incoming webhook URL from Slack"
      >
        <Input
          type="password"
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
          placeholder="https://hooks.slack.com/services/..."
        />
      </FormFieldGroup>

      <div className="flex gap-2">
        <Button type="submit">Add Slack Channel</Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            setWebhookUrl("");
            setChannelName("Slack");
            setErrors({});
          }}
        >
          Clear
        </Button>
      </div>
    </form>
  );
}
