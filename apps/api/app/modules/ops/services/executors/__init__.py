"""
OPS Executors Package
Provides data source executors for Config, Metric, History, and Graph modes.
"""

from .config_executor import (
    ExecutorResult,
    run_config,
    run_graph,
    run_hist,
    run_metric,
)

__all__ = [
    "run_config",
    "run_metric",
    "run_hist",
    "run_graph",
    "ExecutorResult",
]
