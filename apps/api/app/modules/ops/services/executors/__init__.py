"""
OPS Executors Package
Provides data source executors for Config, Metric, History, and Graph modes.
"""

from .config_executor import (
    run_config,
    run_metric,
    run_hist,
    run_graph,
    ExecutorResult,
)

__all__ = [
    "run_config",
    "run_metric",
    "run_hist",
    "run_graph",
    "ExecutorResult",
]
