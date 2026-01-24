import { useState, useEffect } from "react";
import { fetchApi } from "@/lib/apiClient/index";
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";

import { Trash2, Settings, Play, CheckCircle, AlertCircle } from "lucide-react";
import { type AssetSummary } from "@/lib/apiClient/index";

interface AssetOverride {
  assetType: string;
  assetId: string;
  name: string;
  version?: number;
}

interface AssetOverrideDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const ASSET_TYPES = [
  { value: "prompt", label: "Prompt", color: "bg-blue-500" },
  { value: "policy", label: "Policy", color: "bg-purple-500" },
  { value: "query", label: "Query", color: "bg-green-500" },
  { value: "mapping", label: "Mapping", color: "bg-orange-500" },
  { value: "screen", label: "Screen", color: "bg-pink-500" },
];

const DEFAULT_ASSETS = {
  prompt: "ci:planner",
  policy: "plan_budget",
  query: "ci:lookup",
  mapping: "graph_relation",
  screen: "default",
};

export default function AssetOverrideDrawer({
  open,
  onOpenChange,
}: AssetOverrideDrawerProps) {
  const [overrides, setOverrides] = useState<AssetOverride[]>([]);
  const [availableAssets, setAvailableAssets] = useState<Record<string, AssetSummary[]>>({});
  const [loading, setLoading] = useState(false);
  const [testMode, setTestMode] = useState(false);
  const [baselineTraceId, setBaselineTraceId] = useState("");
  const [selectedQuestion, setSelectedQuestion] = useState("");

  // Load available assets for each type
  useEffect(() => {
    if (open) {
      loadAvailableAssets();
    }
  }, [open]);

  const loadAvailableAssets = async () => {
    setLoading(true);
    try {
      const assetsByType: Record<string, AssetSummary[]> = {};

      for (const assetType of ASSET_TYPES.map((a) => a.value)) {
        const response = await fetchApi(`/api/assets/registry?type=${assetType}`);
        if (response.ok) {
          const data = await response.json();
          assetsByType[assetType] = data.data || [];
        }
      }

      setAvailableAssets(assetsByType);

      // Initialize with default overrides
      const initialOverrides = ASSET_TYPES.map((type) => ({
        assetType: type.value,
        assetId: DEFAULT_ASSETS[type.value as keyof typeof DEFAULT_ASSETS],
        name: `${type.label}: ${DEFAULT_ASSETS[type.value as keyof typeof DEFAULT_ASSETS]}`,
      }));
      setOverrides(initialOverrides);
    } catch (error) {
      console.error("Failed to load assets:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleOverrideChange = (assetType: string, assetId: string) => {
    setOverrides((prev) => {
      const newOverrides = prev.filter((o) => o.assetType !== assetType);

      if (assetId) {
        const asset = availableAssets[assetType]?.find((a) => a.asset_id === assetId);
        if (asset) {
          newOverrides.push({
            assetType,
            assetId,
            name: `${assetType}:${assetId}`,
            version: asset.version,
          });
        }
      }

      return newOverrides;
    });
  };

  const handleRemoveOverride = (assetType: string) => {
    setOverrides((prev) => prev.filter((o) => o.assetType !== assetType));
  };

  const handleTestRun = async () => {
    if (!selectedQuestion.trim()) {
      alert("Please enter a question for testing");
      return;
    }

    const payload = {
      question: selectedQuestion,
      tenant_id: "t1", // Should come from auth context
      asset_overrides: overrides.reduce((acc, override) => {
        acc[`${override.assetType}:${DEFAULT_ASSETS[override.assetType as keyof typeof DEFAULT_ASSETS]}`] = override.assetId;
        return acc;
      }, {} as Record<string, string>),
      test_mode: true,
      baseline_trace_id: baselineTraceId || undefined,
    };

    try {
      setLoading(true);
      const response = await fetchApi("/ops/stage-test", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (response.ok) {
        const result = await response.json();
        // Open results in a new tab or modal
        window.open(`/admin/inspector?trace_id=${result.data.trace_id}`, "_blank");
      } else {
        alert("Test run failed");
      }
    } catch (error) {
      console.error("Test run failed:", error);
      alert("Test run failed");
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = () => {
    if (overrides.length === 0) {
      return (
        <div className="flex items-center gap-2 text-orange-500">
          <AlertCircle className="h-4 w-4" />
          <span className="text-sm">No overrides active</span>
        </div>
      );
    }
    return (
      <div className="flex items-center gap-2 text-green-500">
        <CheckCircle className="h-4 w-4" />
        <span className="text-sm">{overrides.length} overrides active</span>
      </div>
    );
  };

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="w-full max-w-2xl">
        <DrawerHeader>
          <div className="flex items-center justify-between">
            <div>
              <DrawerTitle>Asset Override Test</DrawerTitle>
              <DrawerDescription>
                Test with different asset versions to compare performance and results
              </DrawerDescription>
              {getStatusBadge()}
            </div>
            <Settings className="h-5 w-5 text-slate-400" />
          </div>
        </DrawerHeader>

        <div className="px-6 pb-6 space-y-6">
          {/* Asset Overrides Section */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Asset Overrides</h3>
            <div className="space-y-4">
              {ASSET_TYPES.map((assetType) => {
                const override = overrides.find((o) => o.assetType === assetType.value);
                const available = availableAssets[assetType.value] || [];

                return (
                  <div key={assetType.value} className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                    <div className={`p-2 rounded ${assetType.color}`}>
                      <span className="text-xs text-white font-bold">
                        {assetType.label.charAt(0)}
                      </span>
                    </div>

                    <div className="flex-1">
                      <Label className="text-sm font-medium">{assetType.label}</Label>
                      <Select
                        value={override?.assetId || ""}
                        onValueChange={(value) => handleOverrideChange(assetType.value, value)}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select asset" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">
                            Use default ({DEFAULT_ASSETS[assetType.value as keyof typeof DEFAULT_ASSETS]})
                          </SelectItem>
                          {available.map((asset) => (
                            <SelectItem key={asset.asset_id} value={asset.asset_id}>
                              {asset.name || asset.asset_id} (v{asset.version})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {override && (
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">
                          v{override.version || "latest"}
                        </Badge>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveOverride(assetType.value)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Test Configuration */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Test Configuration</h3>
            <div className="space-y-4">
              <div>
                <Label htmlFor="question">Test Question</Label>
                <Input
                  id="question"
                  placeholder="Enter a question to test with the overrides..."
                  value={selectedQuestion}
                  onChange={(e) => setSelectedQuestion(e.target.value)}
                  className="mt-2"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="baseline-trace">Baseline Trace ID (Optional)</Label>
                  <Input
                    id="baseline-trace"
                    placeholder="Trace ID to compare against"
                    value={baselineTraceId}
                    onChange={(e) => setBaselineTraceId(e.target.value)}
                    className="mt-2"
                  />
                </div>

                <div className="flex items-center space-x-2 pt-6">
                  <button
                    id="test-mode"
                    type="button"
                    role="switch"
                    aria-checked={testMode}
                    onClick={() => setTestMode(!testMode)}
                    className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${testMode ? 'bg-blue-600' : 'bg-slate-200'}`}
                  >
                    <span
                      aria-hidden="true"
                      className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${testMode ? 'translate-x-5' : 'translate-x-0'}`}
                    />
                  </button>
                  <Label htmlFor="test-mode">Test Mode</Label>
                </div>
              </div>
            </div>
          </div>

          {/* Active Overrides Summary */}
          {overrides.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-4">Active Overrides</h3>
              <div className="flex flex-wrap gap-2">
                {overrides.map((override) => (
                  <Badge key={`${override.assetType}-${override.assetId}`} variant="outline">
                    {override.assetType}:{override.assetId}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </div>

        <DrawerFooter>
          <div className="flex gap-3 w-full">
            <DrawerClose asChild>
              <Button variant="outline" className="flex-1">
                Cancel
              </Button>
            </DrawerClose>
            <Button
              onClick={handleTestRun}
              disabled={loading || !selectedQuestion.trim()}
              className="flex-1"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Testing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Test Run
                </>
              )}
            </Button>
          </div>
        </DrawerFooter>
      </DrawerContent>
    </Drawer>
  );
}