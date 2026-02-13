"use client";

import { useState, useEffect, useMemo } from "react";
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Clock,
  RefreshCw,
  GitMerge,
  Target,
  Layers,
  Activity,
  Download
} from "lucide-react";
import { cn } from "@/lib/utils";

interface AssetMetrics {
  version: string;
  usage_count: number;
  avg_duration_ms: number;
  success_rate: number;
  error_count: number;
  warning_count: number;
  reference_count: number;
  quality_score: number;
  performance_impact: number;
}

interface ImpactAnalysis {
  asset_id: string;
  versions: {
    [version: string]: AssetMetrics;
  };
  comparisons: {
    baseline_version: string;
    current_version: string;
    changes: {
      quality_change: number;
      performance_change: number;
      error_rate_change: number;
      confidence_score: number;
    };
  };
  related_assets: string[];
  regression_risk: "low" | "medium" | "high";
  recommendations: string[];
}

interface AssetImpactAnalyzerProps {
  className?: string;
  assetType: string;
  assetId: string;
  currentVersion?: string;
  onVersionSelect?: (version: string) => void;
  onExport?: (data: unknown) => void;
}

const IMPACT_COLORS = {
  low: "#10b981", // green
  medium: "#f59e0b", // amber
  high: "#ef4444", // red
};

const QualityRadarData = [
  { subject: 'Performance', A: 120, fullMark: 150 },
  { subject: 'Reliability', A: 98, fullMark: 150 },
  { subject: 'Maintainability', A: 86, fullMark: 150 },
  { subject: 'Security', A: 99, fullMark: 150 },
  { subject: 'Scalability', A: 85, fullMark: 150 },
  { subject: 'Usability', A: 65, fullMark: 150 },
];

export default function AssetImpactAnalyzer({
  className,
  assetType,
  assetId,
  currentVersion,
  onVersionSelect,
  onExport,
}: AssetImpactAnalyzerProps) {
  const [selectedVersion, setSelectedVersion] = useState(currentVersion);
  const [impactData, setImpactData] = useState<ImpactAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [compareMode, setCompareMode] = useState(false);
  const [compareVersions, setCompareVersions] = useState<string[]>([]);

  // Mock data for demonstration
  const mockMetrics = useMemo(() => [
    {
      version: "1.0.0",
      usage_count: 150,
      avg_duration_ms: 250,
      success_rate: 98,
      error_count: 3,
      warning_count: 5,
      reference_count: 45,
      quality_score: 85,
      performance_impact: 10
    },
    {
      version: "1.1.0",
      usage_count: 200,
      avg_duration_ms: 220,
      success_rate: 99,
      error_count: 1,
      warning_count: 2,
      reference_count: 52,
      quality_score: 88,
      performance_impact: -5
    },
    {
      version: "1.2.0",
      usage_count: 300,
      avg_duration_ms: 180,
      success_rate: 97,
      error_count: 4,
      warning_count: 8,
      reference_count: 60,
      quality_score: 82,
      performance_impact: -15
    },
    {
      version: "1.3.0",
      usage_count: 250,
      avg_duration_ms: 190,
      success_rate: 99.5,
      error_count: 1,
      warning_count: 3,
      reference_count: 58,
      quality_score: 92,
      performance_impact: -10
    },
    {
      version: "2.0.0",
      usage_count: 50,
      avg_duration_ms: 300,
      success_rate: 95,
      error_count: 2,
      warning_count: 6,
      reference_count: 70,
      quality_score: 78,
      performance_impact: 25
    },
  ] as AssetMetrics[], []);

  useEffect(() => {
    // Simulate loading impact data
    const timer = setTimeout(() => {
      const mockImpact: ImpactAnalysis = {
        asset_id: assetId,
        versions: mockMetrics.reduce((acc, metric) => {
          acc[metric.version] = metric;
          return acc;
        }, {} as { [key: string]: AssetMetrics }),
        comparisons: {
          baseline_version: "1.0.0",
          current_version: selectedVersion || "2.0.0",
          changes: {
            quality_change: -7,
            performance_change: 25,
            error_rate_change: -33,
            confidence_score: 75
          }
        },
        related_assets: ["policy:user-01", "query:global", "mapping:default"],
        regression_risk: "medium",
        recommendations: [
          "Version 2.0.0 shows increased latency (25ms)",
          "Consider testing in staging environment first",
          "Review error patterns from recent executions"
        ]
      };
      setImpactData(mockImpact);
      setLoading(false);
    }, 1000);

    return () => clearTimeout(timer);
  }, [assetId, selectedVersion, mockMetrics]);

  const handleVersionSelect = (version: string) => {
    setSelectedVersion(version);
    onVersionSelect?.(version);
    setCompareMode(false);
    setCompareVersions([]);
  };

  const toggleCompareMode = (version: string) => {
    if (compareMode) {
      if (compareVersions.includes(version)) {
        setCompareVersions(compareVersions.filter(v => v !== version));
      } else if (compareVersions.length < 2) {
        setCompareVersions([...compareVersions, version]);
      }
    } else {
      setCompareMode(true);
      setCompareVersions([version]);
    }
  };

  const formatImpactScore = (score: number) => {
    const color = score >= 0 ? "text-red-400" : "text-emerald-400";
    const icon = score >= 0 ? TrendingUp : TrendingDown;
    const Icon = icon;
    return (
      <div className={cn("flex items-center gap-1", color)}>
        <Icon className="h-3 w-3" />
        <span className="text-sm font-medium">{Math.abs(score)}ms</span>
      </div>
    );
  };

  // Render the VersionComparisonTable conditionally
  const renderVersionComparison = () => {
    if (!impactData || compareVersions.length < 2) return null;

    const [version1, version2] = compareVersions;
    const metrics1 = impactData.versions[version1];
    const metrics2 = impactData.versions[version2];

    return (
      <div className="mt-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-foreground">
                  <GitMerge className="h-5 w-5" />
          Version Comparison: {version1} vs {version2}
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full border rounded-lg border-border">
            <thead>
              <tr className="border-b bg-slate-500/40 border-border">
                <th className="text-left p-3 text-sm font-medium text-foreground">Metric</th>
                <th className="text-left p-3 text-sm font-medium text-foreground">
                  {version1}
                </th>
                <th className="text-left p-3 text-sm font-medium text-foreground">
                  {version2}
                </th>
                <th className="text-left p-3 text-sm font-medium text-foreground">Change</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border">
                <td className="p-3 text-sm text-foreground">Duration</td>
                <td className="p-3 text-sm text-foreground">{metrics1.avg_duration_ms}ms</td>
                <td className="p-3 text-sm text-foreground">{metrics2.avg_duration_ms}ms</td>
                <td className="p-3">
                  {formatImpactScore(metrics2.avg_duration_ms - metrics1.avg_duration_ms)}
                </td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 text-sm text-foreground">Success Rate</td>
                <td className="p-3 text-sm text-foreground">{metrics1.success_rate}%</td>
                <td className="p-3 text-sm text-foreground">{metrics2.success_rate}%</td>
                <td className={cn(
                  "p-3 flex items-center gap-1",
                  metrics2.success_rate > metrics1.success_rate ? "text-emerald-400" : "text-red-400"
                )}>
                  {metrics2.success_rate > metrics1.success_rate ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                  <span className="text-sm font-medium">
                    {Math.abs(metrics2.success_rate - metrics1.success_rate)}%
                  </span>
                </td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 text-sm text-foreground">Errors</td>
                <td className="p-3 text-sm text-foreground">{metrics1.error_count}</td>
                <td className="p-3 text-sm text-foreground">{metrics2.error_count}</td>
                <td className={cn(
                  "p-3 flex items-center gap-1",
                  metrics2.error_count < metrics1.error_count ? "text-emerald-400" : "text-red-400"
                )}>
                  {metrics2.error_count < metrics1.error_count ? <TrendingDown className="h-4 w-4" /> : <TrendingUp className="h-4 w-4" />}
                  <span className="text-sm font-medium">
                    {Math.abs(metrics2.error_count - metrics1.error_count)}
                  </span>
                </td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 text-sm text-foreground">Quality Score</td>
                <td className="p-3 text-sm text-foreground">{metrics1.quality_score}/100</td>
                <td className="p-3 text-sm text-foreground">{metrics2.quality_score}/100</td>
                <td className={cn(
                  "p-3 flex items-center gap-1",
                  metrics2.quality_score > metrics1.quality_score ? "text-emerald-400" : "text-red-400"
                )}>
                  {metrics2.quality_score > metrics1.quality_score ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                  <span className="text-sm font-medium">
                    {Math.abs(metrics2.quality_score - metrics1.quality_score)}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className={cn("flex items-center justify-center h-64 rounded-2xl border border-border", className)}>
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-muted-foreground" />
          <p className="text-muted-foreground">Analyzing asset impact...</p>
        </div>
      </div>
    );
  }

  if (!impactData) {
    return (
      <div className={cn("flex items-center justify-center h-64 rounded-2xl border border-border", className)}>
        <p className="text-muted-foreground">No impact data available</p>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full rounded-2xl border border-border bg-surface-overlay", className)}>
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold flex items-center gap-2 text-foreground">
              <Activity className="h-5 w-5" />
              Asset Impact Analysis
            </h2>
            <p className="text-sm mt-1 text-muted-foreground">
              {assetId} • {assetType}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onExport?.(impactData)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs transition hover:opacity-80 bg-surface-elevated text-muted-foreground border border-border"
            >
              <Download className="h-3 w-3" />
              Export
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Version Selection */}
        <div>
          <h3 className="text-lg font-semibold mb-3 text-foreground">Version History</h3>
          <div className="flex flex-wrap gap-2">
            {Object.keys(impactData.versions).map((version) => {
              const metrics = impactData.versions[version];
              const isSelected = selectedVersion === version;
              const isInCompare = compareVersions.includes(version);
              const isBaseline = impactData.comparisons.baseline_version === version;

              return (
                <button
                  key={version}
                  onClick={() => compareMode ? toggleCompareMode(version) : handleVersionSelect(version)}
                  className={cn(
                    "px-3 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2",
                    isSelected
                      ? "bg-sky-500 text-white"
                      : isInCompare
                      ? "bg-purple-500/20 text-purple-400 border border-purple-400/30"
                      : isBaseline
                      ? "bg-emerald-500/20 text-emerald-400 border border-emerald-400/30"
                      : "bg-surface-elevated text-foreground"
                  )}
                >
                  {isBaseline && <CheckCircle className="h-3 w-3" />}
                  {isInCompare && <Layers className="h-3 w-3" />}
                  v{version}
                  <span className="text-xs opacity-70">
                    ({metrics.usage_count} uses)
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Current Version Metrics */}
        {selectedVersion && (
          <div>
            <h3 className="text-lg font-semibold mb-3 text-foreground">
              Current Version: v{selectedVersion}
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="rounded-lg p-4 bg-slate-500/50">
                <div className="flex items-center gap-2 text-emerald-400">
                  <CheckCircle className="h-4 w-4" />
                  <span className="text-xs">Success Rate</span>
                </div>
                <p className="text-2xl font-bold mt-1 text-foreground">
                  {impactData.versions[selectedVersion].success_rate}%
                </p>
              </div>
              <div className="rounded-lg p-4 bg-slate-500/50">
                <div className="flex items-center gap-2 text-sky-400">
                  <Clock className="h-4 w-4" />
                  <span className="text-xs">Avg Duration</span>
                </div>
                <p className="text-2xl font-bold mt-1 text-foreground">
                  {impactData.versions[selectedVersion].avg_duration_ms}ms
                </p>
              </div>
              <div className="rounded-lg p-4 bg-slate-500/50">
                <div className="flex items-center gap-2 text-amber-400">
                  <AlertTriangle className="h-4 w-4" />
                  <span className="text-xs">Errors</span>
                </div>
                <p className="text-2xl font-bold mt-1 text-foreground">
                  {impactData.versions[selectedVersion].error_count}
                </p>
              </div>
              <div className="rounded-lg p-4 bg-slate-500/50">
                <div className="flex items-center gap-2 text-purple-400">
                  <Target className="h-4 w-4" />
                  <span className="text-xs">Quality Score</span>
                </div>
                <p className="text-2xl font-bold mt-1 text-foreground">
                  {impactData.versions[selectedVersion].quality_score}/100
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Regression Risk */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold text-foreground">Regression Risk</h3>
            <div className={cn(
              "px-3 py-1 rounded-full text-sm font-medium",
              impactData.regression_risk === "low" ? "bg-emerald-500/20 text-emerald-400" :
              impactData.regression_risk === "medium" ? "bg-amber-500/20 text-amber-400" :
              "bg-red-500/20 text-red-400"
            )}>
              {impactData.regression_risk.toUpperCase()}
            </div>
          </div>
          <div className="rounded-lg p-4 bg-slate-500/50">
            <p className="text-sm mb-3 text-foreground">
              Based on performance metrics and error patterns, this version has a {impactData.regression_risk} risk of introducing regressions.
            </p>
            <div className="flex items-center gap-4 text-xs text-foreground">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-emerald-400"></div>
                <span>Low Risk</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-amber-400"></div>
                <span>Medium Risk</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-400"></div>
                <span>High Risk</span>
              </div>
            </div>
          </div>
        </div>

        {/* Quality Radar Chart */}
        <div>
          <h3 className="text-lg font-semibold mb-3 text-foreground">Quality Metrics</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart data={QualityRadarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--chart-text-color)', fontSize: 12 }} />
                <PolarRadiusAxis angle={30} domain={[0, 150]} tick={{ fill: 'var(--chart-text-color)', fontSize: 12 }} />
                <Radar
                  name={selectedVersion || "Current"}
                  dataKey="A"
                  stroke={IMPACT_COLORS[impactData.regression_risk]}
                  fill={IMPACT_COLORS[impactData.regression_risk]}
                  fillOpacity={0.2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Version Comparison */}
        {renderVersionComparison()}

        {/* Related Assets */}
        <div>
          <h3 className="text-lg font-semibold mb-3 text-foreground">Related Assets</h3>
          <div className="flex flex-wrap gap-2">
            {impactData.related_assets.map((asset, index) => (
              <span
                key={index}
                className="px-3 py-1 rounded-full text-xs border bg-surface-elevated text-foreground border-border"
              >
                {asset}
              </span>
            ))}
          </div>
        </div>

        {/* Recommendations */}
        <div>
          <h3 className="text-lg font-semibold mb-3 text-foreground">Recommendations</h3>
          <div className="space-y-2">
            {impactData.recommendations.map((rec, index) => (
              <div key={index} className="flex items-start gap-2">
                <div className="w-2 h-2 rounded-full bg-sky-400 mt-1.5"></div>
                <p className="text-sm text-foreground">{rec}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}