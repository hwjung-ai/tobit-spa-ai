"""
Mapping registry initialization module.

Loads all mapping assets from Asset Registry and registers fallbacks.
Import this module early in application startup.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _register_fallbacks(registry) -> None:
    """
    Register hardcoded fallbacks for all mappings.

    These fallbacks ensure the system works in dev/test environments
    where Asset Registry may not be populated.
    """
    # 1. metric_aliases
    registry.register_fallback(
        "metric_aliases",
        {
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
            "keywords": ["지표", "지수", "메트릭", "metric"],
        },
    )

    # 2. agg_keywords
    registry.register_fallback(
        "agg_keywords",
        {
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
        },
    )

    # 3. series_keywords
    registry.register_fallback(
        "series_keywords",
        {"keywords": ["추이", "시계열", "그래프", "trend", "series", "line", "chart"]},
    )

    # 4. history_keywords
    registry.register_fallback(
        "history_keywords",
        {
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
            },
        },
    )

    # 5. list_keywords
    registry.register_fallback(
        "list_keywords",
        {
            "keywords": [
                "목록",
                "리스트",
                "list",
                "전체 목록",
                "나열",
                "목록으로",
                "리스트로",
            ]
        },
    )

    # 6. table_hints
    registry.register_fallback(
        "table_hints",
        {
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
        },
    )

    # 7. cep_keywords
    registry.register_fallback(
        "cep_keywords",
        {"keywords": ["simulate", "시뮬", "시뮬레이션", "규칙", "rule", "cep"]},
    )

    # 8. graph_scope_keywords
    registry.register_fallback(
        "graph_scope_keywords",
        {
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
            ],
        },
    )

    # 9. auto_keywords
    registry.register_fallback(
        "auto_keywords",
        {"keywords": ["점검", "상태", "요약", "진단", "health", "overview", "status"]},
    )

    # 10. filterable_fields (FIX BUG #1: use consistent key names)
    registry.register_fallback(
        "filterable_fields",
        {
            "tag_filter_keys": [
                "system",
                "role",
                "runs_on",
                "host_server",
                "ci_subtype",
                "connected_servers",
            ],
            "attr_filter_keys": ["engine", "version", "zone", "ip", "cpu_cores", "memory_gb"],
        },
    )

    # 11. ci_code_patterns
    registry.register_fallback(
        "ci_code_patterns",
        {"patterns": [r"\b(?:sys|srv|app|was|storage|sec|db)[-\w]+\b"]},
    )

    # 12. graph_view_keywords
    registry.register_fallback(
        "graph_view_keywords",
        {
            "view_keyword_map": {
                "의존": "DEPENDENCY",
                "dependency": "DEPENDENCY",
                "주변": "NEIGHBORS",
                "연관": "NEIGHBORS",
                "관련": "NEIGHBORS",
                "neighbors": "NEIGHBORS",
                "영향": "IMPACT",
                "impact": "IMPACT",
                "영향권": "IMPACT",
            },
            "default_depths": {
                "DEPENDENCY": 2,
                "NEIGHBORS": 1,
                "IMPACT": 2,
            },
            "force_keywords": [
                "의존",
                "dependency",
                "관계",
                "그래프",
                "토폴로지",
                "topology",
            ],
        },
    )

    # 13. auto_view_preferences
    registry.register_fallback(
        "auto_view_preferences",
        {
            "preferences": [
                {"keywords": ["path", "경로", "연결"], "views": ["PATH"]},
                {"keywords": ["의존", "dependency", "depends"], "views": ["DEPENDENCY"]},
                {
                    "keywords": ["영향", "impact", "영향권", "downstream"],
                    "views": ["IMPACT"],
                },
                {"keywords": ["구성", "component", "composition"], "views": ["COMPOSITION"]},
                {
                    "keywords": ["주변", "neighbor", "연관", "관련"],
                    "views": ["NEIGHBORS"],
                },
            ]
        },
    )

    # 14. output_type_priorities
    registry.register_fallback(
        "output_type_priorities",
        {"global_priorities": ["chart", "table", "number", "network", "text"]},
    )


def _load_mapping_from_db(mapping_name: str):
    """
    Load a single mapping from Asset Registry.

    Args:
        mapping_name: Name of the mapping to load

    Returns:
        Mapping data or None if not found
    """
    try:
        from app.modules.asset_registry.loader import load_mapping_asset

        mapping_data, metadata = load_mapping_asset(mapping_name)
        if mapping_data:
            logger.info(
                f"Loaded mapping '{mapping_name}' from Asset Registry: {metadata}"
            )
            return mapping_data
    except Exception as e:
        logger.warning(
            f"Failed to load mapping '{mapping_name}' from Asset Registry: {e}"
        )
    return None


def initialize_mappings() -> None:
    """
    Initialize and register all mappings from Asset Registry.

    Loads all published Mapping Assets from the database and
    registers them with the global MappingRegistry.

    Should be called once during application startup.
    """
    try:
        from .registry import get_mapping_registry

        registry = get_mapping_registry()

        # Register fallbacks first (they act as defaults)
        _register_fallbacks(registry)
        logger.info("Registered fallback mappings for dev/test environments")

        # List of all mapping names to load
        mapping_names = [
            "metric_aliases",
            "agg_keywords",
            "series_keywords",
            "history_keywords",
            "list_keywords",
            "table_hints",
            "cep_keywords",
            "graph_scope_keywords",
            "auto_keywords",
            "filterable_fields",
            "ci_code_patterns",
            "graph_view_keywords",
            "auto_view_preferences",
            "output_type_priorities",
        ]

        # Try to load each mapping from Asset Registry
        loaded_count = 0
        for mapping_name in mapping_names:
            try:
                mapping_data = _load_mapping_from_db(mapping_name)
                if mapping_data:
                    registry.register_mapping(
                        mapping_name,
                        mapping_data,
                        source="asset_registry",
                    )
                    loaded_count += 1
            except Exception as e:
                logger.warning(
                    f"Failed to load mapping '{mapping_name}': {e}. "
                    f"Using fallback."
                )

        logger.info(
            f"Successfully loaded {loaded_count}/{len(mapping_names)} "
            f"mappings from Asset Registry"
        )

    except Exception as e:
        logger.error(f"Failed to initialize mapping registry: {e}")
