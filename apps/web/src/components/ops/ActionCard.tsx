import React, { useState } from "react";
import { Button } from "../ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../ui/select";
import { Textarea } from "../ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { formatError } from "../../lib/utils";
import { useMutation } from "@tanstack/react-query";
import type { ReplanTrigger } from "../../types/ops-schemas";

interface ActionCardProps {
  trigger?: ReplanTrigger;
  stage?: string;
  onAction?: (action: string, params: unknown) => void;
}

const ACTION_TYPES = [
  { id: "rerun", label: "Re-run CI", description: "Restart the CI pipeline with the same parameters" },
  { id: "replan", label: "Re-plan", description: "Generate a new plan using updated parameters" },
  { id: "debug", label: "Debug", description: "Run diagnostics on the failed stage" },
  { id: "skip", label: "Skip Stage", description: "Skip the current stage and continue" },
  { id: "rollback", label: "Rollback", description: "Rollback to previous successful state" },
] as const;

type ActionType = typeof ACTION_TYPES[number]["id"];

interface ActionParams {
  ci_code?: string;
  timeout?: number;
  force_rerun?: boolean;
  debug_level?: "basic" | "detailed" | "full";
  skip_reason?: string;
  rollback_version?: string;
}

export default function ActionCard({ trigger, stage, onAction }: ActionCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedAction, setSelectedAction] = useState<ActionType | null>(null);
  const [actionParams, setActionParams] = useState<ActionParams>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const executeActionMutation = useMutation({
    mutationFn: async ({ action, params }: { action: ActionType; params: ActionParams }) => {
      const response = await fetch(`/api/ops/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action,
          trigger,
          stage,
          params,
        }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(body.message ?? "Action failed");
      }
      return body.data;
    },
    onSuccess: () => {
      setIsOpen(false);
      setSelectedAction(null);
      setActionParams({});
      onAction?.(selectedAction!, actionParams);
    },
  });

  const handleExecute = () => {
    if (!selectedAction) return;

    setIsSubmitting(true);
    executeActionMutation.mutate({ action: selectedAction, params: actionParams });
  };

  const renderActionForm = () => {
    if (!selectedAction) return null;

    switch (selectedAction) {
      case "rerun":
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>CI Code</Label>
              <Input
                value={actionParams.ci_code || ""}
                onChange={(e) => setActionParams({ ...actionParams, ci_code: e.target.value })}
                placeholder="Enter CI code to rerun"
              />
            </div>
            <div className="space-y-2">
              <Label>Force Re-run</Label>
              <Select
                value={actionParams.force_rerun ? "true" : "false"}
                onValueChange={(value) => setActionParams({ ...actionParams, force_rerun: value === "true" })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="false">Use cache if available</SelectItem>
                  <SelectItem value="true">Force fresh execution</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Timeout (seconds)</Label>
              <Input
                type="number"
                value={actionParams.timeout || 300}
                onChange={(e) => setActionParams({ ...actionParams, timeout: parseInt(e.target.value) })}
              />
            </div>
          </div>
        );

      case "replan":
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Re-plan Strategy</Label>
              <Select
                value={actionParams.debug_level || "basic"}
                onValueChange={(value) => setActionParams({ ...actionParams, debug_level: value as "basic" | "detailed" | "full" })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="basic">Basic (fast)</SelectItem>
                  <SelectItem value="detailed">Detailed (recommended)</SelectItem>
                  <SelectItem value="full">Full (comprehensive)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={actionParams.skip_reason || ""}
                onChange={(e) => setActionParams({ ...actionParams, skip_reason: e.target.value })}
                placeholder="Reason for re-planning"
                rows={3}
              />
            </div>
          </div>
        );

      case "debug":
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Debug Level</Label>
              <Select
                value={actionParams.debug_level || "basic"}
                onValueChange={(value) => setActionParams({ ...actionParams, debug_level: value as "basic" | "detailed" | "full" })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="basic">Basic logs</SelectItem>
                  <SelectItem value="detailed">Detailed with context</SelectItem>
                  <SelectItem value="full">Full with traces</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Focus Area</Label>
              <Select>
                <SelectTrigger>
                  <SelectValue placeholder="Select focus area" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="network">Network issues</SelectItem>
                  <SelectItem value="performance">Performance</SelectItem>
                  <SelectItem value="logic">Logic errors</SelectItem>
                  <SelectItem value="dependencies">Dependencies</SelectItem>
                  <SelectItem value="all">All areas</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        );

      case "skip":
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Reason for Skipping</Label>
              <Textarea
                value={actionParams.skip_reason || ""}
                onChange={(e) => setActionParams({ ...actionParams, skip_reason: e.target.value })}
                placeholder="Explain why this stage should be skipped"
                rows={3}
              />
            </div>
            <div className="text-xs text-yellow-400">
              Warning: Skipping may affect the final result quality
            </div>
          </div>
        );

      case "rollback":
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Rollback Version</Label>
              <Input
                value={actionParams.rollback_version || ""}
                onChange={(e) => setActionParams({ ...actionParams, rollback_version: e.target.value })}
                placeholder="Version to rollback to"
              />
            </div>
            <div className="text-xs text-yellow-400">
              This will revert all changes made after the specified version
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const selectedActionData = ACTION_TYPES.find(a => a.id === selectedAction);

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger>
        <Card className="cursor-pointer hover:border-sky-500 transition-colors">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm">Available Actions</CardTitle>
              <Badge variant="outline">
                {trigger ? `${trigger.trigger_type.toUpperCase()}` : "Manual"}
              </Badge>
            </div>
            {stage && (
              <CardDescription className="text-xs">
                Stage: {stage}
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            <p className="text-xs ">
              Click to see available recovery actions
            </p>
          </CardContent>
        </Card>
      </DialogTrigger>

      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Recovery Actions</DialogTitle>
          <DialogDescription>
            Select an appropriate action to handle the current situation
          </DialogDescription>
        </DialogHeader>

        {!selectedAction ? (
          <div className="space-y-4">
            <div className="text-sm ">
              {trigger ? (
                <p>
                  Triggered by: <strong>{trigger.trigger_type}</strong> at {trigger.stage_name}
                  <br />
                  Reason: {trigger.reason}
                </p>
              ) : (
                <p>Manual action selection</p>
              )}
            </div>

            <Tabs defaultValue="actions" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="actions">Actions</TabsTrigger>
                <TabsTrigger value="history">Recent Actions</TabsTrigger>
              </TabsList>

              <TabsContent value="actions" className="space-y-3">
                {ACTION_TYPES.map((action) => (
                  <div
                    key={action.id}
                    className="rounded-lg border  p-4 cursor-pointer hover: transition-colors"
                    onClick={() => setSelectedAction(action.id)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-medium text-sm">{action.label}</h3>
                      <Badge variant="secondary" className="text-xs">
                        {action.id}
                      </Badge>
                    </div>
                    <p className="text-xs ">{action.description}</p>
                    {selectedAction === action.id && (
                      <div className="mt-2 text-xs text-sky-400">
                        ✓ Selected
                      </div>
                    )}
                  </div>
                ))}
              </TabsContent>

              <TabsContent value="history" className="space-y-3">
                <div className="text-sm ">
                  Recently executed actions will appear here
                </div>
              </TabsContent>
            </Tabs>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">{selectedActionData?.label}</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedAction(null)}
              >
                Change
              </Button>
            </div>

            <div className="text-sm ">
              {selectedActionData?.description}
            </div>

            {renderActionForm()}

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setIsOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleExecute}
                disabled={isSubmitting || executeActionMutation.isPending}
              >
                {executeActionMutation.isPending ? "Executing..." : "Execute Action"}
              </Button>
            </div>

            {executeActionMutation.isError && (
              <div className="rounded-lg border border-rose-500/70 bg-rose-500/5 p-3 text-xs text-rose-200">
                Error: {formatError(executeActionMutation.error)}
              </div>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}