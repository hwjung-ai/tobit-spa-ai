#!/usr/bin/env python3
"""
Publish Keyword Mapping Assets to Database

This script creates and publishes keyword mapping assets from planner_llm.py.
These mappings are used for natural language query processing.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add apps/api to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.config import get_settings
from core.db import get_session_context
from app.modules.asset_registry.models import TbAssetRegistry


def create_mapping_asset(name: str, content: dict, description: str):
    """Create or update a mapping asset."""
    with get_session_context() as session:
        # Check if asset already exists
        existing = session.query(TbAssetRegistry).filter(
            TbAssetRegistry.name == name,
            TbAssetRegistry.asset_type == "mapping",
        ).first()

        if existing:
            print(f"⚠️  Asset '{name}' already exists (id={existing.asset_id})")
            print("   Updating content...")
            existing.content = content
            existing.status = "published"
            existing.description = description
            session.commit()
            print(f"✅ Updated asset '{name}' (id={existing.asset_id})")
            return existing.asset_id
        else:
            # Create new asset
            asset = TbAssetRegistry(
                name=name,
                asset_type="mapping",
                scope="planner",
                description=description,
                content=content,
                status="published",
                tenant_id="system",  # System-wide policy
            )
            session.add(asset)
            session.commit()
            print(f"✅ Created asset '{name}' (id={asset.asset_id})")
            return asset.asset_id


def publish_metric_aliases():
    """metric_aliases mapping asset 생성"""
    content = {
        "aliases": {
            "cpu": "cpu_usage",
            "cpu_usage": "cpu_usage",
            "memory": "memory_usage",
            "memory_usage": "memory_usage",
            "disk": "disk_io",
            "disk_io": "disk_io",
            "network": "network_in",
            "network_in": "network_in",
            "temperature": "temperature",
            "latency": "cpu_usage",
            "응답시간": "cpu_usage",
            "response": "cpu_usage",
            "rps": "network_in",
            "error": "error",
            "사용량": "cpu_usage",
            "usage": "cpu_usage",
        },
        "keywords": ["지표", "지수", "메트릭", "metric"]
    }
    
    create_mapping_asset(
        name="metric_aliases",
        content=content,
        description="Metric name aliases and keywords for natural language query processing"
    )


def publish_agg_keywords():
    """agg_keywords mapping asset 생성"""
    content = {
        "mappings": {
            "최대": "max",
            "maximum": "max",
            "max": "max",
            "최소": "min",
            "minimum": "min",
            "min": "min",
            "평균": "avg",
            "average": "avg",
            "avg": "avg",
            "count": "count",
            "건수": "count",
            "높은": "max",
            "상위": "max",
            "top": "max",
            "가장": "max",
        }
    }
    
    create_mapping_asset(
        name="agg_keywords",
        content=content,
        description="Aggregation function keywords for natural language query processing"
    )


def publish_series_keywords():
    """series_keywords mapping asset 생성"""
    content = {
        "keywords": ["추이", "시계열", "그래프", "trend", "series", "line", "chart"]
    }
    
    create_mapping_asset(
        name="series_keywords",
        content=content,
        description="Time series/chart keywords for natural language query processing"
    )


def publish_history_keywords():
    """history_keywords mapping asset 생성"""
    content = {
        "keywords": ["이벤트", "알람", "로그", "event"],
        "time_map": {
            "24시간": "last_24h",
            "하루": "last_24h",
            "오늘": "last_24h",
            "7일": "last_7d",
            "일주일": "last_7d",
            "지난주": "last_7d",
            "30일": "last_30d",
            "한달": "last_30d",
        }
    }
    
    create_mapping_asset(
        name="history_keywords",
        content=content,
        description="History/event keywords and time range mappings for natural language query processing"
    )


def publish_list_keywords():
    """list_keywords mapping asset 생성"""
    content = {
        "keywords": [
            "목록",
            "리스트",
            "list",
            "전체 목록",
            "나열",
            "목록으로",
            "리스트로",
        ]
    }
    
    create_mapping_asset(
        name="list_keywords",
        content=content,
        description="List/output keywords for natural language query processing"
    )


def publish_table_hints():
    """table_hints mapping asset 생성"""
    content = {
        "keywords": [
            "표",
            "테이블",
            "table",
            "표로",
            "테이블로",
            "보여줘",
            "표로 보여줘",
            "테이블로 보여줘",
            "정리",
            "정리해서",
            "추출",
            "가져와",
            "뽑아",
            "뽑아줘",
            "출력",
        ]
    }
    
    create_mapping_asset(
        name="table_hints",
        content=content,
        description="Table output hint keywords for natural language query processing"
    )


def publish_cep_keywords():
    """cep_keywords mapping asset 생성"""
    content = {
        "keywords": ["simulate", "시뮬", "시뮬레이션", "규칙", "rule", "cep"]
    }
    
    create_mapping_asset(
        name="cep_keywords",
        content=content,
        description="CEP (Complex Event Processing) keywords for natural language query processing"
    )


def publish_graph_scope_keywords():
    """graph_scope_keywords mapping asset 생성"""
    content = {
        "scope_keywords": [
            "범위",
            "영향",
            "영향권",
            "주변",
            "연관",
            "관련",
            "의존",
            "dependency",
            "impact",
            "neighbors",
        ],
        "metric_keywords": [
            "cpu",
            "latency",
            "error",
            "성능",
            "rps",
            "response",
            "응답",
            "performance",
        ]
    }
    
    create_mapping_asset(
        name="graph_scope_keywords",
        content=content,
        description="Graph scope and metric keywords for natural language query processing"
    )


def publish_auto_keywords():
    """auto_keywords mapping asset 생성"""
    content = {
        "keywords": ["점검", "상태", "요약", "진단", "health", "overview", "status"]
    }
    
    create_mapping_asset(
        name="auto_keywords",
        content=content,
        description="Auto/health check keywords for natural language query processing"
    )


def publish_filterable_fields():
    """filterable_fields mapping asset 생성 (Schema Asset 확장 대안)"""
    content = {
        "tag_filter_keys": [
            "system",
            "role",
            "runs_on",
            "host_server",
            "ci_subtype",
            "connected_servers",
        ],
        "attr_filter_keys": [
            "engine",
            "version",
            "zone",
            "ip",
            "cpu_cores",
            "memory_gb",
        ]
    }
    
    create_mapping_asset(
        name="filterable_fields",
        content=content,
        description="CI filterable fields for tags and attributes in natural language queries"
    )


def main():
    """모든 keyword mapping assets 생성"""
    print("\n" + "="*60)
    print("Keyword Mapping Assets Publish Script")
    print("="*60 + "\n")
    
    try:
        publish_metric_aliases()
        publish_agg_keywords()
        publish_series_keywords()
        publish_history_keywords()
        publish_list_keywords()
        publish_table_hints()
        publish_cep_keywords()
        publish_graph_scope_keywords()
        publish_auto_keywords()
        publish_filterable_fields()
        
        print("\n" + "="*60)
        print("✅ All 10 keyword mapping assets published successfully!")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error publishing assets: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()