#!/usr/bin/env python3
"""
Register System Monitoring and CEP Monitoring screens to Asset Registry
"""

import sys
from pathlib import Path
from datetime import datetime

# Add apps/api to Python path
API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from core.db import get_session_context
from core.logging import get_logger
from app.modules.asset_registry.models import TbAssetRegistry, TbAssetVersionHistory

logger = get_logger(__name__)

# System Monitoring Screen Schema
SYSTEM_MONITORING_SCHEMA = {
    "id": "system_monitoring",
    "screen_id": "system_monitoring",
    "name": "System Monitoring",
    "version": "1.0",
    "components": [
        {
            "id": "sys_header",
            "type": "row",
            "label": "Header Row",
            "props": {
                "gap": 4,
                "components": [
                    {
                        "id": "sys_title",
                        "type": "text",
                        "label": "Title",
                        "props": {
                            "text": "System Monitoring",
                            "variant": "heading",
                        },
                        "visibility": {"rule": True},
                        "actions": [],
                    },
                    {
                        "id": "sys_refresh_button",
                        "type": "button",
                        "label": "Refresh",
                        "props": {
                            "text": "Refresh",
                        },
                        "visibility": {"rule": True},
                        "actions": [
                            {
                                "id": "sys_action_refresh",
                                "handler": "list_maintenance_filtered",
                                "payload_template": {
                                    "offset": 0,
                                    "limit": 20,
                                },
                            },
                        ],
                    },
                ],
            },
            "visibility": {"rule": True},
            "actions": [],
        },
        {
            "id": "sys_kpi_row",
            "type": "row",
            "label": "KPI Row",
            "props": {
                "gap": 3,
                "components": [
                    {
                        "id": "sys_kpi_uptime",
                        "type": "keyvalue",
                        "label": "Uptime",
                        "props": {
                            "items": [
                                {"key": "uptime", "value": "{{state.uptime}}"},
                            ],
                        },
                        "visibility": {"rule": True},
                        "actions": [],
                    },
                    {
                        "id": "sys_kpi_requests",
                        "type": "keyvalue",
                        "label": "Requests",
                        "props": {
                            "items": [
                                {"key": "requests", "value": "{{state.requests}}"},
                            ],
                        },
                        "visibility": {"rule": True},
                        "actions": [],
                    },
                    {
                        "id": "sys_kpi_errors",
                        "type": "keyvalue",
                        "label": "Errors",
                        "props": {
                            "items": [
                                {"key": "errors", "value": "{{state.errors}}"},
                            ],
                        },
                        "visibility": {"rule": True},
                        "actions": [],
                    },
                ],
            },
            "visibility": {"rule": True},
            "actions": [],
        },
        {
            "id": "sys_chart",
            "type": "chart",
            "label": "System Metrics Chart",
            "props": {
                "data": "{{state.metric_points}}",
                "x_key": "timestamp",
                "series": [
                    {"data_key": "requests", "color": "#38bdf8", "name": "Requests"},
                    {"data_key": "errors", "color": "#f87171", "name": "Errors"},
                ],
            },
            "visibility": {"rule": True},
            "actions": [],
        },
        {
            "id": "sys_table",
            "type": "table",
            "label": "System Events",
            "props": {
                "rows": "{{state.events}}",
                "columns": [
                    {"field": "id", "header": "ID", "sortable": True},
                    {"field": "type", "header": "Type", "sortable": True},
                    {"field": "level", "header": "Level", "sortable": True},
                    {"field": "message", "header": "Message", "sortable": True},
                    {"field": "timestamp", "header": "Timestamp", "sortable": True},
                ],
                "sortable": True,
                "page_size": 10,
                "auto_refresh": {
                    "enabled": True,
                    "interval_ms": 30000,
                    "action_index": 0,
                    "max_failures": 3,
                    "backoff_ms": 10000,
                },
            },
            "visibility": {"rule": True},
            "actions": [
                {
                    "id": "sys_action_auto_refresh",
                    "handler": "list_maintenance_filtered",
                    "payload_template": {
                        "offset": "{{state.pagination.offset}}",
                        "limit": "{{state.pagination.limit}}",
                    },
                },
            ],
        },
    ],
    "state": {
        "schema": {
            "uptime": {"type": "string"},
            "requests": {"type": "number"},
            "errors": {"type": "number"},
            "metric_points": {"type": "array"},
            "events": {"type": "array"},
            "pagination": {"type": "object"},
        },
        "initial": {
            "uptime": "99.9%",
            "requests": 0,
            "errors": 0,
            "metric_points": [],
            "events": [],
            "pagination": {"offset": 0, "limit": 20, "total": 0},
        },
    },
    "actions": [],
    "bindings": None,
    "layout": {
        "type": "dashboard",
        "direction": "vertical",
        "spacing": 16,
    },
}

# CEP Monitoring Screen Schema
CEP_MONITORING_SCHEMA = {
    "id": "cep_monitoring",
    "screen_id": "cep_monitoring",
    "name": "CEP Monitoring",
    "version": "1.0",
    "components": [
        {
            "id": "cep_header",
            "type": "row",
            "label": "Header Row",
            "props": {
                "gap": 4,
                "components": [
                    {
                        "id": "cep_title",
                        "type": "text",
                        "label": "Title",
                        "props": {
                            "text": "CEP Monitoring",
                            "variant": "heading",
                        },
                        "visibility": {"rule": True},
                        "actions": [],
                    },
                    {
                        "id": "cep_filter_input",
                        "type": "input",
                        "label": "Filter",
                        "props": {
                            "placeholder": "Filter alerts...",
                            "value": "{{state.filter_text}}",
                        },
                        "visibility": {"rule": True},
                        "actions": [],
                    },
                ],
            },
            "visibility": {"rule": True},
            "actions": [],
        },
        {
            "id": "cep_kpi_row",
            "type": "row",
            "label": "KPI Row",
            "props": {
                "gap": 3,
                "components": [
                    {
                        "id": "cep_kpi_total",
                        "type": "keyvalue",
                        "label": "Total Events",
                        "props": {
                            "items": [
                                {"key": "total_events", "value": "{{state.total_events}}"},
                            ],
                        },
                        "visibility": {"rule": True},
                        "actions": [],
                    },
                    {
                        "id": "cep_kpi_events_per_sec",
                        "type": "keyvalue",
                        "label": "Events/sec",
                        "props": {
                            "items": [
                                {"key": "events_per_sec", "value": "{{state.events_per_sec}}"},
                            ],
                        },
                        "visibility": {"rule": True},
                        "actions": [],
                    },
                ],
            },
            "visibility": {"rule": True},
            "actions": [],
        },
        {
            "id": "cep_alerts_chart",
            "type": "chart",
            "label": "Alert Trend",
            "props": {
                "data": "{{state.event_rate_history}}",
                "x_key": "timestamp",
                "series": [
                    {"data_key": "event_rate", "color": "#38bdf8", "name": "Event Rate"},
                ],
            },
            "visibility": {"rule": True},
            "actions": [],
        },
        {
            "id": "cep_alerts_table",
            "type": "table",
            "label": "CEP Alerts",
            "props": {
                "rows": "{{state.cep_alerts}}",
                "columns": [
                    {"field": "id", "header": "ID", "sortable": True},
                    {"field": "type", "header": "Type", "sortable": True},
                    {"field": "severity", "header": "Severity", "sortable": True},
                    {"field": "message", "header": "Message", "sortable": True},
                    {"field": "timestamp", "header": "Timestamp", "sortable": True},
                ],
                "sortable": True,
                "page_size": 10,
            },
            "visibility": {"rule": True},
            "actions": [],
        },
    ],
    "state": {
        "schema": {
            "filter_text": {"type": "string"},
            "total_events": {"type": "number"},
            "events_per_sec": {"type": "number"},
            "event_rate_history": {"type": "array"},
            "cep_alerts": {"type": "array"},
            "avg_latency": {"type": "number"},
            "p99_latency": {"type": "number"},
            "warning_alerts": {"type": "number"},
            "critical_alerts": {"type": "number"},
            "active_patterns": {"type": "number"},
            "pattern_matches": {"type": "number"},
            "event_streams": {"type": "array"},
            "active_patterns_list": {"type": "array"},
            "pattern_matches_history": {"type": "array"},
            "last_refresh": {"type": "string"},
        },
        "initial": {
            "filter_text": "",
            "total_events": 0,
            "events_per_sec": 0,
            "event_rate_history": [],
            "cep_alerts": [],
            "avg_latency": 0,
            "p99_latency": 0,
            "warning_alerts": 0,
            "critical_alerts": 0,
            "active_patterns": 0,
            "pattern_matches": 0,
            "event_streams": [],
            "active_patterns_list": [],
            "pattern_matches_history": [],
            "last_refresh": "",
        },
    },
    "actions": [],
    "bindings": None,
    "layout": {
        "type": "dashboard",
        "direction": "vertical",
        "spacing": 16,
    },
}


def register_screen(screen_id: str, name: str, description: str, schema: dict):
    """Register a screen asset"""
    with get_session_context() as session:
        # Check if screen already exists
        from sqlmodel import select
        existing = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "screen")
            .where(TbAssetRegistry.screen_id == screen_id)
        ).first()

        if existing:
            logger.info(f"✓ Screen '{name}' (screen_id={screen_id}) already exists")
            print(f"✓ Screen '{name}' (screen_id={screen_id}) already exists")
            return existing

        # Create new screen asset
        asset = TbAssetRegistry(
            asset_type="screen",
            screen_id=screen_id,
            name=name,
            description=description,
            schema_json=schema,
            tags=["monitoring", "dashboard"],
            created_by="admin",
            status="draft",
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(asset)
        session.flush()  # Get asset_id without committing yet

        # Create initial version history
        history = TbAssetVersionHistory(
            asset_id=asset.asset_id,
            version=asset.version,
            snapshot={
                "schema_json": asset.schema_json,
                "name": asset.name,
                "description": asset.description,
            },
        )
        session.add(history)
        session.commit()

        logger.info(f"✓ Created screen '{name}' (screen_id={screen_id}, asset_id={asset.asset_id})")
        print(f"✓ Created screen '{name}' (screen_id={screen_id}, asset_id={asset.asset_id})")
        return asset


def main():
    logger.info("=" * 70)
    logger.info("Registering Monitoring Screens to Asset Registry")
    logger.info("=" * 70)

    print("Registering Monitoring Screens to Asset Registry\n")
    print("=" * 60)

    # Register System Monitoring
    sys_monitoring = register_screen(
        screen_id="system_monitoring",
        name="System Monitoring",
        description="System monitoring dashboard with metrics and events",
        schema=SYSTEM_MONITORING_SCHEMA,
    )

    # Register CEP Monitoring
    cep_monitoring = register_screen(
        screen_id="cep_monitoring",
        name="CEP Monitoring",
        description="CEP monitoring dashboard with alerts and patterns",
        schema=CEP_MONITORING_SCHEMA,
    )

    print("=" * 60)
    print("\n✓ All monitoring screens registered successfully!")
    print("\nYou can now view these screens at:")
    print("  - http://localhost:3000/admin/screens")
    
    logger.info("=" * 70)
    logger.info("✓ All monitoring screens registered successfully!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()