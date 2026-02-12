"""
Metric Collector for Simulation System

**IMPORTANT**: This is NOT a data collection agent!

This module provides CLIENT CODE to connect to EXISTING monitoring systems:

- Prometheus (user's existing Prometheus server)
- AWS CloudWatch (user's existing AWS account)
- Datadog (optional)

Users must already have these monitoring systems running.
This code only fetches data from them via their APIs.

For actual data collection agents, see:
- Prometheus exporters (node_exporter, blackbox_exporter, etc.)
- CloudWatch agents (Amazon CloudWatch Agent)
- Kubernetes metrics server
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field

from core.config import get_settings
from core.db import get_session_context

logger = logging.getLogger(__name__)


class MetricPoint(BaseModel):
    """Single metric data point"""
    timestamp: datetime
    value: float
    labels: dict[str, str] = Field(default_factory=dict)


class MetricSeries(BaseModel):
    """Time series of metric data"""
    metric_name: str
    service: str
    unit: str
    points: list[MetricPoint] = Field(default_factory=list)


class MetricCollectorConfig(BaseModel):
    """Configuration for metric collection"""
    prometheus_url: Optional[str] = None
    prometheus_token: Optional[str] = None
    cloudwatch_region: Optional[str] = None
    cloudwatch_access_key: Optional[str] = None
    cloudwatch_secret_key: Optional[str] = None
    datadog_api_key: Optional[str] = None
    datadog_app_key: Optional[str] = None
    datadog_site: str = "datadoghq.com"


class BaseMetricCollector(ABC):
    """Abstract base class for metric collectors"""

    @abstractmethod
    async def collect(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime,
        step_seconds: int = 60,
    ) -> list[MetricSeries]:
        """Collect metrics within time range"""
        pass


class PrometheusCollector(BaseMetricCollector):
    """Collect metrics from Prometheus"""

    def __init__(self, url: str, token: Optional[str] = None):
        self.url = url.rstrip("/")
        self.token = token
        self.headers = {}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    async def collect(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime,
        step_seconds: int = 60,
    ) -> list[MetricSeries]:
        """
        Collect metrics using Prometheus range query API.

        Args:
            query: PromQL query (e.g., 'rate(http_requests_total[5m])')
            start_time: Start timestamp
            end_time: End timestamp
            step_seconds: Resolution in seconds

        Returns:
            List of MetricSeries
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "query": query,
                "start": int(start_time.timestamp()),
                "end": int(end_time.timestamp()),
                "step": f"{step_seconds}s",
            }

            response = await client.get(
                f"{self.url}/api/v1/query_range",
                params=params,
                headers=self.headers,
            )
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "success":
            logger.error(f"Prometheus query failed: {data}")
            return []

        result_data = data.get("data", {}).get("result", [])
        return self._parse_prometheus_result(result_data)

    def _parse_prometheus_result(
        self, result_data: list[dict]
    ) -> list[MetricSeries]:
        """Parse Prometheus API response into MetricSeries"""
        series_list = []

        for item in result_data:
            metric = item.get("metric", {})
            values = item.get("values", [])

            metric_name = metric.get("__name__", "unknown")
            service = metric.get("service", metric.get("job", "unknown"))

            # Determine unit from metric name
            unit = self._infer_unit(metric_name)

            points = []
            for ts, val in values:
                points.append(MetricPoint(
                    timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
                    value=float(val),
                    labels={k: v for k, v in metric.items() if not k.startswith("__")},
                ))

            series_list.append(MetricSeries(
                metric_name=metric_name,
                service=service,
                unit=unit,
                points=points,
            ))

        return series_list

    def _infer_unit(self, metric_name: str) -> str:
        """Infer unit from metric name"""
        name_lower = metric_name.lower()
        if "latency" in name_lower or "duration" in name_lower or "seconds" in name_lower:
            return "ms"
        elif "requests" in name_lower or "rps" in name_lower or "throughput" in name_lower:
            return "rps"
        elif "error" in name_lower or "failures" in name_lower:
            return "pct"
        elif "cost" in name_lower or "dollars" in name_lower:
            return "usd"
        elif "cpu" in name_lower or "memory" in name_lower:
            return "pct"
        return "unknown"


class CloudWatchCollector(BaseMetricCollector):
    """Collect metrics from AWS CloudWatch"""

    def __init__(
        self,
        region: str,
        access_key: str,
        secret_key: str,
    ):
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self._client = None

    @property
    def client(self):
        """Lazy initialization of CloudWatch client"""
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    "cloudwatch",
                    region_name=self.region,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                )
            except ImportError:
                logger.warning("boto3 not installed. CloudWatch collection unavailable.")
        return self._client

    async def collect(
        self,
        query: str,
        start_time: datetime,
        end_time: datetime,
        step_seconds: int = 60,
    ) -> list[MetricSeries]:
        """
        Collect metrics using CloudWatch GetMetricStatistics API.

        Args:
            query: JSON string with namespace, metric_name, dimensions
                   e.g., '{"namespace": "AWS/EC2", "metric_name": "CPUUtilization", "dimensions": {"InstanceId": "i-xxx"}}'
            start_time: Start timestamp
            end_time: End timestamp
            step_seconds: Resolution (period) in seconds

        Returns:
            List of MetricSeries
        """
        if not self.client:
            logger.warning("CloudWatch client not available")
            return []

        try:
            query_data = json.loads(query)
        except json.JSONDecodeError:
            logger.error(f"Invalid CloudWatch query JSON: {query}")
            return []

        namespace = query_data.get("namespace", "")
        metric_name = query_data.get("metric_name", "")
        dimensions = query_data.get("dimensions", {})

        # Build dimension list
        dimension_list = [{"Name": k, "Value": v} for k, v in dimensions.items()]

        try:
            response = self.client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimension_list,
                StartTime=start_time,
                EndTime=end_time,
                Period=step_seconds,
                Statistics=["Average", "Maximum", "Minimum"],
            )

            datapoints = response.get("Datapoints", [])
            if not datapoints:
                return []

            # Convert to MetricSeries
            points = []
            for dp in datapoints:
                points.append(MetricPoint(
                    timestamp=dp["Timestamp"].replace(tzinfo=timezone.utc),
                    value=dp.get("Average", 0),
                    labels={
                        "unit": dp.get("Unit", ""),
                        "max": str(dp.get("Maximum", 0)),
                        "min": str(dp.get("Minimum", 0)),
                    },
                ))

            # Sort by timestamp
            points.sort(key=lambda p: p.timestamp)

            return [MetricSeries(
                metric_name=metric_name,
                service=dimensions.get("Service", dimensions.get("InstanceId", "unknown")),
                unit=self._infer_cloudwatch_unit(metric_name),
                points=points,
            )]

        except Exception as e:
            logger.error(f"CloudWatch query failed: {e}")
            return []

    def _infer_cloudwatch_unit(self, metric_name: str) -> str:
        """Infer unit from CloudWatch metric name"""
        name_lower = metric_name.lower()
        if "latency" in name_lower or "duration" in name_lower:
            return "ms"
        elif "request" in name_lower or "count" in name_lower:
            return "count"
        elif "cpu" in name_lower or "utilization" in name_lower:
            return "pct"
        elif "memory" in name_lower:
            return "bytes"
        return "unknown"


class MetricCollector:
    """
    Unified Metric Collector

    Two modes of operation:

    1. **Batch Collection (Scheduled)**: Collect and store in DB
       - Use: collect_and_save()
       - Run: Periodically (hourly/daily)
       - Benefit: Fast simulation, historical analysis

    2. **Real-Time Collection (On-Demand)**: Fetch directly for simulation
       - Use: from_prometheus() / from_cloudwatch() directly
       - Run: When user requests simulation
       - Benefit: Always fresh data, no storage needed

    Recommendation:
    - Use **Batch Collection** for production stability
    - Use **Real-Time** for ad-hoc analysis or testing
    """

    def __init__(self, config: Optional[MetricCollectorConfig] = None):
        self.config = config or MetricCollectorConfig()
        self._prometheus: Optional[PrometheusCollector] = None
        self._cloudwatch: Optional[CloudWatchCollector] = None

    @property
    def prometheus(self) -> Optional[PrometheusCollector]:
        """Lazy initialization of Prometheus collector"""
        if self._prometheus is None and self.config.prometheus_url:
            self._prometheus = PrometheusCollector(
                url=self.config.prometheus_url,
                token=self.config.prometheus_token,
            )
        return self._prometheus

    @property
    def cloudwatch(self) -> Optional[CloudWatchCollector]:
        """Lazy initialization of CloudWatch collector"""
        if self._cloudwatch is None and self.config.cloudwatch_region:
            self._cloudwatch = CloudWatchCollector(
                region=self.config.cloudwatch_region,
                access_key=self.config.cloudwatch_access_key or "",
                secret_key=self.config.cloudwatch_secret_key or "",
            )
        return self._cloudwatch

    async def from_prometheus(
        self,
        query: str,
        hours_back: int = 24,
        step_seconds: int = 60,
    ) -> list[MetricSeries]:
        """
        Collect metrics from Prometheus.

        Args:
            query: PromQL query
            hours_back: Hours of historical data to collect
            step_seconds: Resolution in seconds

        Returns:
            List of MetricSeries
        """
        if not self.prometheus:
            logger.warning("Prometheus not configured")
            return []

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)

        return await self.prometheus.collect(
            query=query,
            start_time=start_time,
            end_time=end_time,
            step_seconds=step_seconds,
        )

    async def from_cloudwatch(
        self,
        namespace: str,
        metric_name: str,
        dimensions: dict[str, str],
        hours_back: int = 24,
        step_seconds: int = 60,
    ) -> list[MetricSeries]:
        """
        Collect metrics from CloudWatch.

        Args:
            namespace: CloudWatch namespace (e.g., "AWS/EC2")
            metric_name: Metric name (e.g., "CPUUtilization")
            dimensions: Dimensions dict (e.g., {"InstanceId": "i-xxx"})
            hours_back: Hours of historical data to collect
            step_seconds: Resolution (period) in seconds

        Returns:
            List of MetricSeries
        """
        if not self.cloudwatch:
            logger.warning("CloudWatch not configured")
            return []

        query = json.dumps({
            "namespace": namespace,
            "metric_name": metric_name,
            "dimensions": dimensions,
        })

        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)

        return await self.cloudwatch.collect(
            query=query,
            start_time=start_time,
            end_time=end_time,
            step_seconds=step_seconds,
        )

    def save_to_db(
        self,
        tenant_id: str,
        metrics: list[MetricSeries],
    ) -> int:
        """
        Save collected metrics to PostgreSQL.

        Args:
            tenant_id: Tenant identifier
            metrics: List of MetricSeries to save

        Returns:
            Number of records saved
        """
        from app.modules.simulation.services.simulation.metric_models import TbMetricTimeseries

        saved_count = 0

        with get_session_context() as session:
            for series in metrics:
                for point in series.points:
                    record = TbMetricTimeseries(
                        tenant_id=tenant_id,
                        service=series.service,
                        metric_name=series.metric_name,
                        timestamp=point.timestamp,
                        value=point.value,
                        unit=series.unit,
                        labels=point.labels,
                    )
                    session.add(record)
                    saved_count += 1

            session.commit()

        logger.info(f"Saved {saved_count} metric records for tenant {tenant_id}")
        return saved_count

    async def collect_and_save(
        self,
        tenant_id: str,
        source: str,
        query: str,
        hours_back: int = 24,
        step_seconds: int = 60,
    ) -> dict[str, Any]:
        """
        **BATCH MODE**: Collect metrics from source and save to database.

        Use this for:
        - Scheduled data collection (hourly/daily)
        - Building historical dataset
        - Offline simulation (no external API dependency)

        Args:
            tenant_id: Tenant identifier
            source: Source type ("prometheus" or "cloudwatch")
            query: Query string (PromQL or JSON for CloudWatch)
            hours_back: Hours of historical data
            step_seconds: Resolution in seconds

        Returns:
            Summary dict with collection stats
        """
        if source == "prometheus":
            metrics = await self.from_prometheus(
                query=query,
                hours_back=hours_back,
                step_seconds=step_seconds,
            )
        elif source == "cloudwatch":
            # Parse JSON query for CloudWatch
            try:
                query_data = json.loads(query)
                metrics = await self.from_cloudwatch(
                    namespace=query_data.get("namespace", ""),
                    metric_name=query_data.get("metric_name", ""),
                    dimensions=query_data.get("dimensions", {}),
                    hours_back=hours_back,
                    step_seconds=step_seconds,
                )
            except json.JSONDecodeError:
                return {"error": "Invalid JSON query for CloudWatch"}
        else:
            return {"error": f"Unknown source: {source}"}

        if not metrics:
            return {"error": "No metrics collected", "source": source}

        # Save to database
        saved_count = self.save_to_db(tenant_id=tenant_id, metrics=metrics)

        return {
            "mode": "batch",
            "source": source,
            "series_count": len(metrics),
            "points_count": sum(len(s.points) for s in metrics),
            "saved_count": saved_count,
            "services": list(set(s.service for s in metrics)),
            "metrics": list(set(s.metric_name for s in metrics)),
        }

    async def fetch_realtime(
        self,
        source: str,
        query: str,
        hours_back: int = 1,
        step_seconds: int = 60,
    ) -> dict[str, Any]:
        """
        **REAL-TIME MODE**: Fetch metrics directly without saving.

        Use this for:
        - On-demand simulation with latest data
        - Ad-hoc analysis
        - Testing without database

        Args:
            source: Source type ("prometheus" or "cloudwatch")
            query: Query string (PromQL or JSON for CloudWatch)
            hours_back: Hours of historical data (default: 1 for real-time)
            step_seconds: Resolution in seconds

        Returns:
            Metrics directly (not saved to DB)
        """
        if source == "prometheus":
            if not self.prometheus:
                return {"error": "Prometheus not configured"}
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours_back)
            metrics = await self.prometheus.collect(
                query=query,
                start_time=start_time,
                end_time=end_time,
                step_seconds=step_seconds,
            )
        elif source == "cloudwatch":
            if not self.cloudwatch:
                return {"error": "CloudWatch not configured"}
            try:
                query_data = json.loads(query)
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(hours=hours_back)
                metrics = await self.cloudwatch.collect(
                    query=query,
                    start_time=start_time,
                    end_time=end_time,
                    step_seconds=step_seconds,
                )
            except json.JSONDecodeError:
                return {"error": "Invalid JSON query for CloudWatch"}
        else:
            return {"error": f"Unknown source: {source}"}

        if not metrics:
            return {"error": "No metrics collected", "source": source}

        # Convert to dict format (for direct use in simulation)
        metrics_dict = {}
        for series in metrics:
            key = f"{series.service}:{series.metric_name}"
            if series.points:
                latest_value = series.points[-1].value
                metrics_dict[key] = {
                    "value": latest_value,
                    "unit": series.unit,
                    "timestamp": series.points[-1].timestamp.isoformat(),
                    "history_count": len(series.points),
                }

        return {
            "mode": "realtime",
            "source": source,
            "series_count": len(metrics),
            "metrics": metrics_dict,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }


# Standard Prometheus queries for simulation metrics
STANDARD_PROMETHEUS_QUERIES = {
    "latency_ms": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m])) * 1000",
    "throughput_rps": "sum(rate(http_requests_total[5m]))",
    "error_rate_pct": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m])) * 100",
    "cpu_utilization_pct": "avg(rate(process_cpu_seconds_total[5m])) * 100",
    "memory_utilization_pct": "avg(process_resident_memory_bytes) / 1024 / 1024 / 1024 * 100",
}


async def collect_standard_metrics(
    tenant_id: str,
    prometheus_url: str,
    prometheus_token: Optional[str] = None,
    hours_back: int = 24,
) -> dict[str, Any]:
    """
    Collect standard simulation metrics from Prometheus.

    Args:
        tenant_id: Tenant identifier
        prometheus_url: Prometheus server URL
        prometheus_token: Optional auth token
        hours_back: Hours of historical data

    Returns:
        Collection summary
    """
    config = MetricCollectorConfig(
        prometheus_url=prometheus_url,
        prometheus_token=prometheus_token,
    )
    collector = MetricCollector(config)

    results = {}
    for metric_name, query in STANDARD_PROMETHEUS_QUERIES.items():
        try:
            result = await collector.collect_and_save(
                tenant_id=tenant_id,
                source="prometheus",
                query=query,
                hours_back=hours_back,
            )
            results[metric_name] = result
        except Exception as e:
            logger.error(f"Failed to collect {metric_name}: {e}")
            results[metric_name] = {"error": str(e)}

    return results
