"""
Initialize default output format asset.

This asset defines output formatting templates for the present stage.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.asset_registry.models import TbAssetRegistry
from core.db import get_session_context
from sqlmodel import select

DEFAULT_OUTPUT_FORMAT_CONTENT = {
    "formats": {
        "table": {
            "template": "{title}\n\n{table}\n\n{footer}",
            "wrap_code": False,
        },
        "list": {
            "template": "{title}\n\n{items}\n\n{footer}",
            "wrap_code": False,
        },
        "graph": {
            "template": "{title}\n\n```\n{ascii_graph}\n```\n\n{legend}\n{summary}",
            "wrap_code": True,
        },
        "metric": {
            "template": "{title} ({time_range})\n\n{table}\n\nmetric: {metric_name}, agg: {aggregation}",
            "wrap_code": False,
        },
        "text": {
            "template": "{summary}",
            "wrap_code": False,
        },
    },
    "metadata_format": "필터: {filters}\n시간 범위: {time_range}\n데이터 소스: {sources}",
    "error_format": "⚠️ {error_message}\n\n원인: {error_reason}\n해결 방법: {error_solution}",
}


def init_output_format_asset():
    """Initialize default output format asset."""
    with get_session_context() as session:
        # Check if already exists
        existing = session.exec(
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "mapping")
            .where(TbAssetRegistry.name == "default_output_format")
        ).first()

        if not existing:
            # Create new asset
            asset = TbAssetRegistry(
                name="default_output_format",
                description="기본 출력 포맷 (테이블, 리스트, 그래프 등)",
                asset_type="mapping",
                mapping_type="output_format",
                content=DEFAULT_OUTPUT_FORMAT_CONTENT,
                status="published",
                is_system=True,
                tenant_id="default",
                scope="default",
                tags={"system": True, "type": "output_format"},
            )
            session.add(asset)
            print("[CREATE] default_output_format asset created")
        else:
            # Update existing
            existing.content = DEFAULT_OUTPUT_FORMAT_CONTENT
            existing.is_system = True
            print("[UPDATE] default_output_format asset updated")

        session.commit()
        print("\n✓ Output format asset initialized!")
        print("  Formats: table, list, graph, metric, text")
        print("  is_system: True (protected)")


if __name__ == "__main__":
    print("Initializing output format asset...")
    print("-" * 50)
    init_output_format_asset()
