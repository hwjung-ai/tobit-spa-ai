#!/usr/bin/env python3
"""
Demo Tool Asset Seeder

This script creates demo Tool Assets to showcase the Generic Orchestration System.
It directly creates tools in the database without requiring YAML files.
"""

import argparse
import sys
from pathlib import Path

# Add apps/api to Python path
API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from datetime import datetime

from app.modules.asset_registry.models import TbAssetRegistry, TbAssetVersionHistory
from core.db import get_session_context
from core.logging import get_logger

logger = get_logger(__name__)

# Demo tool definitions
DEMO_TOOLS = [
    {
        "name": "equipment_search",
        "description": "공장 장비 검색 도구. 키워드: 장비, 설비, equipment, machine",
        "tool_type": "database_query",
        "tool_config": {
            "source_ref": "factory_postgres",
            "query_template": "SELECT * FROM equipment WHERE name ILIKE '%{keyword}%' LIMIT {limit}",
            "timeout_ms": 30000,
            "max_retries": 3
        },
        "tool_input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Search keyword for equipment"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 10
                }
            },
            "required": ["keyword"]
        },
        "tool_output_schema": {
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "description": "List of equipment records"
                },
                "total": {
                    "type": "integer",
                    "description": "Total number of records found"
                }
            }
        }
    },
    {
        "name": "maintenance_history",
        "description": "장비 유지보수 이력 조회. 키워드: 유지보수, 점검, 정비, maintenance, history",
        "tool_type": "database_query",
        "tool_config": {
            "source_ref": "factory_postgres",
            "query_template": "SELECT * FROM maintenance WHERE equipment_id = {equipment_id} ORDER BY created_at DESC LIMIT {limit}",
            "timeout_ms": 30000,
            "max_retries": 3
        },
        "tool_input_schema": {
            "type": "object",
            "properties": {
                "equipment_id": {
                    "type": "string",
                    "description": "Equipment ID to search maintenance history for"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of records",
                    "default": 20
                }
            },
            "required": ["equipment_id"]
        },
        "tool_output_schema": {
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "description": "List of maintenance records"
                },
                "total": {
                    "type": "integer",
                    "description": "Total maintenance records"
                }
            }
        }
    },
    {
        "name": "bom_lookup",
        "description": "제품 BOM(부품 구성) 조회. 키워드: BOM, 부품, 구성, component, bill of materials",
        "tool_type": "database_query",
        "tool_config": {
            "source_ref": "factory_postgres",
            "query_template": "SELECT * FROM bom WHERE product_id = {product_id}",
            "timeout_ms": 30000,
            "max_retries": 3
        },
        "tool_input_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "Product ID to look up BOM"
                }
            },
            "required": ["product_id"]
        },
        "tool_output_schema": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string"
                },
                "components": {
                    "type": "array",
                    "description": "List of components in BOM"
                }
            }
        }
    },
    {
        "name": "production_status",
        "description": "생산 현황 조회. 키워드: 생산, 제조, 현황, 상태, production, status",
        "tool_type": "database_query",
        "tool_config": {
            "source_ref": "factory_postgres",
            "query_template": "SELECT * FROM production_order WHERE status = {status} ORDER BY updated_at DESC LIMIT {limit}",
            "timeout_ms": 30000,
            "max_retries": 3
        },
        "tool_input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "running", "completed", "failed"],
                    "description": "Production status filter",
                    "default": "running"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of records",
                    "default": 50
                }
            },
            "required": ["status"]
        },
        "tool_output_schema": {
            "type": "object",
            "properties": {
                "orders": {
                    "type": "array",
                    "description": "List of production orders"
                },
                "total": {
                    "type": "integer"
                }
            }
        }
    },
    {
        "name": "worker_schedule",
        "description": "근무자 일정 조회. 키워드: 근무, 일정, 스케줄, 작업자, worker, schedule",
        "tool_type": "database_query",
        "tool_config": {
            "source_ref": "factory_postgres",
            "query_template": "SELECT * FROM worker_schedule WHERE date = {date} ORDER BY shift",
            "timeout_ms": 30000,
            "max_retries": 3
        },
        "tool_input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "format": "date",
                    "description": "Date for schedule query (YYYY-MM-DD)"
                }
            },
            "required": ["date"]
        },
        "tool_output_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string"
                },
                "schedules": {
                    "type": "array",
                    "description": "List of worker schedules"
                }
            }
        }
    },
    {
        "name": "energy_consumption",
        "description": "에너지 소비량 조회. 키워드: 에너지, 전력, 소비, 사용, energy, power",
        "tool_type": "database_query",
        "tool_config": {
            "source_ref": "factory_postgres",
            "query_template": "SELECT * FROM energy_log WHERE timestamp BETWEEN {start_time} AND {end_time} ORDER BY timestamp DESC",
            "timeout_ms": 30000,
            "max_retries": 3
        },
        "tool_input_schema": {
            "type": "object",
            "properties": {
                "start_time": {
                    "type": "string",
                    "format": "date-time",
                    "description": "Start time for energy query"
                },
                "end_time": {
                    "type": "string",
                    "format": "date-time",
                    "description": "End time for energy query"
                }
            },
            "required": ["start_time", "end_time"]
        },
        "tool_output_schema": {
            "type": "object",
            "properties": {
                "records": {
                    "type": "array",
                    "description": "List of energy consumption records"
                },
                "total_consumption_kwh": {
                    "type": "number"
                }
            }
        }
    }
]


def create_demo_tool(session, tool_data: dict, created_by: str = "demo_seed_script") -> TbAssetRegistry:
    """Create a demo tool asset in database."""
    asset = TbAssetRegistry(
        asset_type="tool",
        name=tool_data["name"],
        description=tool_data["description"],
        tool_type=tool_data["tool_type"],
        tool_config=tool_data["tool_config"],
        tool_input_schema=tool_data["tool_input_schema"],
        tool_output_schema=tool_data.get("tool_output_schema"),
        status="draft",
        version=1,
        created_by=created_by,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add(asset)
    session.flush()  # Get the asset_id without committing yet

    # Create version history
    history = TbAssetVersionHistory(
        asset_id=asset.asset_id,
        version=1,
        snapshot={
            "name": asset.name,
            "description": asset.description,
            "tool_type": asset.tool_type,
            "tool_config": asset.tool_config,
            "tool_input_schema": asset.tool_input_schema,
            "tool_output_schema": asset.tool_output_schema,
        },
        published_at=datetime.now(),
    )
    session.add(history)
    session.commit()

    logger.info(f"Created tool: {tool_data['name']} (id={asset.asset_id})")
    return asset


def main():
    parser = argparse.ArgumentParser(
        description="Seed demo Tool Assets into the database"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Apply changes to database"
    )
    parser.add_argument(
        "--publish", action="store_true", help="Publish created tools immediately"
    )
    parser.add_argument(
        "--cleanup", action="store_true", help="Delete existing draft tools first"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without applying"
    )

    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("Demo Tool Asset Seeder")
    logger.info("=" * 70)

    if args.dry_run:
        print("\n=== DRY RUN MODE ===")
        print(f"Would create {len(DEMO_TOOLS)} demo tools:\n")
        for i, tool in enumerate(DEMO_TOOLS, 1):
            print(f"{i}. {tool['name']}")
            print(f"   Type: {tool['tool_type']}")
            print(f"   Desc: {tool['description'][:60]}...")
            print()
        print("Use --apply flag to actually create tools in database.")
        return

    if not args.apply:
        print("\n⚠ No action performed. Use --apply to create tools.")
        print("Use --dry-run to preview what would be created.")
        return

    with get_session_context() as session:
        # Cleanup existing draft tools if requested
        if args.cleanup:
            logger.info("Cleaning up existing draft tools...")
            from sqlmodel import select

            existing = session.exec(
                select(TbAssetRegistry).where(
                    (TbAssetRegistry.asset_type == "tool")
                    & (TbAssetRegistry.status == "draft")
                )
            ).all()

            if existing:
                count = 0
                for tool in existing:
                    session.delete(tool)
                    count += 1
                session.commit()
                logger.info(f"Deleted {count} existing draft tools")

        # Create demo tools
        created_tools = []
        logger.info(f"Creating {len(DEMO_TOOLS)} demo tools...")
        for tool_data in DEMO_TOOLS:
            try:
                asset = create_demo_tool(session, tool_data)
                created_tools.append(
                    {
                        "name": asset.name,
                        "asset_id": str(asset.asset_id),
                        "status": asset.status,
                    }
                )
            except Exception as e:
                logger.error(f"Failed to create tool '{tool_data['name']}': {e}")
                continue

        # Publish tools if requested
        if args.publish:
            logger.info("Publishing created tools...")
            for tool_info in created_tools:
                try:
                    tool = session.get(TbAssetRegistry, tool_info["asset_id"])
                    if tool:
                        tool.status = "published"
                        tool.published_by = "demo_seed_script"
                        tool.published_at = datetime.now()
                        tool.version = 2
                        session.add(tool)

                        # Add version history for published version
                        history = TbAssetVersionHistory(
                            asset_id=tool.asset_id,
                            version=2,
                            snapshot={
                                "name": tool.name,
                                "description": tool.description,
                                "tool_type": tool.tool_type,
                                "tool_config": tool.tool_config,
                                "tool_input_schema": tool.tool_input_schema,
                                "tool_output_schema": tool.tool_output_schema,
                            },
                            published_by="demo_seed_script",
                            published_at=datetime.now(),
                        )
                        session.add(history)
                        session.commit()
                        logger.info(f"Published: {tool_info['name']}")
                except Exception as e:
                    logger.error(f"Failed to publish '{tool_info['name']}': {e}")

        # Summary
        logger.info("=" * 70)
        logger.info(f"✓ Created {len(created_tools)} demo tools")
        if args.publish:
            logger.info(f"✓ Published {len(created_tools)} tools")
        logger.info("=" * 70)

        print(f"\n✓ Successfully created {len(created_tools)} demo tools")
        if args.publish:
            print("✓ All tools are published and ready to use")
        else:
            print("  Status: draft")
            print("  Use --publish to publish tools")
        print()


if __name__ == "__main__":
    main()
