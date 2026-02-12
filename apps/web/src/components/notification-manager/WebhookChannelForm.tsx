/**
 * WebhookChannelForm
 *
 * Webhook 알림 채널 설정 폼
 * - URL
 * - 커스텀 헤더
 * - HTTP 메서드
 */

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import FormFieldGroup from "../api-manager/FormFieldGroup";

interface WebhookChannelFormProps {
  onSubmit: (config: Record<string, any>, name: string) => void;
}

export default function WebhookChannelForm({ onSubmit }: WebhookChannelFormProps) {
  const [url, setUrl] = useState("");
  const [method, setMethod] = useState("POST");
  const [headersJson, setHeadersJson] = useState("{}");
  const [channelName, setChannelName] = useState("Webhook");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    if (!channelName) newErrors.channelName = "Channel name is required";
    if (!url) newErrors.url = "URL is required";
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      newErrors.url = "URL must start with http:// or https://";
    }

    let headers = {};
    try {
      headers = headersJson ? JSON.parse(headersJson) : {};
    } catch {
      newErrors.headersJson = "Invalid JSON format for headers";
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      onSubmit(
        {
          url: url,
          headers: headers,
          method: method,
        },
        channelName
      );
      setUrl("");
      setMethod("POST");
      setHeadersJson("{}");
      setChannelName("Webhook");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Alert>
        <AlertDescription>
          📌 <strong>Webhook Format:</strong>
          <div className="mt-2 text-sm space-y-1">
            <p>Each alert will send a POST request with this payload:</p>
            <pre className=" p-2 rounded mt-2 text-xs overflow-auto" style={{ backgroundColor: "var(--surface-base)" }}>
{`{
  "title": "Alert Name",
  "body": "Alert Description",
  "severity": "critical",
  "fired_at": "2024-01-01T12:00:00Z"
}`}
            </pre>
          </div>
        </AlertDescription>
      </Alert>

      <FormFieldGroup
        label="Channel Name"
        error={errors.channelName}
        required
        help="A friendly name for this webhook"
      >
        <Input
          value={channelName}
          onChange={(e) => setChannelName(e.target.value)}
          placeholder="e.g., Custom Webhook"
        />
      </FormFieldGroup>

      <FormFieldGroup
        label="Webhook URL"
        error={errors.url}
        required
        help="The HTTP endpoint to receive alerts"
      >
        <Input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://api.example.com/webhooks/alerts"
        />
      </FormFieldGroup>

      <div className="grid grid-cols-2 gap-4">
        <FormFieldGroup
          label="HTTP Method"
          help="Method to use for webhook calls"
        >
          <Select value={method} onValueChange={setMethod}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="POST">POST</SelectItem>
              <SelectItem value="PUT">PUT</SelectItem>
              <SelectItem value="PATCH">PATCH</SelectItem>
            </SelectContent>
          </Select>
        </FormFieldGroup>
      </div>

      <FormFieldGroup
        label="Custom Headers (JSON)"
        error={errors.headersJson}
        help="Optional custom headers to include in the request"
      >
        <Textarea
          value={headersJson}
          onChange={(e) => setHeadersJson(e.target.value)}
          placeholder={`{
  "Authorization": "Bearer token...",
  "X-Custom-Header": "value"
}`}
          className="font-mono text-sm"
          rows={5}
        />
      </FormFieldGroup>

      <div className="flex gap-2">
        <Button type="submit">Add Webhook Channel</Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            setUrl("");
            setMethod("POST");
            setHeadersJson("{}");
            setChannelName("Webhook");
            setErrors({});
          }}
        >
          Clear
        </Button>
      </div>
    </form>
  );
}
