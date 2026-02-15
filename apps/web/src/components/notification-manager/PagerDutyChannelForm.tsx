/**
 * PagerDutyChannelForm
 *
 * PagerDuty 알림 채널 설정 폼
 * - Integration Key
 * - Severity Mapping
 */

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import FormFieldGroup from "../api-manager/FormFieldGroup";

interface PagerDutyChannelFormProps {
  onSubmit: (config: Record<string, unknown>, name: string) => void;
}

export default function PagerDutyChannelForm({ onSubmit }: PagerDutyChannelFormProps) {
  const [integrationKey, setIntegrationKey] = useState("");
  const [defaultSeverity, setDefaultSeverity] = useState("critical");
  const [channelName, setChannelName] = useState("PagerDuty");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    if (!channelName) newErrors.channelName = "Channel name is required";
    if (!integrationKey) newErrors.integrationKey = "Integration Key is required";
    if (integrationKey.length < 20) {
      newErrors.integrationKey = "Integration Key appears to be invalid";
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      onSubmit(
        {
          integration_key: integrationKey,
          default_severity: defaultSeverity,
        },
        channelName
      );
      setIntegrationKey("");
      setDefaultSeverity("critical");
      setChannelName("PagerDuty");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Alert>
        <AlertDescription>
          📌 <strong>PagerDuty Setup:</strong>
          <ol className="list-decimal list-inside mt-2 text-sm space-y-1">
            <li>Go to your PagerDuty dashboard</li>
            <li>Navigate to &quot;Services&quot; and select or create a service</li>
            <li>Go to &quot;Integrations&quot; tab</li>
            <li>Add a new &quot;Events API v2&quot; integration</li>
            <li>Copy the Integration Key below</li>
          </ol>
        </AlertDescription>
      </Alert>

      <FormFieldGroup
        label="Channel Name"
        error={errors.channelName}
        required
        help="A friendly name for this PagerDuty integration"
      >
        <Input
          value={channelName}
          onChange={(e) => setChannelName(e.target.value)}
          placeholder="e.g., PagerDuty Integration"
        />
      </FormFieldGroup>

      <FormFieldGroup
        label="Integration Key"
        error={errors.integrationKey}
        required
        help="The Integration Key from your PagerDuty Events API v2 integration"
      >
        <Input
          type="password"
          value={integrationKey}
          onChange={(e) => setIntegrationKey(e.target.value)}
          placeholder="6011d4c5xxxxxxxxxxxxxxxxxxxxxxxx"
        />
      </FormFieldGroup>

      <FormFieldGroup
        label="Default Severity"
        help="Default severity for incidents triggered by alerts"
      >
        <Select value={defaultSeverity} onValueChange={setDefaultSeverity}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="critical">🔴 Critical</SelectItem>
            <SelectItem value="error">🟠 Error</SelectItem>
            <SelectItem value="warning">🟡 Warning</SelectItem>
            <SelectItem value="info">🔵 Info</SelectItem>
          </SelectContent>
        </Select>
      </FormFieldGroup>

      <Alert className="bg-sky-50 border-sky-200">
        <AlertDescription className="text-sky-800 text-sm">
          💡 <strong>Note:</strong> Incidents will be created in PagerDuty with the severity you
          select above. You can also resolve incidents when alerts are acknowledged.
        </AlertDescription>
      </Alert>

      <div className="flex gap-2">
        <Button type="submit">Add PagerDuty Channel</Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            setIntegrationKey("");
            setDefaultSeverity("critical");
            setChannelName("PagerDuty");
            setErrors({});
          }}
        >
          Clear
        </Button>
      </div>
    </form>
  );
}
