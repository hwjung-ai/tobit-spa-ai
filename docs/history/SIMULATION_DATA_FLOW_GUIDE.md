# Simulation Data Flow & Transparency Guide

## Overview

This document explains how SIM (Simulation) system loads and processes data, with complete transparency on data sources and computation flow.

> Note (2026-02-12): `GET /api/sim/predict/timeline`, `POST /api/sim/predict/with-assumptions`, and the frontend `PredictionTimeline` component were removed from active product scope. This guide keeps historical context for archived flow only.

## IMPORTANT: External Monitoring Requirements

**This system provides CLIENT LIBRARIES to connect to your EXISTING infrastructure!**

### You Already Have:

- **Prometheus Server**: Running with exporters (node_exporter, blackbox_exporter, etc.)
- **Kubernetes Cluster**: Running with metrics server
- **AWS Account**: With CloudWatch agents
- **MySQL/PostgreSQL**: Your existing databases

### What We Provide:

- **API Clients**: Code to connect to your existing systems
- **Data Collection**: Scheduled collection to store metrics in database
- **Real-Time Access**: Direct queries without storage

### What You DON'T Need:

- ❌ Install new monitoring agents
- ❌ Deploy new Prometheus servers
- ❌ Set up new Kubernetes clusters
- ❌ Create new AWS accounts

### Just Configure:

```bash
# Set your environment URLs
PROMETHEUS_URL=http://your-prometheus:9090
K8S_API_SERVER=https://your-k8s-api:6443
CLOUDWATCH_REGION=us-east-1
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│         YOUR EXISTING INFRASTRUCTURE              │
├─────────────────────────────────────────────────────────┤
│  [Prometheus]                 [Kubernetes]    [AWS]   │
│  :9090                      :6443          CloudWatch│
│     ↓                          ↓                ↓        │
└─────────────────────────────────────────────────────────┘
          ↓                    ↓                ↓
┌─────────────────────────────────────────────────────────┐
│         OUR API CLIENTS                            │
├─────────────────────────────────────────────────────────┤
│  PrometheusCollector    KubernetesIngestor   CloudWatch  │
│  (httpx async)       (httpx async)      Collector  │
└─────────────────────────────────────────────────────────┘
          ↓                    ↓                ↓
┌─────────────────────────────────────────────────────────┐
│         DATA STORAGE                               │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL                      Neo4j           │
│  (metric_timeseries)              (topology)       │
└─────────────────────────────────────────────────────────┘
```

**Key Difference**:
- **DB Mode**: Use for production with scheduled data collection
- **Real-Time Mode**: Use for testing, demos, or when storage is not available

## Data Source Priority

### DB Mode Priority (3-tier fallback):

The simulation system uses a **3-tier fallback** for loading baseline KPI data:

### 1. Actual Metric Timeseries (Best)
- **Source**: PostgreSQL `tb_metric_timeseries` table
- **Accuracy**: Highest (real historical measurements)
- **Indicators**:
  - `data_source: "metric_timeseries"`
  - Green "Real Metrics" badge in UI
  - High completeness (>80%)
  - Low recency (<2 hours)

```python
# metric_loader.py
def load_baseline_kpis(tenant_id, service, hours_back=168):
    # Loads last 168 hours (7 days) of actual metrics
    # Returns: {latency_ms, throughput_rps, error_rate_pct, cost_usd_hour}
```

### 2. Tool Asset Registry (Medium)
- **Source**: Asset Registry via DynamicTool
- **Accuracy**: Medium (depends on external tools)
- **Indicators**:
  - `data_source: "tool"`
  - Yellow "Tool Asset" badge in UI
  - Reliable if tools return valid metric data

```python
# metric_tool.py
async def load_metric_kpis_via_tool(tenant_id, service, hours_back):
    # Uses Tool Asset Registry to fetch metrics
    # Fallback for when direct DB access fails
```

### 3. Topology Fallback (Lowest)
- **Source**: Neo4j topology derivation
- **Accuracy**: Lowest (formula-based estimates)
- **Indicators**:
  - `data_source: "topology_fallback"`
  - Yellow "Topology Fallback" badge in UI
  - Warning: "No metric data available - using topology-derived estimates"

```python
# baseline_loader.py
def _derive_kpis_from_topology(topology):
    # Derives KPIs from node simulated_load and link simulated_traffic
    # Warning: This is NOT real metric data
```

### Real-Time Mode Priority (2-tier):

1. **Direct API Call** (Prometheus/CloudWatch) - Live metrics
2. **Topology Fallback** (Neo4j) - Formula estimates

## Real-Time Prediction Timeline (Archived)

### Removed Endpoint: `/api/sim/predict/timeline`

Shows **yesterday's actual data** with **today's predicted range**:

This endpoint is no longer served.

**Response Structure**:
```json
{
  "data_source": "metric_timeseries" | "tool" | "topology_fallback",
  "data_quality": {
    "completeness": 0.95,      // % of expected data points
    "recency_hours": 1.2,        // How fresh is data
    "total_points": 384            // 4 metrics × 96 15-min intervals
  },
  "historical_data": {
    "latency_ms": {
      "values": [45.2, 47.1, ...],    // Last 24 hours
      "mean": 48.3,
      "std": 5.2,
      "min": 42.1,
      "max": 58.9
    }
  },
  "prediction_ranges": {
    "latency_ms": {
      "predicted": 48.3,          // Expected value
      "lower_bound": 42.1,          // 90% CI low
      "upper_bound": 54.5,          // 90% CI high
      "confidence_level": 0.90,
      "std_dev": 5.2,
      "relative_range_pct": 25.7      // Width of interval
    }
  },
  "timeline": [
    {
      "hour": "2026-02-11T00:00:00Z",
      "hour_offset": 0,
      "latency_ms": {
        "predicted": 48.3,
        "lower_bound": 42.1,
        "upper_bound": 54.5
      }
    },
    // ... 24 hours of predictions
  ]
}
```

### Removed Endpoint: `/api/sim/predict/with-assumptions`

Shows **baseline** vs **assumption-adjusted** predictions:

This endpoint is no longer served.

**Response Structure**:
```json
{
  "baseline": { /* Prediction without assumptions */ },
  "adjusted": { /* Prediction with assumptions applied */ },
  "assumptions": { /* Echoed input */ },
  "impact_summary": {
    "combined_impact_pct": 15.0,
    "traffic_contribution_pct": 12.0,
    "resource_contribution_pct": 3.0
  }
}
```

## SSE Stream Transparency

### Real-Time Simulation Endpoint: `/api/sim/stream/run`

**NO artificial delays** - shows real computation time.

**SSE Events**:

#### 1. Progress Event
```json
{
  "event": "progress",
  "data": {
    "step": "planning",
    "message": "Planning simulation",
    "elapsed_ms": 12.5
  }
}
```

#### 2. Baseline Event (with data source!)
```json
{
  "event": "baseline",
  "data": {
    "kpis": {
      "latency_ms": 48.3,
      "throughput_rps": 1024.5,
      "error_rate_pct": 0.12,
      "cost_usd_hour": 12.5
    },
    "data_source": "metric_timeseries",
    "computation_time_ms": 45.2,
    "data_quality": {
      "metrics_available": true,
      "using_fallback": false,
      "note": "Using actual metric data"
    }
  }
}
```

#### 3. Complete Event (with timing breakdown)
```json
{
  "event": "complete",
  "data": {
    "simulation": { /* Standard SimulationResult */ },
    "timing": {
      "total_ms": 234.5,
      "planning_ms": 12.5,
      "baseline_loading_ms": 45.2,
      "strategy_execution_ms": 176.8
    },
    "data_source": "metric_timeseries",
    "data_transparency": {
      "baseline_from_real_metrics": true,
      "baseline_from_topology_fallback": false,
      "strategy_used": "ml",
      "strategy_computation_real": true
    }
  }
}
```

## Data Collection API

### Batch Collection (for DB Mode)

Collect and store metrics for future use:

```bash
# Prometheus
POST /workers/metrics/collect
{
  "source": "prometheus",
  "query": "rate(http_requests_total[5m])",
  "hours_back": 24
}

# CloudWatch
POST /workers/metrics/collect
{
  "source": "cloudwatch",
  "query": "{\"namespace\": \"AWS/EC2\", \"metric_name\": \"CPUUtilization\"}"
}
```

### Real-Time Fetch (for Real-Time Mode)

Fetch metrics without storing:

```bash
# Prometheus
POST /workers/metrics/fetch
{
  "source": "prometheus",
  "query": "rate(http_requests_total[5m])",
  "hours_back": 1
}

# CloudWatch
POST /workers/metrics/fetch
{
  "source": "cloudwatch",
  "query": "{\"namespace\": \"AWS/EC2\", \"metric_name\": \"CPUUtilization\"}"
}
```

## Frontend Components

### 1. PredictionTimeline Component (Removed)

This component was removed from active scope.

### 2. RealTimeSimulation Component (Updated)

**New Features**:
- Data source badge in baseline section
- Data source transparency in final result
- Computation timing breakdown
- No fake delays - shows real progress

**Badges**:
- 🟢 Green = Real Metric Data
- 🟡 Yellow = Topology Fallback

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   SIMULATION REQUEST                          │
│  (service, strategy, assumptions, horizon)                  │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              STEP 1: CHOOSE MODE                             │
├─────────────────────────────────────────────────────────────────┤
│  DB Mode (Default)                                         │
│  - Fast: Loads from PostgreSQL                                │
│  - Offline: Works without external APIs                       │
│  - Use for: Production with scheduled collection                │
│                                                              │
│  Real-Time Mode (Optional)                                   │
│  - Fresh: Calls Prometheus/CloudWatch directly                   │
│  - Online: Requires external APIs to be up                     │
│  - Use for: Testing, demos, no-DB scenarios               │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 2: LOAD BASELINE DATA                        │
├─────────────────────────────────────────────────────────────────┤
│  DB Mode:                                                  │
│  1. Tool Asset Registry (if available)                          │
│  2. PostgreSQL tb_metric_timeseries                             │
│  3. Neo4j Topology (fallback)                                │
│                                                              │
│  Real-Time Mode:                                            │
│  1. Prometheus/CloudWatch API                                  │
│  2. Neo4j Topology (fallback)                                │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 3: GENERATE PREDICTION                        │
├─────────────────────────────────────────────────────────────────┤
│  • Calculate prediction interval (confidence-based)              │
│  • Apply assumptions (traffic, cpu, memory)                 │
│  • Run strategy (rule/stat/ml/dl)                          │
└──────────────────────────────┬────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│           STEP 4: RETURN RESULTS                             │
├─────────────────────────────────────────────────────────────────┤
│  • Data source indicator (metric_timeseries/topology)          │
│  • Data quality metrics (completeness, recency)              │
│  • Prediction ranges (lower, predicted, upper)              │
│  • Timing breakdown (planning, loading, strategy)           │
└─────────────────────────────────────────────────────────────────┘
```

## Ensuring Data Transparency

### For Users

1. **Always check data source badge** - Green is best, Yellow means fallback
2. **Review data quality metrics** - Higher completeness = more reliable
3. **Check timing breakdown** - Shows which steps take longest
4. **Understand prediction intervals** - 90% CI means actual value falls within range 90% of time

### For Developers

1. **Never hide data source** - Always indicate where data came from
2. **No artificial delays** - Real computation time builds trust
3. **Log fallbacks** - When topology derivation is used, log warning
4. **Include error bounds** - Always provide uncertainty estimates

## Troubleshooting

### Problem: Always seeing "Topology Fallback"

**Cause**: No metric timeseries data in database

**Solutions**:
1. Run `/workers/metrics/collect` to populate database
2. Use Real-Time Mode to fetch from Prometheus/CloudWatch directly
3. Check if `tb_metric_timeseries` table has data

### Problem: Low completeness (<50%)

**Cause**: Sparse metric data (missing metrics or time periods)

**Solutions**:
1. Check metric collection agent is sending all 4 metrics
2. Verify retention policy isn't deleting data too quickly
3. Check for data gaps during maintenance windows

### Problem: High recency (>12 hours)

**Cause**: Data ingestion stopped or delayed

**Solutions**:
1. Restart metric collection pipeline
2. Check PostgreSQL connection
3. Verify metric API endpoints are accessible

## API Examples

### DB Mode Simulation (with stored data)
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What happens if traffic increases 20%?",
    "scenario_type": "what_if",
    "strategy": "ml",
    "horizon": "24h",
    "service": "api-server",
    "assumptions": {"traffic_change_pct": 20}
  }' \
  https://api.example.com/api/sim/run
```

### Real-Time Simulation (with live metrics)
```bash
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What happens if traffic increases 20%?",
    "scenario_type": "what_if",
    "strategy": "ml",
    "horizon": "24h",
    "service": "api-server",
    "assumptions": {"traffic_change_pct": 20},
    "source_config": {
      "source": "prometheus",
      "prometheus_url": "http://prometheus:9090",
      "query": "rate(http_requests_total[5m])"
    }
  }' \
  https://api.example.com/api/sim/run/realtime
```

### Prediction timeline endpoints
Removed from active scope (`/api/sim/predict/timeline`, `/api/sim/predict/with-assumptions`).

### Stream simulation with SSE
```javascript
const eventSource = new EventSource(
  '/api/sim/stream/run?' + new URLSearchParams({
    question: 'What happens if traffic increases 20%?',
    scenario_type: 'what_if',
    strategy: 'ml',
    horizon: '24h',
    service: 'api-server',
    assumptions: JSON.stringify({traffic_change_pct: 20})
  })
);

eventSource.addEventListener('baseline', (e) => {
  const data = JSON.parse(e.data);
  console.log('Data source:', data.data_source);  // ← CHECK THIS
  console.log('Data quality:', data.data_quality);
});
```

## Summary

The simulation system now provides **complete data transparency** with **two modes**:

- ✅ **DB Mode**: Fast, offline, for production
- ✅ **Real-Time Mode**: Fresh, online, for testing
- ✅ Data source always shown (metric_timeseries, tool, or topology_fallback)
- ✅ Data quality metrics (completeness, recency, total points)
- ✅ Real computation timing (no fake delays)
- ✅ Prediction intervals with confidence levels
- ✅ Visual indicators (green/yellow badges) in UI

Users can now **choose** between:
1. **Fast DB Mode** when scheduled collection is running
2. **Fresh Real-Time Mode** when latest data is needed

Both modes provide **complete transparency** on where data comes from and how predictions were computed.
