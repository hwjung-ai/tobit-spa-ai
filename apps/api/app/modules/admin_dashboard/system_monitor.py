"""Admin dashboard system monitoring and health service"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil

logger = logging.getLogger(__name__)


class DatabaseMetric:
    """Database connection and performance metrics"""

    def __init__(
        self,
        connection_count: int,
        pool_size: int,
        query_time_ms_avg: float,
        slow_queries: int,
        error_count: int,
    ):
        self.connection_count = connection_count
        self.pool_size = pool_size
        self.query_time_ms_avg = query_time_ms_avg
        self.slow_queries = slow_queries
        self.error_count = error_count
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "connection_count": self.connection_count,
            "pool_size": self.pool_size,
            "query_time_ms_avg": self.query_time_ms_avg,
            "slow_queries": self.slow_queries,
            "error_count": self.error_count,
            "timestamp": self.timestamp.isoformat(),
        }


class APIMetric:
    """API performance metrics"""

    def __init__(
        self,
        total_requests: int,
        total_errors: int,
        avg_response_time_ms: float,
        p95_response_time_ms: float,
        p99_response_time_ms: float,
    ):
        self.total_requests = total_requests
        self.total_errors = total_errors
        self.avg_response_time_ms = avg_response_time_ms
        self.p95_response_time_ms = p95_response_time_ms
        self.p99_response_time_ms = p99_response_time_ms
        self.timestamp = datetime.utcnow()
        self.error_rate = (total_errors / total_requests) if total_requests > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": self.error_rate,
            "avg_response_time_ms": self.avg_response_time_ms,
            "p95_response_time_ms": self.p95_response_time_ms,
            "p99_response_time_ms": self.p99_response_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class ResourceMetric:
    """System resource metrics (CPU, Memory, Disk)"""

    def __init__(
        self,
        cpu_percent: float,
        memory_percent: float,
        memory_available_gb: float,
        disk_percent: float,
        disk_available_gb: float,
    ):
        self.cpu_percent = cpu_percent
        self.memory_percent = memory_percent
        self.memory_available_gb = memory_available_gb
        self.disk_percent = disk_percent
        self.disk_available_gb = disk_available_gb
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_available_gb": self.memory_available_gb,
            "disk_percent": self.disk_percent,
            "disk_available_gb": self.disk_available_gb,
            "timestamp": self.timestamp.isoformat(),
        }


class SystemMonitor:
    """Monitor system health and resources"""

    def __init__(self):
        self.resource_metrics: List[ResourceMetric] = []
        self.api_metrics: List[APIMetric] = []
        self.database_metrics: List[DatabaseMetric] = []
        self.alerts: List[Dict[str, Any]] = []
        self.max_metrics_history = 288  # 24 hours at 5-minute intervals

    def collect_resource_metrics(self) -> ResourceMetric:
        """Collect current system resource metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory_info = psutil.virtual_memory()
            memory_percent = memory_info.percent
            memory_available_gb = memory_info.available / (1024**3)

            # Disk usage
            disk_info = psutil.disk_usage("/")
            disk_percent = disk_info.percent
            disk_available_gb = disk_info.free / (1024**3)

            metric = ResourceMetric(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_gb=memory_available_gb,
                disk_percent=disk_percent,
                disk_available_gb=disk_available_gb,
            )

            # Store metric
            self.resource_metrics.append(metric)

            # Keep only recent metrics
            if len(self.resource_metrics) > self.max_metrics_history:
                self.resource_metrics = self.resource_metrics[-self.max_metrics_history :]

            # Check for alerts
            self._check_resource_alerts(metric)

            return metric

        except Exception as e:
            logger.error(f"Failed to collect resource metrics: {str(e)}")
            return None

    def _check_resource_alerts(self, metric: ResourceMetric) -> None:
        """Check for resource usage alerts"""
        alerts = []

        if metric.cpu_percent > 90:
            alerts.append({
                "type": "cpu_high",
                "severity": "critical",
                "message": f"CPU usage is high: {metric.cpu_percent}%",
                "value": metric.cpu_percent,
            })

        if metric.memory_percent > 85:
            alerts.append({
                "type": "memory_high",
                "severity": "critical",
                "message": f"Memory usage is high: {metric.memory_percent}%",
                "value": metric.memory_percent,
            })

        if metric.disk_percent > 90:
            alerts.append({
                "type": "disk_high",
                "severity": "warning",
                "message": f"Disk usage is high: {metric.disk_percent}%",
                "value": metric.disk_percent,
            })

        for alert in alerts:
            alert["timestamp"] = datetime.utcnow().isoformat()
            self.alerts.append(alert)
            logger.warning(f"Alert: {alert['message']}")

        # Keep only recent alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]

    def record_api_metrics(
        self,
        total_requests: int,
        total_errors: int,
        avg_response_time_ms: float,
        p95_response_time_ms: float,
        p99_response_time_ms: float,
    ) -> APIMetric:
        """Record API performance metrics"""
        metric = APIMetric(
            total_requests=total_requests,
            total_errors=total_errors,
            avg_response_time_ms=avg_response_time_ms,
            p95_response_time_ms=p95_response_time_ms,
            p99_response_time_ms=p99_response_time_ms,
        )

        self.api_metrics.append(metric)

        # Keep only recent metrics
        if len(self.api_metrics) > self.max_metrics_history:
            self.api_metrics = self.api_metrics[-self.max_metrics_history :]

        # Check for alerts
        if metric.error_rate > 0.05:  # More than 5% error rate
            self.alerts.append({
                "type": "api_error_rate_high",
                "severity": "warning",
                "message": f"API error rate is high: {metric.error_rate * 100:.2f}%",
                "value": metric.error_rate,
                "timestamp": datetime.utcnow().isoformat(),
            })

        if metric.p99_response_time_ms > 5000:  # More than 5 seconds
            self.alerts.append({
                "type": "api_slow_response",
                "severity": "warning",
                "message": f"API p99 response time is slow: {metric.p99_response_time_ms}ms",
                "value": metric.p99_response_time_ms,
                "timestamp": datetime.utcnow().isoformat(),
            })

        return metric

    def record_database_metrics(
        self,
        connection_count: int,
        pool_size: int,
        query_time_ms_avg: float,
        slow_queries: int,
        error_count: int,
    ) -> DatabaseMetric:
        """Record database metrics"""
        metric = DatabaseMetric(
            connection_count=connection_count,
            pool_size=pool_size,
            query_time_ms_avg=query_time_ms_avg,
            slow_queries=slow_queries,
            error_count=error_count,
        )

        self.database_metrics.append(metric)

        # Keep only recent metrics
        if len(self.database_metrics) > self.max_metrics_history:
            self.database_metrics = self.database_metrics[-self.max_metrics_history :]

        # Check for alerts
        if connection_count >= pool_size * 0.9:  # 90% of pool
            self.alerts.append({
                "type": "database_connection_pool_high",
                "severity": "warning",
                "message": f"Database connection pool is high: {connection_count}/{pool_size}",
                "value": connection_count,
                "timestamp": datetime.utcnow().isoformat(),
            })

        if slow_queries > 10:
            self.alerts.append({
                "type": "database_slow_queries",
                "severity": "warning",
                "message": f"High number of slow queries: {slow_queries}",
                "value": slow_queries,
                "timestamp": datetime.utcnow().isoformat(),
            })

        return metric

    def get_current_status(self) -> Dict[str, Any]:
        """Get current system status"""
        latest_resource = self.resource_metrics[-1] if self.resource_metrics else None
        latest_api = self.api_metrics[-1] if self.api_metrics else None
        latest_database = self.database_metrics[-1] if self.database_metrics else None

        # Determine overall health
        status = "healthy"
        if latest_resource:
            if latest_resource.cpu_percent > 90 or latest_resource.memory_percent > 85:
                status = "critical"
            elif latest_resource.cpu_percent > 75 or latest_resource.memory_percent > 75:
                status = "warning"

        if latest_api and latest_api.error_rate > 0.05:
            status = "warning" if status == "healthy" else status

        recent_critical_alerts = sum(
            1 for a in self.alerts
            if a.get("severity") == "critical"
            and datetime.fromisoformat(a.get("timestamp", "1970-01-01T00:00:00"))
            > datetime.utcnow() - __import__("datetime").timedelta(hours=1)
        )

        if recent_critical_alerts > 0:
            status = "critical"

        return {
            "status": status,
            "resource": latest_resource.to_dict() if latest_resource else None,
            "api": latest_api.to_dict() if latest_api else None,
            "database": latest_database.to_dict() if latest_database else None,
            "recent_alerts_count": len([a for a in self.alerts if a.get("timestamp") > (datetime.utcnow() - __import__("datetime").timedelta(hours=1)).isoformat()]),
        }

    def get_alerts(
        self,
        severity: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get recent alerts"""
        alerts = self.alerts

        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]

        # Sort by timestamp (newest first)
        alerts.sort(
            key=lambda a: datetime.fromisoformat(a.get("timestamp", "1970-01-01T00:00:00")),
            reverse=True,
        )

        return alerts[:limit]

    def get_metrics_history(self, limit: int = 288) -> Dict[str, Any]:
        """Get historical metrics"""
        return {
            "resources": [m.to_dict() for m in self.resource_metrics[-limit:]],
            "api": [m.to_dict() for m in self.api_metrics[-limit:]],
            "database": [m.to_dict() for m in self.database_metrics[-limit:]],
        }
