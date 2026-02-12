# SIM (Simulation) System - Complete Guide

## Overview

Complete guide for the SIM simulation system including data collection, model training, and simulation execution.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture Overview](#architecture-overview)
3. [Data Collection](#data-collection)
4. [Simulation Modes](#simulation-modes)
5. [Model Training](#model-training)
6. [API Reference](#api-reference)
7. [Frontend Components](#frontend-components)

---

## Quick Start

### For Production Use (DB Mode)

1. **Set up monitoring** (already running)
   - Prometheus server with exporters
   - Kubernetes cluster
   - PostgreSQL database

2. **Configure connection**
   ```bash
   # In .env or UI Settings
   PROMETHEUS_URL=http://your-prometheus:9090
   K8S_API_SERVER=https://your-k8s-api:6443
   ```

3. **Collect metrics** (one-time or scheduled)
   ```bash
   POST /api/workers/metrics/collect
   {
     "source": "prometheus",
     "query": "rate(http_requests_total[5m])",
     "hours_back": 24
   }
   ```

4. **Run simulation**
   ```bash
   POST /api/sim/run
   {
     "service": "api-server",
     "strategy": "ml",
     "assumptions": {"traffic_change_pct": 20}
   }
   ```

### For Testing (Real-Time Mode)

1. **No setup required** - just configure URLs

2. **Run real-time simulation**
   ```bash
   POST /api/sim/run/realtime
   {
     "service": "api-server",
     "strategy": "ml",
     "source_config": {
       "source": "prometheus",
       "prometheus_url": "http://prometheus:9090"
     }
   }
   ```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER REQUEST                          │
│  (service, strategy, assumptions, horizon)                  │
└──────────────────────────────┬────────────────────────────────┘
                               │
                ┌──────────┴──────────┐
                │ MODE SELECTION      │
                │                    │
         ┌──────┴─────┐          │
         │              │          │
    DB MODE    REALTIME      │          │
    (Fast)      (Fresh)     │          │
    │              │          │
    ▼              ▼          │
┌─────────────────────────────────────────────────────────┐
│           DATA SOURCE (3-TIER FALLBACK)              │
├─────────────────────────────────────────────────────────┤
│ 1. Tool Asset Registry (metric_timeseries)  [BEST]│
│ 2. PostgreSQL Direct Access (metric_timeseries)     │
│ 3. Neo4j Topology Fallback [ESTIMATE]        │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│           STRATEGY EXECUTION                     │
├─────────────────────────────────────────────────────────┤
│ • Rule: Weight-based formulas                      │
│ • Stat: EMA + Regression                          │
│ • ML: RandomForest / GradientBoosting (with model)   │
│ • DL: LSTM / Transformer (with model)              │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│           OUTPUT + TRANSPARENCY                   │
├─────────────────────────────────────────────────────────┤
│ • KPI Results (4 metrics)                        │
│ • Data Source Badge (Green/Yellow)                   │
│ • Confidence Interval (90% CI)                       │
│ • Computation Timing (real ms, no fake delays)    │
└─────────────────────────────────────────────────────────┘
```

---

## Data Collection

### IMPORTANT: What We Provide

**We provide CLIENT LIBRARIES**, not monitoring agents.**

You must have ALREADY INSTALLED:
- **Prometheus Server** with exporters (node_exporter, blackbox_exporter)
- **Kubernetes Cluster** with metrics server
- **AWS Account** with CloudWatch agents

Our code connects to YOUR existing infrastructure via APIs.

### Two Collection Modes

#### Batch Mode (DB Storage)

**Endpoint**: `POST /api/workers/metrics/collect`

Collect and store in database for future use.

```bash
# Prometheus
POST /api/workers/metrics/collect
{
  "source": "prometheus",
  "query": "rate(http_requests_total[5m])",
  "hours_back": 24  # Last 24 hours
}

# CloudWatch
POST /api/workers/metrics/collect
{
  "source": "cloudwatch",
  "query": "{\"namespace\": \"AWS/EC2\", \"metric_name\": \"CPUUtilization\"}"
}
```

**Use for**: Scheduled collection (cron/scheduler), building historical dataset

#### Real-Time Mode (Direct Return)

**Endpoint**: `POST /api/workers/metrics/fetch`

Fetch and return immediately without storing.

```bash
POST /api/workers/metrics/fetch
{
  "source": "prometheus",
  "query": "rate(http_requests_total[5m])",
  "hours_back": 1  # Last 1 hour only
}
```

**Use for**: Ad-hoc queries, testing, demos

### Data Source Priority (3-Tier Fallback)

```
1. Tool Asset Registry (metric_timeseries) ←─────┐
   - Via DynamicTool                           │
   - Highest priority                        │
   - If available → use                   │ REQUEST
                                             │
2. PostgreSQL Direct (metric_timeseries)    ←─────┤
   - Direct DB query                         │
   - Fallback if Tool fails               │
                                             │
3. Neo4j Topology Fallback               ←─────┘
   - Formula-based estimates
   - Lowest priority
   - Only if 1 & 2 fail
```

**Data Source Indicators**:
- 🟢 Green: `metric_timeseries` - Real metrics
- 🟡 Yellow: `topology_fallback` - Estimates (no real metrics)

---

## Simulation Modes

### DB Mode (Default)

**Endpoint**: `POST /api/sim/run`

Loads from stored metrics in PostgreSQL.

**Characteristics**:
- ⚡ Fast response (no external API calls)
- 💾 Offline capable (can query past timestamps)
- 📊 Historical analysis (time-travel to any point)
- 🔄 Best for production with scheduled collection

### Real-Time Mode

**Endpoint**: `POST /api/sim/run/realtime`

Fetches directly from Prometheus/CloudWatch.

**Characteristics**:
- 🕐 Always fresh data
- 🔌 No database dependency
- ⏱️ Slower response (external API latency)
- 🧪 Best for testing, demos, or when DB is empty

**Comparison**:

| Aspect | DB Mode | Real-Time Mode |
|--------|----------|----------------|
| Speed | ⚡ Fast | ⏱️ Slower (API call) |
| Freshness | 📅 As of last collection | 🕐 Always live |
| Offline | ✅ Yes (time-travel) | ❌ No |
| Use Case | Production | Testing/Demo |

### SSE Stream Mode

**Endpoint**: `GET /api/sim/stream/run`

Server-Sent Events for real-time progress.

**Events**:
- `progress` - Step-by-step progress
- `baseline` - Loaded baseline with data source
- `kpi` - Individual KPI results
- `complete` - Final result with timing

**No Artificial Delays** - Shows real computation time!

---

## Model Training

### ML Model Registry

**Database Table**: `tb_ml_models`

Stores trained models with metadata:
- Model key (unique ID)
- Tenant/Service
- Model type (surrogate, ml, dl)
- Version (timestamp)
- Model blob (pickled model)
- Performance metrics (R², MAPE, RMSE)
- Active flag (one active model per tenant/service/type)

### Training Pipeline

**Endpoint**: `POST /api/workers/ml/train`

```bash
POST /api/workers/ml/train
{
  "service": "api-server",
  "model_type": "random_forest",
  "training_samples": 1000,
  "use_synthetic": true  # For testing without real data
}
```

**Response**:
- Model key
- Version
- Performance metrics (R², MAPE, RMSE)
- Feature/target names

### Model Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/workers/ml/models` | GET | List all models |
| `/workers/ml/models/active` | GET | Get active model |
| `/workers/ml/models/activate` | POST | Activate a model |
| `/workers/ml/models/{key}` | DELETE | Delete a model |

---

## API Reference

### Simulation Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sim/run` | POST | DB mode simulation |
| `/api/sim/run/realtime` | POST | Real-time mode simulation |
| `/api/sim/stream/run` | GET | SSE stream simulation |
| `/api/sim/functions` | GET | List function library |
| `/api/sim/functions/{id}` | GET | Get function details |

### Data Collection Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workers/metrics/collect` | POST | Batch collect (save to DB) |
| `/api/workers/metrics/fetch` | POST | Real-time fetch (no save) |
| `/api/workers/metrics/sources` | GET | Get source status |
| `/api/workers/topology/collect` | POST | Collect topology |
| `/api/workers/topology/sources` | GET | Get topology status |

### ML Training Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workers/ml/train` | POST | Train model |
| `/api/workers/ml/models` | GET | List models |
| `/api/workers/ml/models/active` | GET | Get active model |
| `/api/workers/ml/models/activate` | POST | Activate model |
| `/api/workers/ml/models/{key}` | DELETE | Delete model |
| `/api/workers/status` | GET | System status |

---

## Frontend Components

### Simulation Page

**Location**: `/apps/web/src/app/sim/page.tsx`

Main simulation interface with:
- Question input
- Scenario type selection
- Strategy selection (rule/stat/ml/dl)
- Assumption inputs (traffic, cpu, memory)
- Service selection
- Results display

### Real-Time Simulation

**Location**: `/apps/web/src/components/simulation/RealTimeSimulation.tsx`

Features:
- SSE event streaming
- Real-time progress display
- Data source badge (Green/Yellow)
- Computation timing breakdown
- KPI results table

### Function Library

**Location**: `/apps/web/src/components/simulation/FunctionBrowser.tsx`

Browse and execute simulation functions:
- 25+ built-in functions
- 4 categories (rule, stat, ml, domain)
- Function comparison
- Custom function support

---

## Data Flow Diagrams

### DB Mode Flow

```
User Request
     │
     ▼
┌─────────────────────────┐
│ Load from PostgreSQL │
│ (metric_timeseries)   │
└──────────┬───────────┘
           │
    ┌──────┴─────┐
    │             │
  Tool          Direct
(Available?)    (Query)
    │             │
    └──────┬──────┘
           │
           ▼ (if both fail)
    ┌─────────────────┐
    │ Topology       │
    │ Fallback       │
    └──────────┬──────┘
               │
               ▼
        Baseline KPIs
               │
               ▼
        Run Strategy
               │
               ▼
        Results + Transparency
```

### Real-Time Mode Flow

```
User Request + source_config
     │
     ▼
┌─────────────────────────┐
│ Call Prometheus/     │
│ CloudWatch API      │
└──────────┬───────────┘
           │
           ▼
    ┌──────┴─────┐
    │             │
Success      Topology
(Direct)     Fallback
    │             │
    └──────┬──────┘
           │
               ▼
        Fresh Baseline KPIs
               │
               ▼
        Run Strategy
               │
               ▼
        Results + Transparency
```

---

## Troubleshooting

### Problem: Always seeing "Topology Fallback" (Yellow Badge)

**Cause**: No metric data in database or tools

**Solutions**:
1. Run batch collection: `POST /api/workers/metrics/collect`
2. Check Prometheus connectivity
3. Verify metric exporters are running

### Problem: Real-Time Mode Timeout

**Cause**: Prometheus/CloudWatch not accessible

**Solutions**:
1. Check network connectivity
2. Verify URLs in configuration
3. Check authentication tokens

### Problem: ML Model Training Fails

**Cause**: No training data

**Solutions**:
1. Use synthetic data: `use_synthetic=true`
2. Collect historical metrics first
3. Check feature columns match

---

## Summary

### Current Status

| Component | Status | Description |
|-----------|--------|-------------|
| **Simulation Execution** | ✅ Complete | DB + Real-Time modes |
| **Data Collection** | ✅ Complete | Prometheus + CloudWatch clients |
| **Topology Collection** | ✅ Complete | K8s + CloudFormation clients |
| **ML Training** | ✅ Complete | Pipeline + Registry |
| **Function Library** | ✅ Complete | 25+ functions |
| **Backtest** | ✅ Complete | Real R², MAPE, RMSE |
| **SSE Streaming** | ✅ Complete | No artificial delays |
| **Data Transparency** | ✅ Complete | Source badges, quality metrics |
| **Documentation** | ✅ Complete | This guide |

### What We Don't Provide

- ❌ Monitoring agents (you run Prometheus/K8s)
- ❌ Prediction timeline UI (removed - redundant)
- ❌ Scenario templates (use manual input)
- ❌ Batch simulation (use single runs)

### Design Principles

1. **Client Libraries**: Connect to your existing infrastructure
2. **Two Modes**: DB (fast) vs Real-Time (fresh)
3. **Data Transparency**: Always show data source
4. **No Fake Delays**: Real computation timing
5. **3-Tier Fallback**: Tool → DB → Topology

---

## Quick Reference

### Standard KPIs

| KPI | Unit | Description |
|------|------|-------------|
| `latency_ms` | ms | Response time |
| `throughput_rps` | rps | Requests per second |
| `error_rate_pct` | % | Error percentage |
| `cost_usd_hour` | USD/hour | Hourly cost |

### Strategy Comparison

| Strategy | Speed | Accuracy | Use When |
|----------|--------|----------|----------|
| Rule | ⚡⚡⚡ | 🟡🟡 | Quick estimate |
| Stat | ⚡⚡ | 🟢 | Trend analysis |
| ML | ⚡ | 🟢🟢 | With trained model |
| DL | ⚡ | 🟢🟢 | With trained model |

---

*Last Updated: 2026-02-12*
