"use client";

import type React from "react";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../components/ui/dialog";
import { Label } from "../../components/ui/label";
import { Textarea } from "../../components/ui/textarea";
import { fetchApi } from "../../lib/adminUtils";
import type { ResolverAssetResponse, ResolverSimulationResult } from "../../types/asset-registry";

interface ResolverAssetFormProps {
  asset: ResolverAssetResponse;
}

export default function ResolverAssetForm({ asset }: ResolverAssetFormProps) {
  const [isSimulateDialogOpen, setIsSimulateDialogOpen] = useState(false);
  const [simulationResults, setSimulationResults] = useState<ResolverSimulationResult[]>([]);
  const [testEntityInput, setTestEntityInput] = useState("");
  const [error, setError] = useState<string | null>(null);

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
    mutationFn: async (testEntities: string[]) => {
      const response = await fetchApi<ResolverSimulationResult[]>(
        `/asset-registry/resolvers/${asset.asset_id}/simulate`,
        {
          method: "POST",
          body: JSON.stringify(testEntities),
        }
      );
      return response.data;
    },
    onSuccess: (data) => {
      setSimulationResults(data);
      setIsSimulateDialogOpen(true);
      setError(null);
    },
    onError: (err: Error) => {
      setError(err.message || "Simulation failed");
    },
  });

  const handleSimulateResolver = () => {
    const entities = testEntityInput.split('\n').map(e => e.trim()).filter(e => e);
    if (entities.length === 0) return;
    simulateMutation.mutate(entities);
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs">Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm text-muted-foreground">
            <div>Rules: <span className="text-foreground">{config.rules?.length ?? 0}</span></div>
            <div>Default Namespace: <span className="text-foreground">{config.default_namespace || "None"}</span></div>
            <div>Version: <span className="text-foreground">{config.version ?? asset.version}</span></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs">Metadata</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm text-muted-foreground">
            <div>ID: <span className="font-mono text-foreground">{asset.asset_id}</span></div>
            <div>Status: <span className="text-foreground">{asset.status}</span></div>
            <div>Created: <span className="text-foreground">{new Date(asset.created_at || "").toLocaleDateString()}</span></div>
            {asset.published_at && (
              <div>Published: <span className="text-foreground">{new Date(asset.published_at).toLocaleDateString()}</span></div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs">Config (JSON)</CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="text-xs bg-surface-elevated p-3 rounded overflow-auto max-h-80 font-mono text-muted-foreground border border-border">
            {JSON.stringify(config, null, 2)}
          </pre>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs">Test Resolver</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-xs text-muted-foreground">
            규칙에 정의된 매핑이 어떻게 변환되는지 테스트합니다. 예: "디비" → "DB"
          </p>
          <div className="space-y-1">
            <Label htmlFor="test-entities">테스트할 엔티티 (한 줄에 하나씩)</Label>
            <Textarea
              id="test-entities"
              value={testEntityInput}
              onChange={(e) => setTestEntityInput(e.target.value)}
              placeholder="디비&#10;와스&#10;CI"
              rows={4}
              className="text-sm font-mono"
            />
          </div>
          {error && (
            <p className="text-xs text-error">{error}</p>
          )}
          <Button
            variant="default"
            onClick={handleSimulateResolver}
            disabled={!testEntityInput.trim() || simulateMutation.isPending}
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            {simulateMutation.isPending ? "실행 중..." : "변환 테스트"}
          </Button>
        </CardContent>
      </Card>

      <Dialog open={isSimulateDialogOpen} onOpenChange={setIsSimulateDialogOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>변환 결과</DialogTitle>
            <DialogDescription>
              {asset.name} 규칙 적용 결과
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3 max-h-[60vh] overflow-y-auto">
            {simulationResults.map((result, index) => (
              <Card key={index}>
                <CardContent className="pt-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="font-mono text-sm">{result.original_entity}</div>
                      <div className="text-xs text-muted-foreground">
                        신뢰도: {(result.confidence_score * 100).toFixed(0)}%
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">→</span>
                      <span className="text-sm font-medium font-mono text-sky-400">{result.resolved_entity}</span>
                    </div>
                    {result.matched_rules.length > 0 && (
                      <div className="text-xs text-muted-foreground">
                        적용된 규칙: {result.matched_rules.join(", ")}
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
