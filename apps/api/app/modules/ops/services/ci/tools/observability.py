from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ToolExecutionTrace:
    tool_type: str
    operation: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    success: bool = False
    error: Optional[str] = None
    cache_hit: bool = False
    input_params: Dict[str, Any] = field(default_factory=dict)
    result_size_bytes: int = 0
    result_count: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    fallback_used: bool = False


class ExecutionTracer:
    def __init__(self):
        self.traces: List[ToolExecutionTrace] = []
        self._start_times: Dict[str, datetime] = {}
        self._trace_info: Dict[str, Dict[str, Any]] = {}

    def start_trace(self, tool_type: str, operation: str, params: Dict[str, Any]) -> str:
        trace_id = f"{tool_type}_{operation}_{int(time.time() * 1000)}"
        self._start_times[trace_id] = datetime.now()
        self._trace_info[trace_id] = {
            "tool_type": tool_type,
            "operation": operation,
            "params": params,
        }
        return trace_id

    def end_trace(
        self,
        trace_id: str,
        success: bool,
        error: Optional[str] = None,
        result_size: int = 0,
        result_count: Optional[int] = None,
        cache_hit: bool = False,
        **metadata: Any,
    ):
        start_time = self._start_times.pop(trace_id, None)
        info = self._trace_info.pop(trace_id, {})
        if not start_time:
            return
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() * 1000
        trace = ToolExecutionTrace(
            tool_type=info.get("tool_type", "unknown"),
            operation=info.get("operation", "unknown"),
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration,
            success=success,
            error=error,
            cache_hit=cache_hit,
            input_params=info.get("params", {}),
            result_size_bytes=result_size,
            result_count=result_count,
            metadata=metadata,
        )
        self.traces.append(trace)

    def get_performance_stats(self) -> Dict[str, Any]:
        if not self.traces:
            return {}
        stats: Dict[str, Dict[str, Any]] = {}
        for trace in self.traces:
            key = f"{trace.tool_type}/{trace.operation}"
            bucket = stats.setdefault(
                key,
                {
                    "count": 0,
                    "success": 0,
                    "error": 0,
                    "total_time_ms": 0.0,
                    "cache_hits": 0,
                },
            )
            bucket["count"] += 1
            bucket["total_time_ms"] += trace.duration_ms
            if trace.success:
                bucket["success"] += 1
            else:
                bucket["error"] += 1
            if trace.cache_hit:
                bucket["cache_hits"] += 1

        for bucket in stats.values():
            bucket["avg_time_ms"] = bucket["total_time_ms"] / bucket["count"]
            bucket["cache_hit_rate"] = bucket["cache_hits"] / bucket["count"]
        return stats

    def export_traces(self, format: str = "json") -> str:
        if format == "json":
            return json.dumps([asdict(trace) for trace in self.traces], default=str)
        if format == "csv":
            lines = []
            header = [
                "tool_type",
                "operation",
                "start_time",
                "end_time",
                "duration_ms",
                "success",
                "error",
                "cache_hit",
                "result_size_bytes",
                "result_count",
            ]
            lines.append(",".join(header))
            for trace in self.traces:
                lines.append(
                    ",".join(
                        str(getattr(trace, field)) if getattr(trace, field) is not None else ""
                        for field in header
                    )
                )
            return "\n".join(lines)
        raise ValueError(f"Unknown format: {format}")
