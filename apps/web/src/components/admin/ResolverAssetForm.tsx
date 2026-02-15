"use client";

import type React from "react";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { fetchApi } from "../../lib/adminUtils";
import type {
  ResolverAssetResponse,
  ResolverSimulationRequest,
  ResolverSimulationResult,
} from "../../types/asset-registry";

const RULE_TYPE_LABELS: Record<string, string> = {
  alias_mapping: "Alias Mapping",
  pattern_rule: "Pattern Rule",
  transformation: "Transformation",
};

interface ResolverAssetFormProps {
  asset: ResolverAssetResponse;
}

export default function ResolverAssetForm({ asset, onSave }: ResolverAssetFormProps) {
  const [isSimulateDialogOpen, setIsSimulateDialogOpen] = useState(false);
  const [simulationResults, setSimulationResults] = useState<ResolverSimulationResult[]>([]);
  const [testEntityInput, setTestEntityInput] = useState("");

  // Provide default values if config is missing
  const config = asset.config ?? {
    name: asset.name,
    description: asset.description,
    rules: [],
    default_namespace: undefined,
    tags: {},
    version: asset.version,
  };

  const simulateMutation = useMutation({
    mutationFn: async (request: ResolverSimulationRequest) => {
      const response = await fetchApi<ResolverSimulationResult[]>(
        "/asset-registry/resolvers/simulate",
        {
          method: "POST",
          body: JSON.stringify(request),
        }
      );
      return response.data;
    },
    onSuccess: (data) => {
      setSimulationResults(data);
      setIsSimulateDialogOpen(true);
    },
  });

  const handleSimulateResolver = () => {
    const entities = testEntityInput.split('\n').filter(e => e.trim());
    const request: ResolverSimulationRequest = {
      config: config,
      test_entities: entities,
      simulation_options: {},
    };
    simulateMutation.mutate(request);
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div>Rules: {config.rules?.length ?? 0}</div>
            <div>Default Namespace: {config.default_namespace || "None"}</div>
            <div>Version: {config.version ?? asset.version}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs">Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            <div>ID: {asset.asset_id}</div>
            <div>Status: {asset.status}</div>
            <div>Created: {new Date(asset.created_at || "").toLocaleDateString()}</div>
            {asset.published_at && (
              <div>Published: {new Date(asset.published_at).toLocaleDateString()}</div>
            )}
          </CardContent>
        </Card>
      </div>

      {asset.description && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs">Description</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm ">
              {asset.description}
            </p>
          </CardContent>
        </Card>
      )}

      {config.rules && config.rules.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs">Rules</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {config.rules.map((rule, index) => (
              <div key={index} className="flex items-center justify-between rounded border  p-2 text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{rule.name}</span>
                  <Badge variant="outline" className="text-xs">
                    {RULE_TYPE_LABELS[rule.rule_type]}
                  </Badge>
                  {!rule.is_active && (
                    <Badge variant="secondary" className="text-xs">
                      Inactive
                    </Badge>
                  )}
                </div>
                <div className="">
                  Priority: {rule.priority}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs">Test Resolver</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1">
            <Label>Test Entities (one per line)</Label>
            <Textarea
              value={testEntityInput}
              onChange={(e) => setTestEntityInput(e.target.value)}
              placeholder="GT-01&#10;가스터빈1호기&#10;equipment-123"
              rows={4}
              className="text-sm"
            />
          </div>
          <Button
            onClick={handleSimulateResolver}
            disabled={!testEntityInput.trim() || simulateMutation.isPending}
          >
            {simulateMutation.isPending ? "Simulating..." : "Simulate Resolution"}
          </Button>
        </CardContent>
      </Card>

      <Dialog open={isSimulateDialogOpen} onOpenChange={setIsSimulateDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Resolver Simulation Results</DialogTitle>
            <DialogDescription>
              Testing {asset.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 max-h-[60vh] overflow-y-auto">
            {simulationResults.map((result, index) => (
              <Card key={index}>
                <CardContent className="pt-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="font-medium text-sm">{result.original_entity}</div>
                      <div className="text-xs ">
                        Confidence: {(result.confidence_score * 100).toFixed(1)}%
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="">→</span>
                      <span className="text-sm font-medium text-sky-400">{result.resolved_entity}</span>
                    </div>
                    {result.transformations_applied.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-xs ">Transformations:</div>
                        {result.transformations_applied.map((transform, i) => (
                          <div key={i} className="text-xs ">• {transform}</div>
                        ))}
                      </div>
                    )}
                    {result.matched_rules.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-xs ">Matched Rules:</div>
                        {result.matched_rules.map((rule, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            {rule}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
