/**
 * SmsChannelForm
 *
 * SMS 알림 채널 설정 폼 (Twilio)
 * - Account SID
 * - Auth Token
 * - From Number
 */

import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import FormFieldGroup from "../api-manager/FormFieldGroup";

interface SmsChannelFormProps {
  onSubmit: (config: Record<string, any>, name: string) => void;
}

export default function SmsChannelForm({ onSubmit }: SmsChannelFormProps) {
  const [accountSid, setAccountSid] = useState("");
  const [authToken, setAuthToken] = useState("");
  const [fromNumber, setFromNumber] = useState("");
  const [channelName, setChannelName] = useState("SMS");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    if (!channelName) newErrors.channelName = "Channel name is required";
    if (!accountSid) newErrors.accountSid = "Account SID is required";
    if (!authToken) newErrors.authToken = "Auth Token is required";
    if (!fromNumber) newErrors.fromNumber = "From number is required";
    if (!/^\+?1?\d{10,}$/.test(fromNumber.replace(/\D/g, ""))) {
      newErrors.fromNumber = "Invalid phone number format";
    }

    setErrors(newErrors);

    if (Object.keys(newErrors).length === 0) {
      onSubmit(
        {
          account_sid: accountSid,
          auth_token: authToken,
          from_number: fromNumber,
        },
        channelName
      );
      setAccountSid("");
      setAuthToken("");
      setFromNumber("");
      setChannelName("SMS");
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <Alert>
        <AlertDescription>
          📌 <strong>Twilio Setup:</strong>
          <ol className="list-decimal list-inside mt-2 text-sm space-y-1">
            <li>Create a Twilio account at twilio.com</li>
            <li>Verify your phone number</li>
            <li>Purchase a Twilio phone number</li>
            <li>Copy Account SID and Auth Token from your dashboard</li>
          </ol>
        </AlertDescription>
      </Alert>

      <FormFieldGroup
        label="Channel Name"
        error={errors.channelName}
        required
        help="A friendly name for this SMS integration"
      >
        <Input
          value={channelName}
          onChange={(e) => setChannelName(e.target.value)}
          placeholder="e.g., SMS Alerts"
        />
      </FormFieldGroup>

      <FormFieldGroup
        label="Account SID"
        error={errors.accountSid}
        required
        help="Your Twilio Account SID"
      >
        <Input
          type="password"
          value={accountSid}
          onChange={(e) => setAccountSid(e.target.value)}
          placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        />
      </FormFieldGroup>

      <FormFieldGroup
        label="Auth Token"
        error={errors.authToken}
        required
        help="Your Twilio Auth Token"
      >
        <Input
          type="password"
          value={authToken}
          onChange={(e) => setAuthToken(e.target.value)}
          placeholder="••••••••••••••••••••••••••••••••"
        />
      </FormFieldGroup>

      <FormFieldGroup
        label="From Number"
        error={errors.fromNumber}
        required
        help="Your Twilio phone number (e.g., +12025551234)"
      >
        <Input
          value={fromNumber}
          onChange={(e) => setFromNumber(e.target.value)}
          placeholder="+12025551234"
        />
      </FormFieldGroup>

      <div className="flex gap-2">
        <Button type="submit">Add SMS Channel</Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            setAccountSid("");
            setAuthToken("");
            setFromNumber("");
            setChannelName("SMS");
            setErrors({});
          }}
        >
          Clear
        </Button>
      </div>
    </form>
  );
}
