/**
 * EmailChannelForm
 *
 * Email 알림 채널 설정 폼
 * - SMTP 서버 설정
 * - 인증 정보
 */

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import FormFieldGroup from "../api-manager/FormFieldGroup";

interface EmailChannelFormProps {
  onSubmit: (config: Record<string, any>, name: string) => void;
}

export default function EmailChannelForm({ onSubmit }: EmailChannelFormProps) {
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("587");
  const [fromEmail, setFromEmail] = useState("");
  const [password, setPassword] = useState("");
  const [useTls, setUseTls] = useState(true);
  const [channelName, setChannelName] = useState("Email");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    if (!channelName) newErrors.channelName = "Channel name is required";
    if (!smtpHost) newErrors.smtpHost = "SMTP host is required";
    if (!smtpPort) newErrors.smtpPort = "SMTP port is required";
    if (isNaN(Number(smtpPort)) || Number(smtpPort) < 1 || Number(smtpPort) > 65535) {
      newErrors.smtpPort = "Port must be between 1 and 65535";
    }
    if (!fromEmail) newErrors.fromEmail = "From email is required";
    if (!fromEmail.includes("@")) newErrors.fromEmail = "Invalid email format";
    if (!password) newErrors.password = "Password is required";

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      onSubmit(
        {
          smtp_host: smtpHost,
          smtp_port: Number(smtpPort),
          from_email: fromEmail,
          password: password,
          use_tls: useTls,
        },
        channelName
      );
      setSmtpHost("");
      setSmtpPort("587");
      setFromEmail("");
      setPassword("");
      setUseTls(true);
      setChannelName("Email");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Alert>
        <AlertDescription>
          📌 <strong>Common SMTP Servers:</strong>
          <ul className="list-disc list-inside mt-2 text-sm space-y-1">
            <li>Gmail: smtp.gmail.com:587 (use app-specific password)</li>
            <li>Office 365: smtp.office365.com:587</li>
            <li>SendGrid: smtp.sendgrid.net:587</li>
          </ul>
        </AlertDescription>
      </Alert>

      <FormFieldGroup
        label="Channel Name"
        error={errors.channelName}
        required
        help="A friendly name for this email integration"
      >
        <Input
          value={channelName}
          onChange={(e) => setChannelName(e.target.value)}
          placeholder="e.g., Email Alerts"
        />
      </FormFieldGroup>

      <FormFieldGroup
        label="SMTP Host"
        error={errors.smtpHost}
        required
        help="SMTP server hostname"
      >
        <Input
          value={smtpHost}
          onChange={(e) => setSmtpHost(e.target.value)}
          placeholder="smtp.gmail.com"
        />
      </FormFieldGroup>

      <div className="grid grid-cols-2 gap-4">
        <FormFieldGroup
          label="SMTP Port"
          error={errors.smtpPort}
          required
          help="Usually 587 (TLS) or 465 (SSL)"
        >
          <Input
            type="number"
            value={smtpPort}
            onChange={(e) => setSmtpPort(e.target.value)}
            placeholder="587"
            min="1"
            max="65535"
          />
        </FormFieldGroup>

        <div className="flex items-end">
          <div className="flex items-center space-x-2 w-full">
            <Checkbox
              id="tls"
              checked={useTls}
              onCheckedChange={(checked) => setUseTls(checked === true)}
            />
            <Label htmlFor="tls" className="cursor-pointer">
              Use TLS
            </Label>
          </div>
        </div>
      </div>

      <FormFieldGroup
        label="From Email"
        error={errors.fromEmail}
        required
        help="Email address that sends notifications"
      >
        <Input
          type="email"
          value={fromEmail}
          onChange={(e) => setFromEmail(e.target.value)}
          placeholder="alerts@company.com"
        />
      </FormFieldGroup>

      <FormFieldGroup
        label="Password"
        error={errors.password}
        required
        help="SMTP password or app-specific password"
      >
        <Input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
        />
      </FormFieldGroup>

      <div className="flex gap-2">
        <Button type="submit">Add Email Channel</Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            setSmtpHost("");
            setSmtpPort("587");
            setFromEmail("");
            setPassword("");
            setUseTls(true);
            setChannelName("Email");
            setErrors({});
          }}
        >
          Clear
        </Button>
      </div>
    </form>
  );
}
