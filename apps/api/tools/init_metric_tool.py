#!/usr/bin/env python3
"""
Initialize Metric Timeseries Tool Asset for Simulation

This script registers a Metric Timeseries Query Tool as an Asset in Asset Registry,
allowing Simulation to use metric data via DynamicTool with SQL query type.

Usage:
    python tools/init_metric_tool.py

Environment Variables:
    DATABASE_URL: SQLAlchemy database URL
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.modules.asset_registry.crud import create_tool_asset, publish_asset
from app.modules.asset_registry.models import TbAssetRegistry
from core.db import engine
from sqlmodel import Session

# SQL Query for metric timeseries aggregation
METRIC_QUERY_SQL = """
-- Metric Timeseries Aggregation for Simulation Baseline
-- Returns aggregated KPI values for a service within a time window
WITH metric_filter AS (
    SELECT
        metric_name,
        value,
        unit,
        timestamp
    FROM tb_metric_timeseries
    WHERE tenant_id = :tenant_id
        AND service = :service
        AND metric_name = ANY(:metric_names)
        AND timestamp >= :since
)
SELECT
    metric_name,
    AVG(value) as mean_value,
    MIN(value) as min_value,
    MAX(value) as max_value,
    STDDEV(value) as stddev_value,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) as median_value,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY value) as p95_value,
    COUNT(*) as data_points,
    MAX(unit) as unit
FROM metric_filter
GROUP BY metric_name
ORDER BY metric_name;
"""

METRIC_TOOL_CONFIG = {
    "name": "sim_metric_timeseries_query",
    "description": "Query metric timeseries data from PostgreSQL for simulation baseline and backtesting",
    "tool_type": "sql_query",
    "tool_catalog_ref": "default_postgres",
    "query_sql": METRIC_QUERY_SQL.strip(),
    "query_params": {
        "tenant_id": {
            "type": "string",
            "description": "Tenant identifier",
            "required": True
        },
        "service": {
            "type": "string",
            "description": "Service name (e.g., api-gateway, order-service)",
            "required": True
        },
        "metric_names": {
            "type": "array",
            "description": "List of metric names to query",
            "required": False,
            "default": ["latency_ms", "throughput_rps", "error_rate_pct", "cost_usd_hour"]
        },
        "since": {
            "type": "string",
            "format": "date-time",
            "description": "ISO 8601 timestamp for time window start",
            "required": False
        }
    },
    "query_metadata": {
        "timeout_seconds": 30,
        "max_rows": 10000,
        "requires_connection": "default_postgres"
    },
    "tags": {
        "category": "simulation",
        "version": "1.0",
        "module": "metric_timeseries",
        "data_source": "postgresql"
    }
}


def init_metric_tool(session: Session):
    """
    Initialize Metric Timeseries Tool Asset

    Args:
        session: Database session
    """

    print("Initializing Metric Timeseries Tool Asset...")
    print(f"  Tool Name: {METRIC_TOOL_CONFIG['name']}")
    print(f"  Tool Type: {METRIC_TOOL_CONFIG['tool_type']}")
    print(f"  Catalog: {METRIC_TOOL_CONFIG['tool_catalog_ref']}")

    try:
        # Check if tool already exists
        from sqlalchemy import select
        stmt = select(TbAssetRegistry).where(
            (TbAssetRegistry.name == "sim_metric_timeseries_query") &
            (TbAssetRegistry.asset_type == "tool")
        )
        existing = session.exec(stmt).first()

        if existing:
            print(f"\n⚠️  Metric Tool already exists (ID: {existing.asset_id})")
            print(f"   Status: {existing.status}")
            return existing

        # Build input schema from query params
        input_schema = {
            "type": "object",
            "properties": {
                "tenant_id": {
                    "type": "string",
                    "description": "Tenant identifier"
                },
                "service": {
                    "type": "string",
                    "description": "Service name (e.g., api-gateway, order-service)"
                },
                "metric_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of metric names to query",
                    "default": ["latency_ms", "throughput_rps", "error_rate_pct", "cost_usd_hour"]
                },
                "since": {
                    "type": "string",
                    "format": "date-time",
                    "description": "ISO 8601 timestamp for time window start"
                }
            },
            "required": ["tenant_id", "service"]
        }

        # Output schema for aggregated metrics
        output_schema = {
            "type": "object",
            "properties": {
                "metrics": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "metric_name": {"type": "string"},
                            "mean_value": {"type": "number"},
                            "min_value": {"type": "number"},
                            "max_value": {"type": "number"},
                            "stddev_value": {"type": "number"},
                            "median_value": {"type": "number"},
                            "p95_value": {"type": "number"},
                            "data_points": {"type": "integer"},
                            "unit": {"type": "string"}
                        }
                    }
                },
                "execution_time_ms": {
                    "type": "integer",
                    "description": "Query execution time in milliseconds"
                },
                "row_count": {
                    "type": "integer",
                    "description": "Total rows processed"
                }
            }
        }

        # Create tool asset
        tool_asset = create_tool_asset(
            session=session,
            name=METRIC_TOOL_CONFIG["name"],
            description=METRIC_TOOL_CONFIG["description"],
            tool_type=METRIC_TOOL_CONFIG["tool_type"],
            tool_catalog_ref=METRIC_TOOL_CONFIG["tool_catalog_ref"],
            tool_config={
                "query_sql": METRIC_TOOL_CONFIG["query_sql"],
                "query_params": METRIC_TOOL_CONFIG["query_params"],
                "query_metadata": METRIC_TOOL_CONFIG["query_metadata"]
            },
            tool_input_schema=input_schema,
            tool_output_schema=output_schema,
            tags=METRIC_TOOL_CONFIG["tags"],
            created_by="system",
        )

        print(f"\n✅ Tool Asset created: {tool_asset.asset_id}")
        print(f"   Name: {tool_asset.name}")
        print(f"   Status: {tool_asset.status}")

        # Publish tool asset
        published_asset = publish_asset(
            session=session,
            asset=tool_asset,
            published_by="system",
        )

        print("\n✅ Tool Asset published")
        print(f"   Version: {published_asset.version}")
        print(f"   Status: {published_asset.status}")
        print(f"   Published At: {published_asset.published_at}")

        # Display usage information
        print("\n" + "="*70)
        print("METRIC TIMESERIES TOOL REGISTERED SUCCESSFULLY")
        print("="*70)
        print(f"\nTool Asset ID: {published_asset.asset_id}")
        print(f"Tool Name: {published_asset.name}")
        print("\nUsage in Simulation:")
        print("  - Tool will be automatically discovered by metric_loader.py")
        print("  - Baseline KPIs will be loaded from PostgreSQL timeseries")
        print("  - Supports aggregations: mean, min, max, stddev, median, p95")
        print("\nQuery Details:")
        print(f"  - Catalog: {METRIC_TOOL_CONFIG['tool_catalog_ref']}")
        print(f"  - Type: {METRIC_TOOL_CONFIG['tool_type']}")
        print(f"  - Timeout: {METRIC_TOOL_CONFIG['query_metadata']['timeout_seconds']}s")
        print(f"  - Max Rows: {METRIC_TOOL_CONFIG['query_metadata']['max_rows']}")
        print("\n" + "="*70)

        return published_asset

    except Exception as e:
        print(f"\n❌ Error creating tool asset: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """Main entry point"""

    print("\n" + "="*70)
    print("METRIC TIMESERIES TOOL INITIALIZATION")
    print("="*70)

    try:
        with Session(engine) as session:
            tool_asset = init_metric_tool(session)
            print("\n✅ Initialization complete!")
            return 0

    except Exception as e:
        print(f"\n❌ Initialization failed: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
