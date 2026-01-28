# 범용 데이터 오케스트레이션 시스템 구현 계획

> **문서 버전**: 1.0
> **작성일**: 2026-01-28
> **목표**: CI 도메인 하드코딩을 제거하고, UI 설정만으로 다양한 도메인에 적용 가능한 범용 오케스트레이션 플랫폼 구축

---

## 목차

1. [개요](#1-개요)
2. [현재 시스템 분석](#2-현재-시스템-분석)
3. [Phase 0: 하드코딩 키워드 → Mapping Asset 이동](#3-phase-0-하드코딩-키워드--mapping-asset-이동)
4. [Phase 1: Tool Asset 스키마 추가](#4-phase-1-tool-asset-스키마-추가)
5. [Phase 2: Tool 동적 로딩](#5-phase-2-tool-동적-로딩)
6. [Phase 3: 범용 Planner](#6-phase-3-범용-planner)
7. [Phase 4: Tool 체이닝 실행기](#7-phase-4-tool-체이닝-실행기)
8. [Phase 5: Admin UI](#8-phase-5-admin-ui)
9. [테스트 계획](#9-테스트-계획)
10. [배포 및 롤백 계획](#10-배포-및-롤백-계획)

---

## 1. 개요

### 1.1 현재 문제점

| 문제 | 위치 | 영향 |
|------|------|------|
| CI 도메인 하드코딩 | `planner_llm.py` | 다른 도메인 적용 불가 |
| Tool 하드코딩 | `registry_init.py` | 새 Tool 추가 시 코드 수정 필요 |
| Intent→Tool 매핑 하드코딩 | `tool_selector.py` | 도메인별 매핑 불가 |
| 키워드 상수 하드코딩 | `planner_llm.py` | UI에서 키워드 수정 불가 |

### 1.2 목표 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        Admin UI                                  │
├─────────────────────────────────────────────────────────────────┤
│  Source Asset  │  Tool Asset  │  Mapping Asset  │  Query Asset  │
│  (DB 연결)      │  (도구 정의)   │  (키워드 매핑)    │  (쿼리 템플릿)  │
└────────┬───────┴──────┬───────┴───────┬─────────┴───────┬───────┘
         │              │               │                 │
         ▼              ▼               ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Asset Registry (DB)                          │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Generic Planner                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ LLM Tool    │  │ Keyword     │  │ Intent      │              │
│  │ Selector    │  │ Matcher     │  │ Analyzer    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Tool Chain Executor                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Sequential  │  │ Parallel    │  │ DAG         │              │
│  │ Executor    │  │ Executor    │  │ Executor    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Dynamic Tool Registry                        │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
│  │ DB Query  │  │ HTTP API  │  │ Graph     │  │ Custom    │    │
│  │ Tool      │  │ Tool      │  │ Tool      │  │ Tool      │    │
│  └───────────┘  └───────────┘  └───────────┘  └───────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Phase 별 요약

| Phase | 목표 | 파일 수 | 의존성 |
|-------|------|--------|--------|
| 0 | 하드코딩 키워드 → Mapping Asset | 5개 수정 | 없음 |
| 1 | Tool Asset 스키마 추가 | 6개 수정 + 1개 생성 | Phase 0 |
| 2 | Tool 동적 로딩 | 4개 수정 + 1개 생성 | Phase 1 |
| 3 | 범용 Planner | 2개 수정 + 3개 생성 | Phase 2 |
| 4 | Tool 체이닝 | 1개 수정 + 2개 생성 | Phase 3 |
| 5 | Admin UI | 2개 수정 + 4개 생성 | Phase 1-4 |

---

## 2. 현재 시스템 분석

### 2.1 하드코딩된 요소 목록

#### planner_llm.py 하드코딩 (12개)

| 라인 | 변수명 | 용도 | 이동 대상 |
|------|--------|------|----------|
| ~50 | `CI_CODE_PATTERN` | CI 코드 패턴 정규식 | ci_code_patterns.yaml |
| ~55 | `NUMBER_KEYWORDS` | 숫자/집계 키워드 | ci_code_patterns.yaml |
| ~60 | `TYPE_KEYWORDS` | 타입/종류 키워드 | ci_code_patterns.yaml |
| ~65 | `SERVER_FILTER_KEYWORDS` | 서버 필터 키워드 | ci_code_patterns.yaml |
| ~200 | `GRAPH_VIEW_KEYWORD_MAP` | 그래프 뷰 키워드 매핑 | graph_view_keywords.yaml |
| ~210 | `DEFAULT_DEPTHS` | 그래프 기본 깊이 | graph_view_keywords.yaml |
| ~220 | `FORCE_GRAPH_KEYWORDS` | 강제 그래프 키워드 | graph_view_keywords.yaml |
| ~400 | `AUTO_VIEW_PREFERENCES` | 자동 뷰 선호도 | auto_view_preferences.yaml |
| ~500 | `OUTPUT_TYPE_PRIORITIES` | 출력 타입 우선순위 | output_type_priorities.yaml |
| ~600 | `FILTER_OP_KEYWORDS` | 필터 연산자 키워드 | filter_keywords.yaml |
| ~700 | `AGGREGATION_KEYWORDS` | 집계 키워드 | aggregation_keywords.yaml |
| 1083 | `LIST_KEYWORDS` | 리스트 키워드 (버그) | list_keywords.yaml |

#### registry_init.py 하드코딩 (5개 Tool)

```python
# 현재 하드코딩된 Tool 등록
register_tool(CommonToolTypes.CI, CITool)
register_tool(CommonToolTypes.GRAPH, GraphTool)
register_tool(CommonToolTypes.METRIC, MetricTool)
register_tool(CommonToolTypes.HISTORY, HistoryTool)
register_tool(CommonToolTypes.CEP, CEPTool)
```

#### tool_selector.py 하드코딩 (Intent→Tool 매핑)

```python
# 현재 하드코딩된 매핑
mapping = {
    Intent.SEARCH: ["CI_SEARCH", "CI_GET"],
    Intent.LOOKUP: ["CI_GET", "CI_GET_BY_CODE"],
    Intent.AGGREGATE: ["CI_AGGREGATE", "METRIC_AGGREGATE"],
    Intent.EXPAND: ["GRAPH_EXPAND"],
    Intent.PATH: ["GRAPH_PATH"],
    Intent.LIST: ["CI_LIST_PREVIEW", "CI_SEARCH"],
}
```

### 2.2 현재 Asset 유형

| asset_type | 용도 | DB 필드 |
|------------|------|---------|
| prompt | LLM 프롬프트 템플릿 | template, input_schema, output_contract |
| query | SQL/Cypher 쿼리 | query_sql, query_cypher, query_params |
| source | 데이터 소스 연결 | (별도 테이블 참조) |
| mapping | 키워드/설정 매핑 | content |
| policy | 정책/제한 | limits |
| screen | UI 화면 정의 | schema_json, screen_id |
| schema | 데이터 스키마 | schema_json |
| resolver | 이름 해석 규칙 | content |

---

## 3. Phase 0: 하드코딩 키워드 → Mapping Asset 이동

### 3.1 체크리스트

- [ ] **P0-1**: Mapping YAML 파일 6개 생성
  - [ ] `ci_code_patterns.yaml`
  - [ ] `graph_view_keywords.yaml`
  - [ ] `auto_view_preferences.yaml`
  - [ ] `output_type_priorities.yaml`
  - [ ] `filter_keywords.yaml`
  - [ ] `aggregation_keywords.yaml`
- [ ] **P0-2**: `planner_llm.py`에 `_get_*()` 함수 추가
  - [ ] `_get_ci_code_patterns()`
  - [ ] `_get_graph_view_keywords()`
  - [ ] `_get_auto_view_preferences()`
  - [ ] `_get_output_type_priorities()`
  - [ ] `_get_filter_keywords()`
  - [ ] `_get_aggregation_keywords()`
- [ ] **P0-3**: 하드코딩 상수를 함수 호출로 교체
- [ ] **P0-4**: `LIST_KEYWORDS` 버그 수정 (line 1083)
- [ ] **P0-5**: 테스트 실행 및 검증

### 3.2 Mapping YAML 파일 상세

#### 3.2.1 ci_code_patterns.yaml

```yaml
# apps/api/resources/mappings/ci_code_patterns.yaml
name: ci_code_patterns
description: CI 코드 패턴 및 키워드 정의
content:
  # CI 코드 정규식 패턴
  patterns:
    - "(?:sys|srv|app|was|storage|sec|db)[-\\w]+"

  # 숫자/집계 관련 키워드
  number_keywords:
    - "얼마나"
    - "숫자"
    - "count"
    - "total"
    - "몇"
    - "개수"
    - "합계"
    - "평균"

  # 타입/종류 관련 키워드
  type_keywords:
    - "종류"
    - "타입"
    - "type"
    - "category"
    - "분류"
    - "유형"

  # 서버 필터 키워드
  server_filter_keywords:
    - "서버"
    - "server"
    - "호스트"
    - "host"
    - "인스턴스"
    - "instance"

  # 리스트 키워드
  list_keywords:
    - "목록"
    - "list"
    - "리스트"
    - "전체"
    - "모든"
    - "all"
```

#### 3.2.2 graph_view_keywords.yaml

```yaml
# apps/api/resources/mappings/graph_view_keywords.yaml
name: graph_view_keywords
description: 그래프 뷰 키워드 및 설정
content:
  # 키워드 → 뷰 타입 매핑
  view_keyword_map:
    "의존": "DEPENDENCY"
    "dependency": "DEPENDENCY"
    "depends": "DEPENDENCY"
    "주변": "NEIGHBORS"
    "neighbor": "NEIGHBORS"
    "이웃": "NEIGHBORS"
    "영향": "IMPACT"
    "impact": "IMPACT"
    "파급": "IMPACT"
    "경로": "PATH"
    "path": "PATH"
    "연결": "PATH"

  # 뷰별 기본 깊이
  default_depths:
    DEPENDENCY: 2
    NEIGHBORS: 1
    IMPACT: 2
    PATH: 4

  # 강제 그래프 모드 키워드
  force_keywords:
    - "의존"
    - "dependency"
    - "관계"
    - "그래프"
    - "토폴로지"
    - "topology"
    - "연결"
    - "connection"
```

#### 3.2.3 auto_view_preferences.yaml

```yaml
# apps/api/resources/mappings/auto_view_preferences.yaml
name: auto_view_preferences
description: 자동 뷰 선택 선호도
content:
  preferences:
    - keywords: ["path", "경로", "연결", "어떻게"]
      views: ["PATH"]
      priority: 1

    - keywords: ["의존", "dependency", "depends"]
      views: ["DEPENDENCY"]
      priority: 2

    - keywords: ["영향", "impact", "파급"]
      views: ["IMPACT"]
      priority: 3

    - keywords: ["주변", "neighbor", "이웃", "근처"]
      views: ["NEIGHBORS"]
      priority: 4

    - keywords: ["구조", "아키텍처", "topology"]
      views: ["DEPENDENCY", "NEIGHBORS"]
      priority: 5
```

#### 3.2.4 output_type_priorities.yaml

```yaml
# apps/api/resources/mappings/output_type_priorities.yaml
name: output_type_priorities
description: 출력 타입 우선순위
content:
  # 우선순위 순서 (앞이 높음)
  priorities:
    - "chart"
    - "table"
    - "number"
    - "network"
    - "text"

  # Intent별 기본 출력 타입
  intent_defaults:
    SEARCH: "table"
    LOOKUP: "table"
    AGGREGATE: "chart"
    EXPAND: "network"
    PATH: "network"
    LIST: "table"
```

#### 3.2.5 filter_keywords.yaml

```yaml
# apps/api/resources/mappings/filter_keywords.yaml
name: filter_keywords
description: 필터 연산자 키워드
content:
  operators:
    equals:
      keywords: ["인", "은", "가", "이", "="]
      operator: "eq"

    contains:
      keywords: ["포함", "contain", "like", "있는"]
      operator: "contains"

    greater_than:
      keywords: ["이상", "초과", "넘는", ">", "bigger"]
      operator: "gt"

    less_than:
      keywords: ["이하", "미만", "작은", "<", "smaller"]
      operator: "lt"

    between:
      keywords: ["사이", "범위", "between", "from~to"]
      operator: "between"
```

#### 3.2.6 aggregation_keywords.yaml

```yaml
# apps/api/resources/mappings/aggregation_keywords.yaml
name: aggregation_keywords
description: 집계 함수 키워드
content:
  functions:
    count:
      keywords: ["개수", "count", "몇 개", "총"]
      function: "COUNT"

    sum:
      keywords: ["합계", "sum", "총합", "합"]
      function: "SUM"

    average:
      keywords: ["평균", "average", "avg", "mean"]
      function: "AVG"

    max:
      keywords: ["최대", "max", "maximum", "가장 큰"]
      function: "MAX"

    min:
      keywords: ["최소", "min", "minimum", "가장 작은"]
      function: "MIN"

  # 그룹핑 키워드
  group_by_keywords:
    - "별로"
    - "기준"
    - "group by"
    - "분류"
    - "카테고리별"
```

### 3.3 코드 변경 상세

#### 3.3.1 planner_llm.py 수정

```python
# apps/api/app/modules/ops/services/ci/planner/planner_llm.py

# 캐시 변수 추가 (파일 상단)
_CI_CODE_PATTERNS_CACHE: dict | None = None
_GRAPH_VIEW_KEYWORDS_CACHE: dict | None = None
_AUTO_VIEW_PREFERENCES_CACHE: dict | None = None
_OUTPUT_TYPE_PRIORITIES_CACHE: dict | None = None
_FILTER_KEYWORDS_CACHE: dict | None = None
_AGGREGATION_KEYWORDS_CACHE: dict | None = None


def _get_ci_code_patterns() -> dict:
    """CI 코드 패턴 로드 (캐시 적용)"""
    global _CI_CODE_PATTERNS_CACHE
    if _CI_CODE_PATTERNS_CACHE is not None:
        return _CI_CODE_PATTERNS_CACHE

    from app.modules.asset_registry.loader import load_mapping_asset

    mapping, _ = load_mapping_asset("ci_code_patterns")
    if mapping and mapping.get("content"):
        _CI_CODE_PATTERNS_CACHE = mapping["content"]
        return _CI_CODE_PATTERNS_CACHE

    # Fallback (하위 호환)
    _CI_CODE_PATTERNS_CACHE = {
        "patterns": [r"(?:sys|srv|app|was|storage|sec|db)[-\w]+"],
        "number_keywords": ["얼마나", "숫자", "count", "total", "몇"],
        "type_keywords": ["종류", "타입", "type", "category"],
        "server_filter_keywords": ["서버", "server"],
        "list_keywords": ["목록", "list", "리스트", "전체"],
    }
    return _CI_CODE_PATTERNS_CACHE


def _get_graph_view_keywords() -> dict:
    """그래프 뷰 키워드 로드 (캐시 적용)"""
    global _GRAPH_VIEW_KEYWORDS_CACHE
    if _GRAPH_VIEW_KEYWORDS_CACHE is not None:
        return _GRAPH_VIEW_KEYWORDS_CACHE

    from app.modules.asset_registry.loader import load_mapping_asset

    mapping, _ = load_mapping_asset("graph_view_keywords")
    if mapping and mapping.get("content"):
        _GRAPH_VIEW_KEYWORDS_CACHE = mapping["content"]
        return _GRAPH_VIEW_KEYWORDS_CACHE

    # Fallback
    _GRAPH_VIEW_KEYWORDS_CACHE = {
        "view_keyword_map": {"의존": "DEPENDENCY", "주변": "NEIGHBORS"},
        "default_depths": {"DEPENDENCY": 2, "NEIGHBORS": 1, "IMPACT": 2, "PATH": 4},
        "force_keywords": ["의존", "dependency", "관계", "그래프"],
    }
    return _GRAPH_VIEW_KEYWORDS_CACHE


def _get_list_keywords() -> list:
    """리스트 키워드 로드"""
    patterns = _get_ci_code_patterns()
    return patterns.get("list_keywords", ["목록", "list", "리스트"])


# 기존 하드코딩 사용 부분 교체 예시:
# Before: if any(kw in question for kw in NUMBER_KEYWORDS):
# After:  if any(kw in question for kw in _get_ci_code_patterns()["number_keywords"]):

# Before: if any(kw in question for kw in LIST_KEYWORDS):  # 버그: 정의되지 않음
# After:  if any(kw in question for kw in _get_list_keywords()):
```

### 3.4 테스트 케이스

```python
# tests/unit/test_planner_mapping_integration.py

import pytest
from app.modules.ops.services.ci.planner.planner_llm import (
    _get_ci_code_patterns,
    _get_graph_view_keywords,
    _get_list_keywords,
)


class TestMappingIntegration:
    """Mapping Asset 통합 테스트"""

    def test_ci_code_patterns_loads_from_db(self, db_session):
        """DB에서 CI 코드 패턴을 로드하는지 확인"""
        # Given: DB에 Mapping Asset 존재
        # When: _get_ci_code_patterns() 호출
        patterns = _get_ci_code_patterns()

        # Then: 필수 키 존재
        assert "patterns" in patterns
        assert "number_keywords" in patterns
        assert "type_keywords" in patterns

    def test_fallback_when_db_empty(self, db_session):
        """DB에 데이터 없을 때 fallback 동작 확인"""
        # Given: DB에 Mapping Asset 없음
        # When: _get_ci_code_patterns() 호출
        patterns = _get_ci_code_patterns()

        # Then: fallback 값 반환
        assert len(patterns["patterns"]) > 0

    def test_list_keywords_bug_fixed(self, db_session):
        """LIST_KEYWORDS 버그 수정 확인"""
        # Given/When
        keywords = _get_list_keywords()

        # Then: 리스트 반환 (NameError 없음)
        assert isinstance(keywords, list)
        assert len(keywords) > 0

    def test_cache_works(self, db_session):
        """캐시가 동작하는지 확인"""
        # Given: 첫 번째 호출
        patterns1 = _get_ci_code_patterns()

        # When: 두 번째 호출
        patterns2 = _get_ci_code_patterns()

        # Then: 동일 객체 반환 (캐시)
        assert patterns1 is patterns2
```

---

## 4. Phase 1: Tool Asset 스키마 추가

### 4.1 체크리스트

- [ ] **P1-1**: DB 스키마 수정
  - [ ] `models.py`에 Tool 필드 4개 추가
  - [ ] Alembic 마이그레이션 파일 생성
  - [ ] 마이그레이션 실행
- [ ] **P1-2**: Pydantic 스키마 추가
  - [ ] `ToolAssetCreate` 스키마
  - [ ] `ToolAssetRead` 스키마
  - [ ] `ToolAssetUpdate` 스키마
- [ ] **P1-3**: CRUD 함수 추가
  - [ ] `create_tool_asset()`
  - [ ] `get_tool_asset()`
  - [ ] `update_tool_asset()`
  - [ ] `list_tool_assets()`
- [ ] **P1-4**: Loader 함수 추가
  - [ ] `load_tool_asset()`
  - [ ] `load_all_published_tools()`
- [ ] **P1-5**: 검증 로직 추가
  - [ ] Tool input_schema 검증
  - [ ] Tool config 검증
- [ ] **P1-6**: API 엔드포인트 추가
  - [ ] `GET /api/asset-registry/tools`
  - [ ] `POST /api/asset-registry/tools`
  - [ ] `PUT /api/asset-registry/tools/{id}`
  - [ ] `POST /api/asset-registry/tools/{id}/test`
- [ ] **P1-7**: 테스트 작성 및 실행

### 4.2 DB 스키마 변경

#### 4.2.1 models.py 수정

```python
# apps/api/app/modules/asset_registry/models.py

class TbAssetRegistry(SQLModel, table=True):
    # ... 기존 필드 ...

    # ===== Tool Asset 필드 (Phase 1 추가) =====
    tool_type: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Tool 실행 유형: database_query, http_api, graph_query, custom"
    )
    tool_config: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Tool 실행 설정 (source_ref, query_ref, timeout 등)"
    )
    tool_input_schema: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Tool 입력 파라미터 JSON Schema"
    )
    tool_output_schema: dict[str, Any] | None = Field(
        default=None,
        sa_column=Column(JSONB, nullable=True),
        description="Tool 출력 결과 JSON Schema"
    )
```

#### 4.2.2 Alembic 마이그레이션

```python
# apps/api/alembic/versions/xxxx_add_tool_asset_fields.py

"""Add Tool Asset fields to tb_asset_registry

Revision ID: xxxx
Revises: yyyy
Create Date: 2026-01-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'xxxx'
down_revision = 'yyyy'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tool Asset 필드 추가
    op.add_column(
        'tb_asset_registry',
        sa.Column('tool_type', sa.Text(), nullable=True)
    )
    op.add_column(
        'tb_asset_registry',
        sa.Column('tool_config', JSONB(), nullable=True)
    )
    op.add_column(
        'tb_asset_registry',
        sa.Column('tool_input_schema', JSONB(), nullable=True)
    )
    op.add_column(
        'tb_asset_registry',
        sa.Column('tool_output_schema', JSONB(), nullable=True)
    )

    # 인덱스 추가 (tool_type으로 조회 빈번)
    op.create_index(
        'ix_asset_registry_tool_type',
        'tb_asset_registry',
        ['tool_type'],
        postgresql_where=sa.text("asset_type = 'tool'")
    )


def downgrade() -> None:
    op.drop_index('ix_asset_registry_tool_type')
    op.drop_column('tb_asset_registry', 'tool_output_schema')
    op.drop_column('tb_asset_registry', 'tool_input_schema')
    op.drop_column('tb_asset_registry', 'tool_config')
    op.drop_column('tb_asset_registry', 'tool_type')
```

### 4.3 Pydantic 스키마

```python
# apps/api/app/modules/asset_registry/schemas.py

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Any, Literal


class ToolAssetCreate(BaseModel):
    """Tool Asset 생성 스키마"""
    model_config = ConfigDict(populate_by_name=True)

    asset_type: Literal["tool"] = "tool"
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(
        None,
        description="Tool 설명 (LLM이 Tool 선택 시 참조)"
    )

    tool_type: str = Field(
        ...,
        description="Tool 실행 유형",
        examples=["database_query", "http_api", "graph_query", "custom"]
    )
    tool_config: dict[str, Any] = Field(
        ...,
        description="Tool 실행 설정"
    )
    tool_input_schema: dict[str, Any] = Field(
        ...,
        description="JSON Schema for input parameters"
    )
    tool_output_schema: dict[str, Any] | None = Field(
        None,
        description="JSON Schema for output (optional)"
    )

    scope: str | None = None
    tags: dict[str, Any] | None = None
    created_by: str | None = None

    @field_validator('tool_type')
    @classmethod
    def validate_tool_type(cls, v: str) -> str:
        allowed = ["database_query", "http_api", "graph_query", "custom"]
        if v not in allowed:
            raise ValueError(f"tool_type must be one of {allowed}")
        return v

    @field_validator('tool_config')
    @classmethod
    def validate_tool_config(cls, v: dict, info) -> dict:
        tool_type = info.data.get('tool_type')

        if tool_type == "database_query":
            if "source_ref" not in v:
                raise ValueError("database_query requires 'source_ref' in tool_config")
        elif tool_type == "http_api":
            if "base_url" not in v:
                raise ValueError("http_api requires 'base_url' in tool_config")

        return v


class ToolAssetRead(BaseModel):
    """Tool Asset 조회 스키마"""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    asset_id: str
    asset_type: str
    name: str
    description: str | None
    version: int
    status: str

    tool_type: str | None
    tool_config: dict[str, Any] | None
    tool_input_schema: dict[str, Any] | None
    tool_output_schema: dict[str, Any] | None

    scope: str | None
    tags: dict[str, Any] | None
    created_by: str | None
    published_by: str | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ToolAssetUpdate(BaseModel):
    """Tool Asset 수정 스키마"""
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    description: str | None = None
    tool_type: str | None = None
    tool_config: dict[str, Any] | None = None
    tool_input_schema: dict[str, Any] | None = None
    tool_output_schema: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
```

### 4.4 CRUD 함수

```python
# apps/api/app/modules/asset_registry/crud.py

async def create_tool_asset(
    db: AsyncSession,
    data: ToolAssetCreate,
) -> TbAssetRegistry:
    """Tool Asset 생성"""
    asset = TbAssetRegistry(
        asset_type="tool",
        name=data.name,
        description=data.description,
        tool_type=data.tool_type,
        tool_config=data.tool_config,
        tool_input_schema=data.tool_input_schema,
        tool_output_schema=data.tool_output_schema,
        scope=data.scope,
        tags=data.tags,
        created_by=data.created_by,
        status="draft",
        version=1,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def list_tool_assets(
    db: AsyncSession,
    status: str | None = None,
    tool_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[TbAssetRegistry], int]:
    """Tool Asset 목록 조회"""
    query = select(TbAssetRegistry).where(
        TbAssetRegistry.asset_type == "tool"
    )

    if status:
        query = query.where(TbAssetRegistry.status == status)
    if tool_type:
        query = query.where(TbAssetRegistry.tool_type == tool_type)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Results
    query = query.order_by(TbAssetRegistry.updated_at.desc())
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)

    return result.scalars().all(), total or 0
```

### 4.5 Loader 함수

```python
# apps/api/app/modules/asset_registry/loader.py

async def load_tool_asset(name: str) -> tuple[dict | None, str | None]:
    """
    이름으로 Tool Asset 로드

    Returns:
        (tool_dict, error_message)
    """
    async with get_async_session() as db:
        result = await db.execute(
            select(TbAssetRegistry).where(
                TbAssetRegistry.asset_type == "tool",
                TbAssetRegistry.name == name,
                TbAssetRegistry.status == "published",
            )
        )
        asset = result.scalar_one_or_none()

        if not asset:
            return None, f"Tool '{name}' not found or not published"

        return {
            "asset_id": str(asset.asset_id),
            "name": asset.name,
            "description": asset.description,
            "tool_type": asset.tool_type,
            "tool_config": asset.tool_config,
            "tool_input_schema": asset.tool_input_schema,
            "tool_output_schema": asset.tool_output_schema,
        }, None


async def load_all_published_tools() -> list[dict]:
    """
    발행된 모든 Tool Asset 로드

    Returns:
        Tool Asset 목록
    """
    async with get_async_session() as db:
        result = await db.execute(
            select(TbAssetRegistry).where(
                TbAssetRegistry.asset_type == "tool",
                TbAssetRegistry.status == "published",
            )
        )
        assets = result.scalars().all()

        return [
            {
                "asset_id": str(a.asset_id),
                "name": a.name,
                "description": a.description,
                "tool_type": a.tool_type,
                "tool_config": a.tool_config,
                "tool_input_schema": a.tool_input_schema,
                "tool_output_schema": a.tool_output_schema,
            }
            for a in assets
        ]
```

### 4.6 초기 데이터 (기존 Tool → Tool Asset 이관)

```yaml
# apps/api/resources/tools/ci_search.yaml
name: ci_search
description: |
  CI(Configuration Item) 검색 도구.
  서버, 애플리케이션, 데이터베이스 등 IT 자산을 키워드로 검색합니다.
  키워드: 서버, 시스템, CI, 검색, 찾기, search
tool_type: database_query
tool_config:
  source_ref: cmdb_postgres
  query_ref: ci_search_query
  timeout_ms: 30000
  max_results: 100
tool_input_schema:
  type: object
  properties:
    keywords:
      type: array
      items:
        type: string
      description: 검색 키워드 목록
    filters:
      type: array
      items:
        type: object
      description: 필터 조건
    limit:
      type: integer
      default: 10
      maximum: 100
  required:
    - keywords
tool_output_schema:
  type: object
  properties:
    records:
      type: array
      items:
        type: object
    total:
      type: integer
    truncated:
      type: boolean


# apps/api/resources/tools/graph_expand.yaml
name: graph_expand
description: |
  그래프 관계 확장 도구.
  특정 CI의 의존성, 영향도, 주변 관계를 그래프로 조회합니다.
  키워드: 관계, 의존, 연결, 그래프, 토폴로지, dependency
tool_type: graph_query
tool_config:
  source_ref: neo4j_cmdb
  timeout_ms: 60000
  max_depth: 5
tool_input_schema:
  type: object
  properties:
    ci_id:
      type: string
      description: 시작 CI ID
    view_type:
      type: string
      enum: [DEPENDENCY, NEIGHBORS, IMPACT, PATH]
      default: DEPENDENCY
    depth:
      type: integer
      default: 2
      maximum: 5
  required:
    - ci_id
tool_output_schema:
  type: object
  properties:
    nodes:
      type: array
    edges:
      type: array
    metadata:
      type: object
```

### 4.7 마이그레이션 스크립트

```python
# scripts/migrate_tools_to_assets.py
"""
기존 하드코딩된 Tool 정의를 Tool Asset으로 이관
"""

import asyncio
import yaml
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.asset_registry.crud import create_tool_asset
from app.modules.asset_registry.schemas import ToolAssetCreate
from core.database import get_async_session


TOOLS_DIR = Path("apps/api/resources/tools")


async def migrate_tools():
    """Tool YAML 파일을 DB로 이관"""

    async with get_async_session() as db:
        for yaml_file in TOOLS_DIR.glob("*.yaml"):
            print(f"Migrating {yaml_file.name}...")

            with open(yaml_file) as f:
                tool_data = yaml.safe_load(f)

            # ToolAssetCreate로 변환
            create_data = ToolAssetCreate(
                name=tool_data["name"],
                description=tool_data.get("description"),
                tool_type=tool_data["tool_type"],
                tool_config=tool_data["tool_config"],
                tool_input_schema=tool_data["tool_input_schema"],
                tool_output_schema=tool_data.get("tool_output_schema"),
                created_by="migration_script",
            )

            # 생성
            asset = await create_tool_asset(db, create_data)
            print(f"  Created: {asset.asset_id}")

            # 자동 발행 (기존 Tool은 즉시 사용 가능해야 함)
            asset.status = "published"
            asset.published_by = "migration_script"
            await db.commit()
            print(f"  Published: {asset.name}")

    print("Migration complete!")


if __name__ == "__main__":
    asyncio.run(migrate_tools())
```

---

## 5. Phase 2: Tool 동적 로딩

### 5.1 체크리스트

- [ ] **P2-1**: DynamicTool 클래스 구현
  - [ ] `dynamic_tool.py` 파일 생성
  - [ ] BaseTool 상속 구현
  - [ ] database_query 실행기
  - [ ] http_api 실행기
  - [ ] graph_query 실행기
- [ ] **P2-2**: ToolRegistry 확장
  - [ ] `register_dynamic()` 메서드 추가
  - [ ] `load_from_db()` 메서드 추가
  - [ ] `reload_tools()` 메서드 추가 (핫 리로드)
- [ ] **P2-3**: registry_init.py 수정
  - [ ] DB 로딩 호출 추가
  - [ ] 에러 핸들링 추가
- [ ] **P2-4**: 테스트 작성 및 실행

### 5.2 DynamicTool 클래스

```python
# apps/api/app/modules/ops/services/ci/tools/dynamic_tool.py

"""
동적 Tool 클래스

Tool Asset에서 로드된 정의를 기반으로 런타임에 Tool 인스턴스를 생성합니다.
"""

from __future__ import annotations

import asyncio
import httpx
from typing import Any, Dict

from app.modules.ops.services.ci.tools.base import (
    BaseTool,
    ToolContext,
    ToolResult,
)
from app.modules.asset_registry.loader import load_source_asset
from core.logging import get_logger

logger = get_logger(__name__)


class DynamicTool(BaseTool):
    """
    동적으로 로드되는 Tool.

    Tool Asset의 정의에 따라 다양한 실행 유형을 지원합니다:
    - database_query: SQL/Cypher 쿼리 실행
    - http_api: REST API 호출
    - graph_query: 그래프 DB 쿼리
    - custom: 커스텀 Python 코드 실행
    """

    def __init__(self, tool_asset: Dict[str, Any]):
        """
        Tool Asset으로부터 DynamicTool 생성

        Args:
            tool_asset: Tool Asset 딕셔너리
                - name: Tool 이름
                - description: Tool 설명 (LLM 선택용)
                - tool_type: 실행 유형
                - tool_config: 실행 설정
                - tool_input_schema: 입력 스키마
                - tool_output_schema: 출력 스키마 (optional)
        """
        super().__init__()
        self._asset = tool_asset
        self._name = tool_asset["name"]
        self._description = tool_asset.get("description", "")
        self._tool_type_value = tool_asset["tool_type"]
        self._config = tool_asset.get("tool_config", {})
        self._input_schema = tool_asset.get("tool_input_schema", {})
        self._output_schema = tool_asset.get("tool_output_schema")

        # 실행기 매핑
        self._executors = {
            "database_query": self._execute_database_query,
            "http_api": self._execute_http_api,
            "graph_query": self._execute_graph_query,
            "custom": self._execute_custom,
        }

    @property
    def tool_type(self) -> str:
        return self._tool_type_value

    @property
    def tool_name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        return self._input_schema

    async def should_execute(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> bool:
        """이 Tool이 실행 가능한지 확인"""
        # 필수 파라미터 검증
        required = self._input_schema.get("required", [])
        for req in required:
            if req not in params:
                return False
        return True

    async def execute(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> ToolResult:
        """Tool 실행"""
        executor = self._executors.get(self._tool_type_value)
        if not executor:
            return ToolResult(
                success=False,
                error=f"Unknown tool_type: {self._tool_type_value}",
            )

        try:
            return await executor(context, params)
        except Exception as e:
            logger.exception(f"DynamicTool {self._name} execution failed")
            return ToolResult(
                success=False,
                error=str(e),
                error_details={"tool_name": self._name, "params": params},
            )

    async def _execute_database_query(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> ToolResult:
        """데이터베이스 쿼리 실행"""
        source_ref = self._config.get("source_ref")
        query_ref = self._config.get("query_ref")
        query_template = self._config.get("query_template")
        timeout_ms = self._config.get("timeout_ms", 30000)

        # Source 로드
        source, err = await load_source_asset(source_ref)
        if err:
            return ToolResult(success=False, error=f"Source load failed: {err}")

        # Query 로드 또는 템플릿 사용
        if query_ref:
            from app.modules.asset_registry.loader import load_query_asset
            query, err = await load_query_asset(query_ref)
            if err:
                return ToolResult(success=False, error=f"Query load failed: {err}")
            sql = query.get("query_sql")
        elif query_template:
            # 템플릿 변수 치환
            sql = self._render_template(query_template, params)
        else:
            return ToolResult(
                success=False,
                error="Either query_ref or query_template required",
            )

        # 쿼리 실행
        from app.modules.ops.services.ci.tools.database_executor import (
            execute_query,
        )

        result = await asyncio.wait_for(
            execute_query(source, sql, params),
            timeout=timeout_ms / 1000,
        )

        return ToolResult(
            success=True,
            data=result,
            metadata={"tool_name": self._name, "query_type": "database"},
        )

    async def _execute_http_api(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> ToolResult:
        """HTTP API 호출"""
        base_url = self._config.get("base_url")
        endpoint = self._config.get("endpoint", "")
        method = self._config.get("method", "GET").upper()
        headers = self._config.get("headers", {})
        timeout_ms = self._config.get("timeout_ms", 30000)

        # URL 조립
        url = f"{base_url}{endpoint}"
        url = self._render_template(url, params)

        # 인증 처리
        auth_type = self._config.get("auth_type")
        if auth_type == "bearer":
            token_ref = self._config.get("token_ref")
            # 토큰 로드 로직...
            # headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=params)
            else:
                return ToolResult(
                    success=False,
                    error=f"Unsupported method: {method}",
                )

            response.raise_for_status()
            data = response.json()

        return ToolResult(
            success=True,
            data=data,
            metadata={"tool_name": self._name, "status_code": response.status_code},
        )

    async def _execute_graph_query(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> ToolResult:
        """그래프 쿼리 실행"""
        source_ref = self._config.get("source_ref")
        cypher_template = self._config.get("cypher_template")
        timeout_ms = self._config.get("timeout_ms", 60000)

        # Source 로드
        source, err = await load_source_asset(source_ref)
        if err:
            return ToolResult(success=False, error=f"Source load failed: {err}")

        # Cypher 템플릿 렌더링
        cypher = self._render_template(cypher_template, params)

        # Neo4j 쿼리 실행
        from app.modules.ops.services.ci.tools.graph_executor import (
            execute_cypher,
        )

        result = await asyncio.wait_for(
            execute_cypher(source, cypher, params),
            timeout=timeout_ms / 1000,
        )

        return ToolResult(
            success=True,
            data=result,
            metadata={"tool_name": self._name, "query_type": "graph"},
        )

    async def _execute_custom(
        self, context: ToolContext, params: Dict[str, Any]
    ) -> ToolResult:
        """커스텀 실행 (향후 확장)"""
        return ToolResult(
            success=False,
            error="Custom execution not yet implemented",
        )

    def _render_template(self, template: str, params: Dict[str, Any]) -> str:
        """템플릿 변수 치환"""
        result = template
        for key, value in params.items():
            placeholder = f"{{{{{key}}}}}"  # {{key}} 형식
            if isinstance(value, (list, dict)):
                import json
                value = json.dumps(value)
            result = result.replace(placeholder, str(value))
        return result
```

### 5.3 ToolRegistry 확장

```python
# apps/api/app/modules/ops/services/ci/tools/base.py 수정

class ToolRegistry:
    """Tool 레지스트리 (확장)"""

    def __init__(self):
        self._tools: Dict[str, Type[BaseTool]] = {}
        self._instances: Dict[str, BaseTool] = {}
        self._dynamic_tools: Dict[str, BaseTool] = {}  # 동적 Tool 별도 관리

    def register_dynamic(self, tool_asset: Dict[str, Any]) -> None:
        """
        Tool Asset으로부터 동적 Tool 등록

        Args:
            tool_asset: Tool Asset 딕셔너리
        """
        from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool

        name = tool_asset["name"]
        if name in self._dynamic_tools:
            logger.warning(f"Dynamic tool '{name}' already registered; replacing")

        tool = DynamicTool(tool_asset)
        self._dynamic_tools[name] = tool
        # 통합 인스턴스에도 추가 (하위 호환)
        self._instances[name] = tool
        logger.info(f"Registered dynamic tool: {name}")

    def load_from_db(self) -> int:
        """
        DB에서 발행된 모든 Tool Asset을 로드하여 등록

        Returns:
            등록된 Tool 수
        """
        import asyncio
        from app.modules.asset_registry.loader import load_all_published_tools

        # 동기 컨텍스트에서 비동기 호출
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        tool_assets = loop.run_until_complete(load_all_published_tools())

        count = 0
        for asset in tool_assets:
            try:
                self.register_dynamic(asset)
                count += 1
            except Exception as e:
                logger.error(f"Failed to register tool '{asset.get('name')}': {e}")

        logger.info(f"Loaded {count} dynamic tools from database")
        return count

    def reload_tools(self) -> int:
        """
        동적 Tool 전체 리로드 (핫 리로드용)

        Returns:
            등록된 Tool 수
        """
        # 기존 동적 Tool 제거
        for name in list(self._dynamic_tools.keys()):
            del self._instances[name]
        self._dynamic_tools.clear()

        # DB에서 다시 로드
        return self.load_from_db()

    def get_dynamic_tools(self) -> Dict[str, BaseTool]:
        """동적 Tool 목록 반환"""
        return self._dynamic_tools.copy()

    def get_tool_descriptions(self) -> list[Dict[str, str]]:
        """
        모든 Tool의 이름과 설명 반환 (LLM Tool 선택용)

        Returns:
            [{"name": "...", "description": "...", "input_schema": {...}}, ...]
        """
        descriptions = []

        for name, tool in self._instances.items():
            desc = {
                "name": name,
                "description": getattr(tool, "description", ""),
            }
            if hasattr(tool, "input_schema"):
                desc["input_schema"] = tool.input_schema
            descriptions.append(desc)

        return descriptions
```

### 5.4 registry_init.py 수정

```python
# apps/api/app/modules/ops/services/ci/tools/registry_init.py

"""
Tool Registry 초기화

하드코딩된 Tool과 DB에서 로드한 동적 Tool을 모두 등록합니다.
"""

from app.modules.ops.services.ci.tools.base import (
    get_tool_registry,
    register_tool,
    CommonToolTypes,
)
from app.modules.ops.services.ci.tools.ci_tool import CITool
from app.modules.ops.services.ci.tools.graph_tool import GraphTool
from app.modules.ops.services.ci.tools.metric_tool import MetricTool
from app.modules.ops.services.ci.tools.history_tool import HistoryTool
from app.modules.ops.services.ci.tools.cep_tool import CEPTool

from core.logging import get_logger

logger = get_logger(__name__)

_initialized = False


def initialize_tools() -> None:
    """
    Tool Registry 초기화

    1. 하드코딩된 기본 Tool 등록 (하위 호환)
    2. DB에서 동적 Tool 로드
    """
    global _initialized
    if _initialized:
        logger.debug("Tool registry already initialized")
        return

    registry = get_tool_registry()

    # ===== 1. 하드코딩된 기본 Tool (하위 호환) =====
    logger.info("Registering built-in tools...")
    register_tool(CommonToolTypes.CI, CITool)
    register_tool(CommonToolTypes.GRAPH, GraphTool)
    register_tool(CommonToolTypes.METRIC, MetricTool)
    register_tool(CommonToolTypes.HISTORY, HistoryTool)
    register_tool(CommonToolTypes.CEP, CEPTool)
    logger.info(f"Registered {len(registry.get_available_tools())} built-in tools")

    # ===== 2. DB에서 동적 Tool 로드 =====
    try:
        logger.info("Loading dynamic tools from database...")
        count = registry.load_from_db()
        logger.info(f"Loaded {count} dynamic tools from database")
    except Exception as e:
        logger.error(f"Failed to load dynamic tools: {e}")
        # DB 연결 실패해도 기본 Tool은 사용 가능

    _initialized = True
    logger.info(
        f"Tool registry initialized with {len(registry.get_available_tools())} total tools"
    )


def reload_dynamic_tools() -> int:
    """
    동적 Tool 리로드 (Admin UI에서 Tool 변경 시 호출)

    Returns:
        리로드된 Tool 수
    """
    registry = get_tool_registry()
    return registry.reload_tools()
```

---

## 6. Phase 3: 범용 Planner

### 6.1 체크리스트

- [ ] **P3-1**: 데이터 구조 정의
  - [ ] `ToolSelection` 스키마
  - [ ] `GenericPlan` 스키마
- [ ] **P3-2**: LLM Tool Selector 구현
  - [ ] `tool_selector_llm.py` 파일 생성
  - [ ] Tool description 수집
  - [ ] LLM 프롬프트 구성
  - [ ] 응답 파싱
- [ ] **P3-3**: GenericPlanner 구현
  - [ ] `generic_planner.py` 파일 생성
  - [ ] BaseDomainPlanner 상속
  - [ ] should_handle() 구현
  - [ ] create_plan() 구현
- [ ] **P3-4**: 프롬프트 Asset 추가
  - [ ] `tool_selector.yaml` 프롬프트
- [ ] **P3-5**: 테스트 작성 및 실행

### 6.2 데이터 구조

```python
# apps/api/app/modules/ops/services/ci/planner/plan_schema.py

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal


class ToolSelection(BaseModel):
    """LLM이 선택한 Tool 정보"""

    tool_name: str = Field(..., description="선택된 Tool 이름")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="선택 신뢰도 (0.0~1.0)"
    )
    reasoning: str = Field(..., description="Tool 선택 이유")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Tool에 전달할 파라미터"
    )


class GenericPlan(BaseModel):
    """범용 실행 계획"""

    question: str = Field(..., description="원본 질문")
    selected_tools: List[ToolSelection] = Field(
        default_factory=list, description="선택된 Tool 목록"
    )
    execution_order: Literal["sequential", "parallel", "dag"] = Field(
        default="sequential", description="실행 순서"
    )
    chain_config: Dict[str, Any] | None = Field(
        default=None, description="체이닝 설정 (output→input 매핑)"
    )

    @property
    def primary_tool(self) -> ToolSelection | None:
        """가장 높은 신뢰도의 Tool 반환"""
        if not self.selected_tools:
            return None
        return max(self.selected_tools, key=lambda t: t.confidence)

    @property
    def tool_names(self) -> List[str]:
        """선택된 Tool 이름 목록"""
        return [t.tool_name for t in self.selected_tools]
```

### 6.3 LLM Tool Selector

```python
# apps/api/app/modules/ops/services/domain/tool_selector_llm.py

"""
LLM 기반 Tool Selector

등록된 Tool들의 description을 보고 질문에 적합한 Tool을 선택합니다.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from app.modules.ops.services.ci.planner.plan_schema import ToolSelection
from app.modules.ops.services.ci.tools.base import get_tool_registry
from app.modules.asset_registry.loader import load_prompt_asset
from core.llm import create_llm_response
from core.logging import get_logger

logger = get_logger(__name__)


class LLMToolSelector:
    """LLM 기반 Tool 선택기"""

    def __init__(self):
        self._prompt_template: str | None = None

    async def _load_prompt(self) -> str:
        """Tool 선택 프롬프트 로드"""
        if self._prompt_template:
            return self._prompt_template

        prompt_asset, err = await load_prompt_asset("tool_selector")
        if err:
            logger.warning(f"Failed to load tool_selector prompt: {err}")
            # Fallback 프롬프트
            self._prompt_template = self._get_fallback_prompt()
        else:
            self._prompt_template = prompt_asset.get("template", "")

        return self._prompt_template

    def _get_fallback_prompt(self) -> str:
        """Fallback 프롬프트"""
        return """당신은 사용자 질문에 적합한 도구(Tool)를 선택하는 AI입니다.

사용 가능한 도구 목록:
{tool_descriptions}

사용자 질문:
{question}

응답 형식 (JSON):
{{
  "tools": [
    {{
      "tool_name": "도구 이름",
      "confidence": 0.0~1.0 사이의 신뢰도,
      "reasoning": "선택 이유",
      "parameters": {{"파라미터명": "값"}}
    }}
  ],
  "execution_order": "sequential" 또는 "parallel"
}}

주의사항:
1. 질문에 가장 적합한 도구를 선택하세요
2. 여러 도구가 필요하면 모두 선택하세요
3. 도구 순서가 중요하면 sequential, 독립적이면 parallel로 지정하세요
4. 파라미터는 질문에서 추출할 수 있는 값만 포함하세요

JSON 응답:"""

    def _build_tool_descriptions(self) -> str:
        """등록된 Tool들의 description 수집"""
        registry = get_tool_registry()
        descriptions = registry.get_tool_descriptions()

        lines = []
        for desc in descriptions:
            name = desc["name"]
            description = desc.get("description", "(설명 없음)")
            input_schema = desc.get("input_schema", {})

            # 입력 파라미터 요약
            props = input_schema.get("properties", {})
            params_str = ", ".join(props.keys()) if props else "(파라미터 없음)"

            lines.append(f"- {name}: {description}")
            lines.append(f"  입력: {params_str}")

        return "\n".join(lines)

    async def select_tools(
        self, question: str, context: Dict[str, Any] | None = None
    ) -> List[ToolSelection]:
        """
        질문에 적합한 Tool 선택

        Args:
            question: 사용자 질문
            context: 추가 컨텍스트 (이전 대화, 세션 정보 등)

        Returns:
            선택된 Tool 목록
        """
        # 프롬프트 구성
        template = await self._load_prompt()
        tool_descriptions = self._build_tool_descriptions()

        prompt = template.format(
            tool_descriptions=tool_descriptions,
            question=question,
        )

        # LLM 호출
        response = await create_llm_response(
            prompt=prompt,
            temperature=0.1,  # 일관된 결과를 위해 낮은 온도
            max_tokens=1000,
        )

        # 응답 파싱
        try:
            result = self._parse_response(response)
            logger.info(
                f"Selected {len(result)} tools for question: {question[:50]}..."
            )
            return result
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return []

    def _parse_response(self, response: str) -> List[ToolSelection]:
        """LLM 응답 파싱"""
        # JSON 추출
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        data = json.loads(response.strip())
        tools_data = data.get("tools", [])

        result = []
        for tool in tools_data:
            selection = ToolSelection(
                tool_name=tool["tool_name"],
                confidence=float(tool.get("confidence", 0.5)),
                reasoning=tool.get("reasoning", ""),
                parameters=tool.get("parameters", {}),
            )
            result.append(selection)

        return result
```

### 6.4 GenericPlanner

```python
# apps/api/app/modules/ops/services/domain/generic_planner.py

"""
범용 Planner

도메인에 관계없이 LLM이 Tool을 선택하여 질문에 응답합니다.
"""

from __future__ import annotations

from typing import Any, Dict

from app.modules.ops.services.ci.planner.plan_schema import GenericPlan
from app.modules.ops.services.domain.tool_selector_llm import LLMToolSelector
from app.modules.ops.services.ci.tools.base import ToolContext
from core.logging import get_logger

logger = get_logger(__name__)


class GenericPlanner:
    """
    범용 Planner

    LLM 기반 Tool 선택을 통해 모든 도메인의 질문을 처리합니다.
    """

    def __init__(self):
        self._tool_selector = LLMToolSelector()

    @property
    def domain(self) -> str:
        return "generic"

    async def should_handle(self, question: str) -> bool:
        """
        이 Planner가 질문을 처리할 수 있는지 확인

        GenericPlanner는 모든 질문을 처리할 수 있음 (fallback)
        """
        return True

    async def create_plan(
        self,
        question: str,
        context: ToolContext,
        options: Dict[str, Any] | None = None,
    ) -> GenericPlan:
        """
        질문에 대한 실행 계획 생성

        Args:
            question: 사용자 질문
            context: 실행 컨텍스트
            options: 추가 옵션

        Returns:
            GenericPlan
        """
        logger.info(f"Creating plan for: {question[:50]}...")

        # LLM으로 Tool 선택
        selected_tools = await self._tool_selector.select_tools(
            question=question,
            context={"tenant_id": context.tenant_id},
        )

        if not selected_tools:
            logger.warning("No tools selected by LLM")

        # 체이닝 설정 분석 (향후 확장)
        chain_config = self._analyze_chaining(selected_tools, question)

        plan = GenericPlan(
            question=question,
            selected_tools=selected_tools,
            execution_order=self._determine_execution_order(selected_tools),
            chain_config=chain_config,
        )

        logger.info(
            f"Plan created: {len(selected_tools)} tools, "
            f"order={plan.execution_order}"
        )

        return plan

    def _determine_execution_order(self, tools: list) -> str:
        """실행 순서 결정"""
        if len(tools) <= 1:
            return "sequential"

        # 도구 간 의존성 분석 (간단 버전)
        # 향후: DAG 분석으로 확장
        return "sequential"

    def _analyze_chaining(self, tools: list, question: str) -> Dict[str, Any] | None:
        """체이닝 설정 분석"""
        if len(tools) <= 1:
            return None

        # 향후: 도구 간 output→input 매핑 분석
        return None
```

### 6.5 Tool Selector 프롬프트

```yaml
# apps/api/resources/prompts/generic/tool_selector.yaml
name: tool_selector
description: LLM Tool 선택기 프롬프트
scope: generic
engine: openai
template: |
  당신은 사용자 질문에 적합한 도구(Tool)를 선택하는 AI 어시스턴트입니다.

  ## 사용 가능한 도구
  {tool_descriptions}

  ## 사용자 질문
  {question}

  ## 응답 지침
  1. 질문을 분석하여 가장 적합한 도구를 선택하세요
  2. 여러 도구가 필요하면 순서대로 모두 선택하세요
  3. 질문에서 추출할 수 있는 파라미터를 포함하세요
  4. 확신이 낮으면 confidence를 낮게 설정하세요

  ## 응답 형식 (반드시 JSON으로 응답)
  {{
    "tools": [
      {{
        "tool_name": "도구 이름",
        "confidence": 0.95,
        "reasoning": "이 도구를 선택한 이유",
        "parameters": {{
          "keyword": "추출된 값"
        }}
      }}
    ],
    "execution_order": "sequential"
  }}

  JSON 응답:
input_schema:
  type: object
  properties:
    tool_descriptions:
      type: string
      description: 사용 가능한 도구 목록
    question:
      type: string
      description: 사용자 질문
  required:
    - tool_descriptions
    - question
output_contract:
  type: object
  properties:
    tools:
      type: array
    execution_order:
      type: string
```

---

## 7. Phase 4: Tool 체이닝 실행기

### 7.1 체크리스트

- [ ] **P4-1**: 데이터 구조 정의
  - [ ] `ToolChainStep` 스키마
  - [ ] `ToolChain` 스키마
  - [ ] `ChainExecutionResult` 스키마
- [ ] **P4-2**: Chain Executor 구현
  - [ ] `chain_executor.py` 파일 생성
  - [ ] Sequential 실행
  - [ ] Parallel 실행
  - [ ] DAG 실행
  - [ ] Output→Input 매핑
- [ ] **P4-3**: Generic Runner 구현
  - [ ] `generic_runner.py` 파일 생성
  - [ ] GenericPlanner 연동
  - [ ] ChainExecutor 연동
- [ ] **P4-4**: 테스트 작성 및 실행

### 7.2 데이터 구조

```python
# apps/api/app/modules/ops/schemas.py (추가)

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal


class ToolChainStep(BaseModel):
    """Tool 체인의 단일 스텝"""

    step_id: str = Field(..., description="스텝 고유 ID")
    tool_name: str = Field(..., description="실행할 Tool 이름")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Tool 파라미터"
    )
    depends_on: List[str] = Field(
        default_factory=list, description="의존하는 step_id 목록"
    )
    output_mapping: Dict[str, str] = Field(
        default_factory=dict,
        description="이전 스텝 결과 → 파라미터 매핑 (예: {'ci_id': 'step1.records[0].ci_id'})"
    )
    timeout_ms: int = Field(default=30000, description="타임아웃 (ms)")
    retry_count: int = Field(default=0, description="재시도 횟수")


class ToolChain(BaseModel):
    """Tool 실행 체인"""

    chain_id: str = Field(..., description="체인 고유 ID")
    steps: List[ToolChainStep] = Field(..., description="스텝 목록")
    execution_mode: Literal["sequential", "parallel", "dag"] = Field(
        default="sequential", description="실행 모드"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="체인 메타데이터"
    )


class StepResult(BaseModel):
    """단일 스텝 실행 결과"""

    step_id: str
    success: bool
    data: Any = None
    error: str | None = None
    execution_time_ms: int = 0


class ChainExecutionResult(BaseModel):
    """체인 실행 결과"""

    chain_id: str
    success: bool
    step_results: Dict[str, StepResult] = Field(default_factory=dict)
    final_output: Any = None
    total_execution_time_ms: int = 0
    failed_steps: List[str] = Field(default_factory=list)
```

### 7.3 Chain Executor

```python
# apps/api/app/modules/ops/services/ci/orchestrator/chain_executor.py

"""
Tool Chain Executor

여러 Tool을 순차/병렬/DAG 방식으로 실행하고 결과를 파이프라인합니다.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Dict, List

from app.modules.ops.schemas import (
    ToolChain,
    ToolChainStep,
    ChainExecutionResult,
    StepResult,
)
from app.modules.ops.services.ci.tools.base import (
    get_tool_registry,
    ToolContext,
    ToolResult,
)
from core.logging import get_logger

logger = get_logger(__name__)


class ToolChainExecutor:
    """Tool 체인 실행기"""

    def __init__(self):
        self._registry = get_tool_registry()

    async def execute_chain(
        self, chain: ToolChain, context: ToolContext
    ) -> ChainExecutionResult:
        """
        Tool 체인 실행

        Args:
            chain: 실행할 체인
            context: 실행 컨텍스트

        Returns:
            ChainExecutionResult
        """
        start_time = time.time()
        logger.info(f"Executing chain {chain.chain_id} with {len(chain.steps)} steps")

        if chain.execution_mode == "parallel":
            result = await self._execute_parallel(chain, context)
        elif chain.execution_mode == "dag":
            result = await self._execute_dag(chain, context)
        else:  # sequential
            result = await self._execute_sequential(chain, context)

        result.total_execution_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Chain {chain.chain_id} completed: "
            f"success={result.success}, "
            f"time={result.total_execution_time_ms}ms"
        )

        return result

    async def _execute_sequential(
        self, chain: ToolChain, context: ToolContext
    ) -> ChainExecutionResult:
        """순차 실행"""
        step_results: Dict[str, StepResult] = {}
        failed_steps: List[str] = []

        for step in chain.steps:
            # 파라미터 매핑 (이전 결과 참조)
            params = self._merge_params(step, step_results)

            # Tool 실행
            step_result = await self._execute_step(step, params, context)
            step_results[step.step_id] = step_result

            if not step_result.success:
                failed_steps.append(step.step_id)
                # 순차 실행에서 실패 시 중단
                break

        # 마지막 성공한 스텝의 결과를 최종 출력으로
        final_output = None
        for step in reversed(chain.steps):
            if step.step_id in step_results and step_results[step.step_id].success:
                final_output = step_results[step.step_id].data
                break

        return ChainExecutionResult(
            chain_id=chain.chain_id,
            success=len(failed_steps) == 0,
            step_results=step_results,
            final_output=final_output,
            failed_steps=failed_steps,
        )

    async def _execute_parallel(
        self, chain: ToolChain, context: ToolContext
    ) -> ChainExecutionResult:
        """병렬 실행"""
        tasks = []
        for step in chain.steps:
            params = self._merge_params(step, {})  # 병렬은 이전 결과 참조 불가
            task = self._execute_step(step, params, context)
            tasks.append((step.step_id, task))

        # 병렬 실행
        results = await asyncio.gather(
            *[t[1] for t in tasks], return_exceptions=True
        )

        step_results: Dict[str, StepResult] = {}
        failed_steps: List[str] = []

        for i, (step_id, _) in enumerate(tasks):
            result = results[i]
            if isinstance(result, Exception):
                step_results[step_id] = StepResult(
                    step_id=step_id,
                    success=False,
                    error=str(result),
                )
                failed_steps.append(step_id)
            else:
                step_results[step_id] = result
                if not result.success:
                    failed_steps.append(step_id)

        # 모든 결과를 리스트로 병합
        final_output = [
            step_results[step.step_id].data
            for step in chain.steps
            if step_results.get(step.step_id, {}).success
        ]

        return ChainExecutionResult(
            chain_id=chain.chain_id,
            success=len(failed_steps) == 0,
            step_results=step_results,
            final_output=final_output,
            failed_steps=failed_steps,
        )

    async def _execute_dag(
        self, chain: ToolChain, context: ToolContext
    ) -> ChainExecutionResult:
        """DAG 기반 실행 (의존성 순서 고려)"""
        step_results: Dict[str, StepResult] = {}
        failed_steps: List[str] = []
        completed: set = set()

        # 의존성 그래프 구축
        step_map = {s.step_id: s for s in chain.steps}

        while len(completed) < len(chain.steps):
            # 실행 가능한 스텝 찾기 (의존성 모두 완료된 스텝)
            ready_steps = []
            for step in chain.steps:
                if step.step_id in completed:
                    continue
                if all(dep in completed for dep in step.depends_on):
                    ready_steps.append(step)

            if not ready_steps:
                # 데드락 또는 모든 완료
                if len(completed) < len(chain.steps):
                    logger.error("DAG deadlock detected")
                    break
                break

            # 준비된 스텝 병렬 실행
            tasks = []
            for step in ready_steps:
                params = self._merge_params(step, step_results)
                task = self._execute_step(step, params, context)
                tasks.append((step.step_id, task))

            results = await asyncio.gather(
                *[t[1] for t in tasks], return_exceptions=True
            )

            for i, (step_id, _) in enumerate(tasks):
                result = results[i]
                if isinstance(result, Exception):
                    step_results[step_id] = StepResult(
                        step_id=step_id,
                        success=False,
                        error=str(result),
                    )
                    failed_steps.append(step_id)
                else:
                    step_results[step_id] = result
                    if not result.success:
                        failed_steps.append(step_id)
                completed.add(step_id)

        # 마지막 스텝 결과를 최종 출력으로
        final_output = None
        if chain.steps:
            last_step = chain.steps[-1]
            if last_step.step_id in step_results:
                final_output = step_results[last_step.step_id].data

        return ChainExecutionResult(
            chain_id=chain.chain_id,
            success=len(failed_steps) == 0,
            step_results=step_results,
            final_output=final_output,
            failed_steps=failed_steps,
        )

    async def _execute_step(
        self, step: ToolChainStep, params: Dict[str, Any], context: ToolContext
    ) -> StepResult:
        """단일 스텝 실행"""
        start_time = time.time()

        try:
            tool = self._registry.get_tool(step.tool_name)
        except ValueError as e:
            return StepResult(
                step_id=step.step_id,
                success=False,
                error=f"Tool not found: {step.tool_name}",
            )

        try:
            result: ToolResult = await asyncio.wait_for(
                tool.safe_execute(context, params),
                timeout=step.timeout_ms / 1000,
            )

            return StepResult(
                step_id=step.step_id,
                success=result.success,
                data=result.data,
                error=result.error,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        except asyncio.TimeoutError:
            return StepResult(
                step_id=step.step_id,
                success=False,
                error=f"Timeout after {step.timeout_ms}ms",
                execution_time_ms=step.timeout_ms,
            )
        except Exception as e:
            return StepResult(
                step_id=step.step_id,
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def _merge_params(
        self, step: ToolChainStep, prev_results: Dict[str, StepResult]
    ) -> Dict[str, Any]:
        """
        이전 스텝 결과에서 파라미터 매핑

        output_mapping 예시:
        - {"ci_id": "step1.data.records[0].ci_id"}
        - {"keywords": "step1.data.keywords"}
        """
        params = dict(step.parameters)

        for param_name, path in step.output_mapping.items():
            value = self._resolve_path(path, prev_results)
            if value is not None:
                params[param_name] = value

        return params

    def _resolve_path(
        self, path: str, results: Dict[str, StepResult]
    ) -> Any:
        """
        경로 표현식 해석

        예: "step1.data.records[0].ci_id"
        """
        parts = path.split(".")
        if not parts:
            return None

        step_id = parts[0]
        if step_id not in results:
            return None

        current = results[step_id]
        for part in parts[1:]:
            if current is None:
                return None

            # 배열 인덱스 처리 (예: records[0])
            match = re.match(r"(\w+)\[(\d+)\]", part)
            if match:
                attr, index = match.groups()
                current = getattr(current, attr, None)
                if current is None:
                    current = current.get(attr) if isinstance(current, dict) else None
                if isinstance(current, list) and int(index) < len(current):
                    current = current[int(index)]
                else:
                    return None
            else:
                # 일반 속성 접근
                if hasattr(current, part):
                    current = getattr(current, part)
                elif isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None

        return current
```

### 7.4 체이닝 예시

```json
{
  "chain_id": "chain_001",
  "execution_mode": "sequential",
  "steps": [
    {
      "step_id": "search_ci",
      "tool_name": "ci_search",
      "parameters": {"keywords": ["sys-order-01"]},
      "timeout_ms": 30000
    },
    {
      "step_id": "get_incidents",
      "tool_name": "incident_log",
      "depends_on": ["search_ci"],
      "output_mapping": {
        "ci_id": "search_ci.data.records[0].ci_id"
      },
      "timeout_ms": 30000
    },
    {
      "step_id": "get_guide",
      "tool_name": "work_guide",
      "depends_on": ["get_incidents"],
      "output_mapping": {
        "incident_type": "get_incidents.data.records[0].type"
      },
      "timeout_ms": 30000
    }
  ]
}
```

---

## 8. Phase 5: Admin UI

### 8.1 체크리스트

- [ ] **P5-1**: Tool 목록 페이지
  - [ ] `/admin/tools/page.tsx` 생성
  - [ ] AG Grid 테이블 구현
  - [ ] 필터/검색 기능
- [ ] **P5-2**: Tool 관리 패널
  - [ ] `ToolAssetPanel.tsx` 생성
  - [ ] 기본 정보 편집
  - [ ] JSON Schema 에디터
- [ ] **P5-3**: Tool 생성 모달
  - [ ] `CreateToolModal.tsx` 생성
  - [ ] Tool 타입 선택
  - [ ] Source 연결
- [ ] **P5-4**: Tool 테스트 패널
  - [ ] `ToolTestPanel.tsx` 생성
  - [ ] 입력 JSON 에디터
  - [ ] 결과 뷰어
- [ ] **P5-5**: AdminDashboard 수정
  - [ ] Tools 탭 추가
- [ ] **P5-6**: API 엔드포인트 추가
  - [ ] Tool CRUD API
  - [ ] Tool 테스트 API
- [ ] **P5-7**: 테스트 작성 및 실행

### 8.2 Tool 목록 페이지

```tsx
// apps/web/src/app/admin/tools/page.tsx

"use client";

import { useState, useEffect, useCallback } from "react";
import { AgGridReact } from "ag-grid-react";
import { ColDef, ICellRendererParams } from "ag-grid-community";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import { CreateToolModal } from "@/components/admin/CreateToolModal";
import { ToolAssetPanel } from "@/components/admin/ToolAssetPanel";
import { ToolTestPanel } from "@/components/admin/ToolTestPanel";

import { apiClient } from "@/lib/apiClient";

interface ToolAsset {
  asset_id: string;
  name: string;
  description: string | null;
  tool_type: string;
  status: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export default function ToolsPage() {
  const [tools, setTools] = useState<ToolAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTool, setSelectedTool] = useState<ToolAsset | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showTestPanel, setShowTestPanel] = useState(false);

  // 필터
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchTools = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (statusFilter !== "all") params.status = statusFilter;
      if (typeFilter !== "all") params.tool_type = typeFilter;

      const response = await apiClient.get("/api/asset-registry/tools", { params });
      setTools(response.data.assets || []);
    } catch (error) {
      console.error("Failed to fetch tools:", error);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, typeFilter]);

  useEffect(() => {
    fetchTools();
  }, [fetchTools]);

  const columnDefs: ColDef<ToolAsset>[] = [
    {
      field: "name",
      headerName: "Tool Name",
      flex: 1,
      filter: true,
    },
    {
      field: "tool_type",
      headerName: "Type",
      width: 150,
      cellRenderer: (params: ICellRendererParams) => (
        <span className="px-2 py-1 rounded text-xs bg-blue-100 text-blue-800">
          {params.value}
        </span>
      ),
    },
    {
      field: "status",
      headerName: "Status",
      width: 100,
      cellRenderer: (params: ICellRendererParams) => (
        <span
          className={`px-2 py-1 rounded text-xs ${
            params.value === "published"
              ? "bg-green-100 text-green-800"
              : "bg-yellow-100 text-yellow-800"
          }`}
        >
          {params.value}
        </span>
      ),
    },
    {
      field: "version",
      headerName: "Ver",
      width: 70,
    },
    {
      field: "updated_at",
      headerName: "Updated",
      width: 150,
      valueFormatter: (params) =>
        new Date(params.value).toLocaleDateString("ko-KR"),
    },
    {
      headerName: "Actions",
      width: 200,
      cellRenderer: (params: ICellRendererParams<ToolAsset>) => (
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setSelectedTool(params.data!)}
          >
            Edit
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setSelectedTool(params.data!);
              setShowTestPanel(true);
            }}
          >
            Test
          </Button>
          {params.data?.status === "draft" && (
            <Button
              size="sm"
              onClick={() => handlePublish(params.data!.asset_id)}
            >
              Publish
            </Button>
          )}
        </div>
      ),
    },
  ];

  const handlePublish = async (assetId: string) => {
    try {
      await apiClient.post(`/api/asset-registry/tools/${assetId}/publish`);
      fetchTools();
    } catch (error) {
      console.error("Failed to publish tool:", error);
    }
  };

  const handleCreate = async (data: any) => {
    try {
      await apiClient.post("/api/asset-registry/tools", data);
      setShowCreateModal(false);
      fetchTools();
    } catch (error) {
      console.error("Failed to create tool:", error);
    }
  };

  const filteredTools = tools.filter((tool) =>
    tool.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-full flex flex-col p-4">
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Tool Management</h1>
        <Button onClick={() => setShowCreateModal(true)}>+ New Tool</Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-4">
        <Input
          placeholder="Search tools..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-64"
        />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="draft">Draft</SelectItem>
            <SelectItem value="published">Published</SelectItem>
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="database_query">Database Query</SelectItem>
            <SelectItem value="http_api">HTTP API</SelectItem>
            <SelectItem value="graph_query">Graph Query</SelectItem>
            <SelectItem value="custom">Custom</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Grid */}
      <div className="flex-1 ag-theme-alpine">
        <AgGridReact
          rowData={filteredTools}
          columnDefs={columnDefs}
          loading={loading}
          rowSelection="single"
          onRowClicked={(e) => setSelectedTool(e.data)}
        />
      </div>

      {/* Modals & Panels */}
      {showCreateModal && (
        <CreateToolModal
          onClose={() => setShowCreateModal(false)}
          onSave={handleCreate}
        />
      )}

      {selectedTool && !showTestPanel && (
        <ToolAssetPanel
          tool={selectedTool}
          onClose={() => setSelectedTool(null)}
          onUpdate={fetchTools}
        />
      )}

      {selectedTool && showTestPanel && (
        <ToolTestPanel
          tool={selectedTool}
          onClose={() => {
            setShowTestPanel(false);
            setSelectedTool(null);
          }}
        />
      )}
    </div>
  );
}
```

### 8.3 Tool 생성 모달

```tsx
// apps/web/src/components/admin/CreateToolModal.tsx

"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { JsonEditor } from "@/components/admin/JsonEditor";

interface CreateToolModalProps {
  onClose: () => void;
  onSave: (data: any) => Promise<void>;
}

const TOOL_TYPES = [
  { value: "database_query", label: "Database Query" },
  { value: "http_api", label: "HTTP API" },
  { value: "graph_query", label: "Graph Query" },
  { value: "custom", label: "Custom" },
];

const DEFAULT_INPUT_SCHEMA = {
  type: "object",
  properties: {
    keywords: {
      type: "array",
      items: { type: "string" },
      description: "Search keywords",
    },
  },
  required: ["keywords"],
};

const DEFAULT_CONFIG = {
  database_query: {
    source_ref: "",
    query_ref: "",
    timeout_ms: 30000,
  },
  http_api: {
    base_url: "",
    endpoint: "",
    method: "GET",
    headers: {},
    timeout_ms: 30000,
  },
  graph_query: {
    source_ref: "",
    cypher_template: "",
    timeout_ms: 60000,
  },
  custom: {},
};

export function CreateToolModal({ onClose, onSave }: CreateToolModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [toolType, setToolType] = useState("database_query");
  const [config, setConfig] = useState(DEFAULT_CONFIG.database_query);
  const [inputSchema, setInputSchema] = useState(DEFAULT_INPUT_SCHEMA);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleToolTypeChange = (type: string) => {
    setToolType(type);
    setConfig(DEFAULT_CONFIG[type as keyof typeof DEFAULT_CONFIG] || {});
  };

  const handleSave = async () => {
    if (!name.trim()) {
      setError("Tool name is required");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await onSave({
        name: name.trim(),
        description: description.trim() || null,
        tool_type: toolType,
        tool_config: config,
        tool_input_schema: inputSchema,
      });
    } catch (e: any) {
      setError(e.message || "Failed to create tool");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create New Tool</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {error && (
            <div className="p-3 bg-red-50 text-red-700 rounded">{error}</div>
          )}

          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="name">Tool Name *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., equipment_search"
              />
            </div>
            <div>
              <Label htmlFor="tool_type">Tool Type *</Label>
              <Select value={toolType} onValueChange={handleToolTypeChange}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TOOL_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe what this tool does. Include keywords that help LLM select this tool."
              rows={3}
            />
            <p className="text-xs text-gray-500 mt-1">
              LLM uses this description to select the appropriate tool.
            </p>
          </div>

          {/* Tool Config */}
          <div>
            <Label>Tool Configuration</Label>
            <JsonEditor
              value={config}
              onChange={setConfig}
              height="200px"
            />
          </div>

          {/* Input Schema */}
          <div>
            <Label>Input Schema (JSON Schema)</Label>
            <JsonEditor
              value={inputSchema}
              onChange={setInputSchema}
              height="200px"
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Creating..." : "Create Tool"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

### 8.4 Tool 테스트 패널

```tsx
// apps/web/src/components/admin/ToolTestPanel.tsx

"use client";

import { useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { JsonEditor } from "@/components/admin/JsonEditor";
import { JsonViewer } from "@/components/admin/JsonViewer";
import { apiClient } from "@/lib/apiClient";

interface ToolTestPanelProps {
  tool: {
    asset_id: string;
    name: string;
    tool_input_schema?: any;
  };
  onClose: () => void;
}

export function ToolTestPanel({ tool, onClose }: ToolTestPanelProps) {
  const [input, setInput] = useState<any>({});
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executionTime, setExecutionTime] = useState<number | null>(null);

  // 입력 스키마에서 기본값 생성
  const getDefaultInput = () => {
    const schema = tool.tool_input_schema;
    if (!schema?.properties) return {};

    const defaults: any = {};
    for (const [key, prop] of Object.entries(schema.properties) as any) {
      if (prop.default !== undefined) {
        defaults[key] = prop.default;
      } else if (prop.type === "array") {
        defaults[key] = [];
      } else if (prop.type === "object") {
        defaults[key] = {};
      } else if (prop.type === "string") {
        defaults[key] = "";
      } else if (prop.type === "integer" || prop.type === "number") {
        defaults[key] = 0;
      }
    }
    return defaults;
  };

  const handleTest = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    const startTime = Date.now();

    try {
      const response = await apiClient.post(
        `/api/asset-registry/tools/${tool.asset_id}/test`,
        input
      );
      setResult(response.data);
      setExecutionTime(Date.now() - startTime);
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || "Test failed");
      setExecutionTime(Date.now() - startTime);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setInput(getDefaultInput());
    setResult(null);
    setError(null);
    setExecutionTime(null);
  };

  return (
    <Sheet open onOpenChange={onClose}>
      <SheetContent className="w-[600px] sm:max-w-[600px]">
        <SheetHeader>
          <SheetTitle>Test: {tool.name}</SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-4">
          {/* Input */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="font-medium">Input Parameters</label>
              <Button size="sm" variant="ghost" onClick={handleReset}>
                Reset
              </Button>
            </div>
            <JsonEditor
              value={input}
              onChange={setInput}
              height="200px"
            />
          </div>

          {/* Run Button */}
          <div className="flex gap-2">
            <Button onClick={handleTest} disabled={loading} className="flex-1">
              {loading ? "Running..." : "Run Test"}
            </Button>
          </div>

          {/* Execution Time */}
          {executionTime !== null && (
            <div className="text-sm text-gray-500">
              Execution time: {executionTime}ms
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-50 text-red-700 rounded text-sm">
              {error}
            </div>
          )}

          {/* Result */}
          {result && (
            <div>
              <label className="font-medium">Result</label>
              <div className="mt-2 border rounded p-2 bg-gray-50 max-h-[400px] overflow-auto">
                <JsonViewer data={result} />
              </div>
            </div>
          )}

          {/* Schema Reference */}
          {tool.tool_input_schema && (
            <details className="text-sm">
              <summary className="cursor-pointer text-gray-600">
                Input Schema Reference
              </summary>
              <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-auto">
                {JSON.stringify(tool.tool_input_schema, null, 2)}
              </pre>
            </details>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

### 8.5 API 엔드포인트

```python
# apps/api/app/modules/asset_registry/router.py (추가)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.asset_registry.schemas import (
    ToolAssetCreate,
    ToolAssetRead,
    ToolAssetUpdate,
)
from app.modules.asset_registry import crud
from core.database import get_db

router = APIRouter(prefix="/api/asset-registry", tags=["asset-registry"])


@router.get("/tools")
async def list_tools(
    status: str | None = None,
    tool_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Tool Asset 목록 조회"""
    assets, total = await crud.list_tool_assets(
        db, status=status, tool_type=tool_type, limit=limit, offset=offset
    )
    return {
        "assets": [ToolAssetRead.model_validate(a) for a in assets],
        "total": total,
    }


@router.post("/tools")
async def create_tool(
    data: ToolAssetCreate,
    db: AsyncSession = Depends(get_db),
):
    """Tool Asset 생성"""
    asset = await crud.create_tool_asset(db, data)
    return ToolAssetRead.model_validate(asset)


@router.get("/tools/{asset_id}")
async def get_tool(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Tool Asset 조회"""
    asset = await crud.get_asset_by_id(db, asset_id)
    if not asset or asset.asset_type != "tool":
        raise HTTPException(status_code=404, detail="Tool not found")
    return ToolAssetRead.model_validate(asset)


@router.put("/tools/{asset_id}")
async def update_tool(
    asset_id: str,
    data: ToolAssetUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Tool Asset 수정"""
    asset = await crud.get_asset_by_id(db, asset_id)
    if not asset or asset.asset_type != "tool":
        raise HTTPException(status_code=404, detail="Tool not found")

    updated = await crud.update_tool_asset(db, asset_id, data)
    return ToolAssetRead.model_validate(updated)


@router.post("/tools/{asset_id}/publish")
async def publish_tool(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Tool Asset 발행"""
    asset = await crud.get_asset_by_id(db, asset_id)
    if not asset or asset.asset_type != "tool":
        raise HTTPException(status_code=404, detail="Tool not found")

    published = await crud.publish_asset(db, asset_id)

    # Tool Registry 리로드
    from app.modules.ops.services.ci.tools.registry_init import reload_dynamic_tools
    reload_dynamic_tools()

    return ToolAssetRead.model_validate(published)


@router.post("/tools/{asset_id}/test")
async def test_tool(
    asset_id: str,
    test_input: dict,
    db: AsyncSession = Depends(get_db),
):
    """Tool 테스트 실행"""
    from app.modules.ops.services.ci.tools.base import (
        get_tool_registry,
        ToolContext,
    )

    asset = await crud.get_asset_by_id(db, asset_id)
    if not asset or asset.asset_type != "tool":
        raise HTTPException(status_code=404, detail="Tool not found")

    # 테스트용 컨텍스트
    context = ToolContext(
        tenant_id="test",
        user_id="test_user",
        request_id="test_request",
    )

    # Tool 실행
    registry = get_tool_registry()

    # 발행되지 않은 Tool은 임시로 DynamicTool 생성
    if asset.status != "published":
        from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool

        tool = DynamicTool({
            "name": asset.name,
            "description": asset.description,
            "tool_type": asset.tool_type,
            "tool_config": asset.tool_config,
            "tool_input_schema": asset.tool_input_schema,
        })
    else:
        tool = registry.get_tool(asset.name)

    result = await tool.safe_execute(context, test_input)

    return {
        "success": result.success,
        "data": result.data,
        "error": result.error,
        "metadata": result.metadata,
    }
```

---

## 9. 테스트 계획

### 9.1 단위 테스트 (Unit Tests)

#### Phase 0 테스트

```python
# tests/unit/ops/planner/test_mapping_loader.py

import pytest
from unittest.mock import patch, AsyncMock


class TestMappingLoader:
    """Mapping Asset 로더 테스트"""

    @pytest.mark.asyncio
    async def test_load_ci_code_patterns_from_db(self, db_session):
        """DB에서 CI 코드 패턴 로드"""
        from app.modules.ops.services.ci.planner.planner_llm import (
            _get_ci_code_patterns,
        )

        patterns = _get_ci_code_patterns()

        assert "patterns" in patterns
        assert "number_keywords" in patterns
        assert isinstance(patterns["patterns"], list)

    @pytest.mark.asyncio
    async def test_fallback_when_db_empty(self):
        """DB 비어있을 때 fallback"""
        with patch(
            "app.modules.asset_registry.loader.load_mapping_asset",
            return_value=(None, "Not found"),
        ):
            from app.modules.ops.services.ci.planner.planner_llm import (
                _get_ci_code_patterns,
            )

            # 캐시 초기화
            import app.modules.ops.services.ci.planner.planner_llm as planner
            planner._CI_CODE_PATTERNS_CACHE = None

            patterns = _get_ci_code_patterns()
            assert patterns is not None
            assert len(patterns["patterns"]) > 0

    def test_list_keywords_defined(self):
        """LIST_KEYWORDS 버그 수정 확인"""
        from app.modules.ops.services.ci.planner.planner_llm import (
            _get_list_keywords,
        )

        keywords = _get_list_keywords()
        assert isinstance(keywords, list)
        assert "목록" in keywords or "list" in keywords
```

#### Phase 1 테스트

```python
# tests/unit/asset_registry/test_tool_crud.py

import pytest
from app.modules.asset_registry.schemas import ToolAssetCreate
from app.modules.asset_registry import crud


class TestToolCRUD:
    """Tool Asset CRUD 테스트"""

    @pytest.fixture
    def valid_tool_data(self):
        return ToolAssetCreate(
            name="test_tool",
            description="Test tool description",
            tool_type="database_query",
            tool_config={
                "source_ref": "test_source",
                "timeout_ms": 30000,
            },
            tool_input_schema={
                "type": "object",
                "properties": {
                    "keywords": {"type": "array"},
                },
                "required": ["keywords"],
            },
        )

    @pytest.mark.asyncio
    async def test_create_tool_asset(self, db_session, valid_tool_data):
        """Tool Asset 생성"""
        asset = await crud.create_tool_asset(db_session, valid_tool_data)

        assert asset.asset_id is not None
        assert asset.name == "test_tool"
        assert asset.asset_type == "tool"
        assert asset.tool_type == "database_query"
        assert asset.status == "draft"

    @pytest.mark.asyncio
    async def test_list_tool_assets(self, db_session, valid_tool_data):
        """Tool Asset 목록 조회"""
        await crud.create_tool_asset(db_session, valid_tool_data)

        assets, total = await crud.list_tool_assets(db_session)

        assert total >= 1
        assert any(a.name == "test_tool" for a in assets)

    @pytest.mark.asyncio
    async def test_list_tool_assets_by_status(self, db_session, valid_tool_data):
        """상태별 Tool Asset 조회"""
        await crud.create_tool_asset(db_session, valid_tool_data)

        assets, total = await crud.list_tool_assets(db_session, status="draft")
        assert total >= 1

        assets, total = await crud.list_tool_assets(db_session, status="published")
        assert all(a.status == "published" for a in assets)

    def test_tool_type_validation(self):
        """Tool type 유효성 검증"""
        with pytest.raises(ValueError):
            ToolAssetCreate(
                name="invalid_tool",
                tool_type="invalid_type",  # 잘못된 타입
                tool_config={},
                tool_input_schema={},
            )

    def test_tool_config_validation(self):
        """Tool config 유효성 검증"""
        with pytest.raises(ValueError):
            ToolAssetCreate(
                name="missing_source",
                tool_type="database_query",
                tool_config={},  # source_ref 누락
                tool_input_schema={},
            )
```

#### Phase 2 테스트

```python
# tests/unit/ops/tools/test_dynamic_tool.py

import pytest
from unittest.mock import AsyncMock, patch
from app.modules.ops.services.ci.tools.dynamic_tool import DynamicTool
from app.modules.ops.services.ci.tools.base import ToolContext, ToolResult


class TestDynamicTool:
    """DynamicTool 테스트"""

    @pytest.fixture
    def db_query_tool_asset(self):
        return {
            "name": "test_db_tool",
            "description": "Test database query tool",
            "tool_type": "database_query",
            "tool_config": {
                "source_ref": "test_postgres",
                "query_template": "SELECT * FROM items WHERE name LIKE '%{{keyword}}%'",
                "timeout_ms": 5000,
            },
            "tool_input_schema": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                },
                "required": ["keyword"],
            },
        }

    @pytest.fixture
    def http_api_tool_asset(self):
        return {
            "name": "test_http_tool",
            "description": "Test HTTP API tool",
            "tool_type": "http_api",
            "tool_config": {
                "base_url": "https://api.example.com",
                "endpoint": "/search?q={{query}}",
                "method": "GET",
                "timeout_ms": 10000,
            },
            "tool_input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        }

    def test_dynamic_tool_creation(self, db_query_tool_asset):
        """DynamicTool 생성"""
        tool = DynamicTool(db_query_tool_asset)

        assert tool.tool_name == "test_db_tool"
        assert tool.tool_type == "database_query"
        assert tool.description == "Test database query tool"

    @pytest.mark.asyncio
    async def test_should_execute_with_valid_params(self, db_query_tool_asset):
        """필수 파라미터가 있을 때 실행 가능"""
        tool = DynamicTool(db_query_tool_asset)
        context = ToolContext(tenant_id="test")

        result = await tool.should_execute(context, {"keyword": "test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_should_execute_without_required_params(self, db_query_tool_asset):
        """필수 파라미터 없을 때 실행 불가"""
        tool = DynamicTool(db_query_tool_asset)
        context = ToolContext(tenant_id="test")

        result = await tool.should_execute(context, {})
        assert result is False

    def test_render_template(self, db_query_tool_asset):
        """템플릿 렌더링"""
        tool = DynamicTool(db_query_tool_asset)

        template = "SELECT * FROM items WHERE id = {{id}} AND name = '{{name}}'"
        result = tool._render_template(template, {"id": 123, "name": "test"})

        assert result == "SELECT * FROM items WHERE id = 123 AND name = 'test'"

    @pytest.mark.asyncio
    async def test_execute_database_query(self, db_query_tool_asset):
        """Database query 실행"""
        tool = DynamicTool(db_query_tool_asset)
        context = ToolContext(tenant_id="test")

        with patch(
            "app.modules.asset_registry.loader.load_source_asset",
            new_callable=AsyncMock,
            return_value=({"host": "localhost"}, None),
        ), patch(
            "app.modules.ops.services.ci.tools.database_executor.execute_query",
            new_callable=AsyncMock,
            return_value=[{"id": 1, "name": "test"}],
        ):
            result = await tool.execute(context, {"keyword": "test"})

            assert result.success is True
            assert result.data is not None

    @pytest.mark.asyncio
    async def test_execute_http_api(self, http_api_tool_asset):
        """HTTP API 실행"""
        tool = DynamicTool(http_api_tool_asset)
        context = ToolContext(tenant_id="test")

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.json.return_value = {"results": []}
            mock_response.status_code = 200
            mock_response.raise_for_status = lambda: None

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            result = await tool.execute(context, {"query": "test"})

            assert result.success is True
```

#### Phase 3 테스트

```python
# tests/unit/ops/planner/test_tool_selector_llm.py

import pytest
from unittest.mock import AsyncMock, patch
from app.modules.ops.services.domain.tool_selector_llm import LLMToolSelector


class TestLLMToolSelector:
    """LLM Tool Selector 테스트"""

    @pytest.fixture
    def selector(self):
        return LLMToolSelector()

    @pytest.mark.asyncio
    async def test_build_tool_descriptions(self, selector):
        """Tool description 수집"""
        with patch(
            "app.modules.ops.services.ci.tools.base.get_tool_registry"
        ) as mock_registry:
            mock_registry.return_value.get_tool_descriptions.return_value = [
                {
                    "name": "ci_search",
                    "description": "CI 검색 도구",
                    "input_schema": {"properties": {"keywords": {}}},
                },
                {
                    "name": "graph_expand",
                    "description": "그래프 확장 도구",
                    "input_schema": {"properties": {"ci_id": {}}},
                },
            ]

            descriptions = selector._build_tool_descriptions()

            assert "ci_search" in descriptions
            assert "graph_expand" in descriptions
            assert "CI 검색 도구" in descriptions

    @pytest.mark.asyncio
    async def test_select_tools(self, selector):
        """Tool 선택"""
        mock_llm_response = """
        {
            "tools": [
                {
                    "tool_name": "ci_search",
                    "confidence": 0.95,
                    "reasoning": "사용자가 서버를 검색하려고 함",
                    "parameters": {"keywords": ["sys-order"]}
                }
            ],
            "execution_order": "sequential"
        }
        """

        with patch(
            "app.modules.ops.services.domain.tool_selector_llm.create_llm_response",
            new_callable=AsyncMock,
            return_value=mock_llm_response,
        ), patch(
            "app.modules.ops.services.ci.tools.base.get_tool_registry"
        ) as mock_registry:
            mock_registry.return_value.get_tool_descriptions.return_value = []

            tools = await selector.select_tools("sys-order 서버 찾아줘")

            assert len(tools) == 1
            assert tools[0].tool_name == "ci_search"
            assert tools[0].confidence == 0.95

    def test_parse_response(self, selector):
        """LLM 응답 파싱"""
        response = """```json
        {
            "tools": [
                {"tool_name": "test", "confidence": 0.8, "reasoning": "test"}
            ]
        }
        ```"""

        tools = selector._parse_response(response)

        assert len(tools) == 1
        assert tools[0].tool_name == "test"

    def test_parse_response_invalid_json(self, selector):
        """잘못된 JSON 응답"""
        response = "This is not JSON"

        with pytest.raises(Exception):
            selector._parse_response(response)
```

#### Phase 4 테스트

```python
# tests/unit/ops/orchestrator/test_chain_executor.py

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.modules.ops.schemas import ToolChain, ToolChainStep
from app.modules.ops.services.ci.orchestrator.chain_executor import ToolChainExecutor
from app.modules.ops.services.ci.tools.base import ToolContext, ToolResult


class TestToolChainExecutor:
    """Tool Chain Executor 테스트"""

    @pytest.fixture
    def executor(self):
        return ToolChainExecutor()

    @pytest.fixture
    def context(self):
        return ToolContext(tenant_id="test", user_id="test_user")

    @pytest.fixture
    def simple_chain(self):
        return ToolChain(
            chain_id="test_chain",
            execution_mode="sequential",
            steps=[
                ToolChainStep(
                    step_id="step1",
                    tool_name="tool_a",
                    parameters={"input": "value"},
                ),
                ToolChainStep(
                    step_id="step2",
                    tool_name="tool_b",
                    depends_on=["step1"],
                    output_mapping={"prev_result": "step1.data.result"},
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_execute_sequential_chain(self, executor, context, simple_chain):
        """순차 체인 실행"""
        mock_tool = MagicMock()
        mock_tool.safe_execute = AsyncMock(
            return_value=ToolResult(success=True, data={"result": "ok"})
        )

        with patch.object(executor._registry, "get_tool", return_value=mock_tool):
            result = await executor.execute_chain(simple_chain, context)

            assert result.success is True
            assert len(result.step_results) == 2
            assert "step1" in result.step_results
            assert "step2" in result.step_results

    @pytest.mark.asyncio
    async def test_sequential_chain_stops_on_failure(self, executor, context):
        """순차 체인에서 실패 시 중단"""
        chain = ToolChain(
            chain_id="fail_chain",
            execution_mode="sequential",
            steps=[
                ToolChainStep(step_id="step1", tool_name="tool_a"),
                ToolChainStep(step_id="step2", tool_name="tool_b"),
            ],
        )

        mock_tool = MagicMock()
        mock_tool.safe_execute = AsyncMock(
            return_value=ToolResult(success=False, error="Failed")
        )

        with patch.object(executor._registry, "get_tool", return_value=mock_tool):
            result = await executor.execute_chain(chain, context)

            assert result.success is False
            assert len(result.step_results) == 1  # step2는 실행되지 않음
            assert "step1" in result.failed_steps

    @pytest.mark.asyncio
    async def test_execute_parallel_chain(self, executor, context):
        """병렬 체인 실행"""
        chain = ToolChain(
            chain_id="parallel_chain",
            execution_mode="parallel",
            steps=[
                ToolChainStep(step_id="step1", tool_name="tool_a"),
                ToolChainStep(step_id="step2", tool_name="tool_b"),
                ToolChainStep(step_id="step3", tool_name="tool_c"),
            ],
        )

        mock_tool = MagicMock()
        mock_tool.safe_execute = AsyncMock(
            return_value=ToolResult(success=True, data={"result": "ok"})
        )

        with patch.object(executor._registry, "get_tool", return_value=mock_tool):
            result = await executor.execute_chain(chain, context)

            assert result.success is True
            assert len(result.step_results) == 3
            # 병렬 실행이므로 모든 결과가 리스트로
            assert isinstance(result.final_output, list)

    def test_merge_params(self, executor):
        """파라미터 매핑"""
        from app.modules.ops.schemas import StepResult

        prev_results = {
            "step1": StepResult(
                step_id="step1",
                success=True,
                data={"records": [{"ci_id": "CI-001"}]},
            )
        }

        step = ToolChainStep(
            step_id="step2",
            tool_name="tool_b",
            parameters={"static_param": "value"},
            output_mapping={"ci_id": "step1.data.records[0].ci_id"},
        )

        params = executor._merge_params(step, prev_results)

        assert params["static_param"] == "value"
        assert params["ci_id"] == "CI-001"

    def test_resolve_path(self, executor):
        """경로 해석"""
        from app.modules.ops.schemas import StepResult

        results = {
            "step1": StepResult(
                step_id="step1",
                success=True,
                data={"items": [{"id": 1}, {"id": 2}], "count": 2},
            )
        }

        # 단순 경로
        assert executor._resolve_path("step1.data.count", results) == 2

        # 배열 인덱스
        assert executor._resolve_path("step1.data.items[0].id", results) == 1
        assert executor._resolve_path("step1.data.items[1].id", results) == 2

        # 존재하지 않는 경로
        assert executor._resolve_path("step1.data.nonexistent", results) is None
```

### 9.2 통합 테스트 (Integration Tests)

```python
# tests/integration/test_orchestration_flow.py

import pytest
from httpx import AsyncClient


class TestOrchestrationFlow:
    """오케스트레이션 전체 흐름 통합 테스트"""

    @pytest.fixture
    async def setup_tools(self, db_session):
        """테스트용 Tool 설정"""
        from app.modules.asset_registry import crud
        from app.modules.asset_registry.schemas import ToolAssetCreate

        # CI Search Tool
        ci_tool = await crud.create_tool_asset(
            db_session,
            ToolAssetCreate(
                name="test_ci_search",
                description="테스트 CI 검색",
                tool_type="database_query",
                tool_config={"source_ref": "test_db"},
                tool_input_schema={
                    "type": "object",
                    "properties": {"keywords": {"type": "array"}},
                    "required": ["keywords"],
                },
            ),
        )
        ci_tool.status = "published"
        await db_session.commit()

        return {"ci_tool": ci_tool}

    @pytest.mark.asyncio
    async def test_full_query_flow(self, client: AsyncClient, setup_tools):
        """전체 질의 흐름 테스트"""
        # 1. Tool 목록 조회
        response = await client.get("/api/asset-registry/tools")
        assert response.status_code == 200
        assert len(response.json()["assets"]) > 0

        # 2. 질의 실행
        response = await client.post(
            "/api/ops/query",
            json={"question": "sys-order 서버 찾아줘"},
        )
        assert response.status_code == 200

        # 3. 결과 확인
        result = response.json()
        assert "data" in result or "error" in result

    @pytest.mark.asyncio
    async def test_tool_create_and_test(self, client: AsyncClient):
        """Tool 생성 및 테스트"""
        # 1. Tool 생성
        response = await client.post(
            "/api/asset-registry/tools",
            json={
                "name": "integration_test_tool",
                "description": "통합 테스트용 Tool",
                "tool_type": "custom",
                "tool_config": {},
                "tool_input_schema": {"type": "object"},
            },
        )
        assert response.status_code == 200
        tool_id = response.json()["asset_id"]

        # 2. Tool 테스트
        response = await client.post(
            f"/api/asset-registry/tools/{tool_id}/test",
            json={},
        )
        # custom 타입은 아직 구현되지 않아 실패할 수 있음
        assert response.status_code in [200, 400]

        # 3. Tool 삭제 (정리)
        response = await client.delete(f"/api/asset-registry/tools/{tool_id}")
        assert response.status_code in [200, 204]
```

### 9.3 E2E 테스트 (Playwright)

```typescript
// apps/web/e2e/admin/tools.spec.ts

import { test, expect } from "@playwright/test";

test.describe("Tool Management", () => {
  test.beforeEach(async ({ page }) => {
    // 로그인
    await page.goto("/admin/login");
    await page.fill('[data-testid="email"]', "admin@example.com");
    await page.fill('[data-testid="password"]', "password");
    await page.click('[data-testid="login-button"]');
    await page.waitForURL("/admin");
  });

  test("should display tool list", async ({ page }) => {
    await page.goto("/admin/tools");

    // 테이블이 표시되는지 확인
    await expect(page.locator(".ag-root-wrapper")).toBeVisible();

    // 컬럼 헤더 확인
    await expect(page.locator("text=Tool Name")).toBeVisible();
    await expect(page.locator("text=Type")).toBeVisible();
    await expect(page.locator("text=Status")).toBeVisible();
  });

  test("should create new tool", async ({ page }) => {
    await page.goto("/admin/tools");

    // New Tool 버튼 클릭
    await page.click("text=+ New Tool");

    // 모달이 열리는지 확인
    await expect(page.locator("text=Create New Tool")).toBeVisible();

    // 폼 입력
    await page.fill('[id="name"]', "e2e_test_tool");
    await page.selectOption('[data-testid="tool-type-select"]', "database_query");
    await page.fill('[id="description"]', "E2E 테스트용 Tool");

    // Config 입력 (JSON Editor)
    const configEditor = page.locator('[data-testid="tool-config-editor"]');
    await configEditor.fill(JSON.stringify({ source_ref: "test" }));

    // 생성 버튼 클릭
    await page.click("text=Create Tool");

    // 모달이 닫히고 목록에 추가되었는지 확인
    await expect(page.locator("text=Create New Tool")).not.toBeVisible();
    await expect(page.locator("text=e2e_test_tool")).toBeVisible();
  });

  test("should test tool", async ({ page }) => {
    await page.goto("/admin/tools");

    // 첫 번째 Tool의 Test 버튼 클릭
    await page.click('[data-testid="tool-row"]:first-child button:text("Test")');

    // 테스트 패널이 열리는지 확인
    await expect(page.locator("text=Test:")).toBeVisible();

    // 입력 작성
    const inputEditor = page.locator('[data-testid="test-input-editor"]');
    await inputEditor.fill(JSON.stringify({ keywords: ["test"] }));

    // Run Test 클릭
    await page.click("text=Run Test");

    // 결과가 표시되는지 확인 (성공 또는 에러)
    await expect(
      page.locator('[data-testid="test-result"]').or(page.locator('[data-testid="test-error"]'))
    ).toBeVisible({ timeout: 30000 });
  });

  test("should publish tool", async ({ page }) => {
    await page.goto("/admin/tools");

    // Draft 상태의 Tool 찾기
    const draftRow = page.locator('[data-testid="tool-row"]:has-text("draft")').first();

    // Publish 버튼 클릭
    await draftRow.locator("text=Publish").click();

    // 상태가 published로 변경되었는지 확인
    await expect(draftRow.locator("text=published")).toBeVisible();
  });

  test("should filter tools by status", async ({ page }) => {
    await page.goto("/admin/tools");

    // Status 필터 선택
    await page.selectOption('[data-testid="status-filter"]', "published");

    // 필터링된 결과 확인
    const rows = page.locator('[data-testid="tool-row"]');
    const count = await rows.count();

    for (let i = 0; i < count; i++) {
      await expect(rows.nth(i).locator("text=published")).toBeVisible();
    }
  });
});
```

### 9.4 UI 테스트 체크리스트

| 화면 | 테스트 항목 | 우선순위 |
|------|------------|----------|
| Tool 목록 | 테이블 렌더링 | P0 |
| Tool 목록 | 필터/검색 동작 | P1 |
| Tool 목록 | 페이지네이션 | P2 |
| Tool 생성 | 폼 유효성 검증 | P0 |
| Tool 생성 | JSON Editor 동작 | P1 |
| Tool 생성 | Source 선택 (드롭다운) | P1 |
| Tool 편집 | 기존 값 로드 | P0 |
| Tool 편집 | 저장 동작 | P0 |
| Tool 테스트 | 입력 JSON 작성 | P0 |
| Tool 테스트 | 실행 및 결과 표시 | P0 |
| Tool 테스트 | 에러 메시지 표시 | P1 |
| Tool 발행 | 상태 변경 확인 | P0 |
| Tool 발행 | Registry 리로드 확인 | P1 |

---

## 10. 배포 및 롤백 계획

### 10.1 배포 순서

```
Phase 0 (DB 변경 없음) → Phase 1 (DB 마이그레이션) → Phase 2-4 (백엔드) → Phase 5 (프론트엔드)
```

### 10.2 Phase별 배포 체크리스트

#### Phase 0 배포

```bash
# 1. Mapping YAML 파일 배포
cp apps/api/resources/mappings/*.yaml /deploy/resources/mappings/

# 2. planner_llm.py 배포
cp apps/api/app/modules/ops/services/ci/planner/planner_llm.py /deploy/

# 3. 재시작
systemctl restart tobit-api

# 4. 검증
curl -X POST http://localhost:8000/api/ops/query \
  -H "Content-Type: application/json" \
  -d '{"question": "sys-order 서버 목록"}'
```

#### Phase 1 배포

```bash
# 1. 백업
pg_dump -h localhost -U tobit tobit_db > backup_before_phase1.sql

# 2. 마이그레이션 실행
cd apps/api
alembic upgrade head

# 3. 마이그레이션 확인
psql -h localhost -U tobit tobit_db -c "\d tb_asset_registry"
# tool_type, tool_config, tool_input_schema, tool_output_schema 컬럼 확인

# 4. 초기 데이터 이관 (선택)
python scripts/migrate_tools_to_assets.py

# 5. 애플리케이션 배포
systemctl restart tobit-api

# 6. 검증
curl http://localhost:8000/api/asset-registry/tools
```

#### Phase 2-4 배포

```bash
# 1. 코드 배포
git pull origin main

# 2. 의존성 업데이트 (필요시)
pip install -r requirements.txt

# 3. 재시작
systemctl restart tobit-api

# 4. Tool Registry 로드 확인
curl http://localhost:8000/api/health/tools
# {"total_tools": N, "dynamic_tools": M}

# 5. 동적 Tool 테스트
curl -X POST http://localhost:8000/api/ops/query \
  -H "Content-Type: application/json" \
  -d '{"question": "장비 검색해줘"}'
```

#### Phase 5 배포

```bash
# 1. 프론트엔드 빌드
cd apps/web
npm run build

# 2. 배포
cp -r .next/standalone/* /deploy/web/

# 3. 재시작
systemctl restart tobit-web

# 4. UI 접근 확인
curl -I http://localhost:3000/admin/tools
```

### 10.3 롤백 계획

#### Phase 0 롤백

```bash
# 기존 planner_llm.py 복원
git checkout HEAD~1 -- apps/api/app/modules/ops/services/ci/planner/planner_llm.py

# Mapping 파일은 삭제해도 fallback 동작
rm apps/api/resources/mappings/ci_code_patterns.yaml

systemctl restart tobit-api
```

#### Phase 1 롤백

```bash
# DB 롤백
cd apps/api
alembic downgrade -1

# 또는 백업에서 복원
psql -h localhost -U tobit tobit_db < backup_before_phase1.sql

systemctl restart tobit-api
```

#### Phase 2-4 롤백

```bash
# 이전 버전 체크아웃
git checkout HEAD~1 -- apps/api/app/modules/ops/

# 재시작 (동적 Tool 로드 스킵됨)
systemctl restart tobit-api
```

#### Phase 5 롤백

```bash
# 이전 빌드 복원
cp -r /backup/web/.next/standalone/* /deploy/web/

systemctl restart tobit-web
```

### 10.4 모니터링

#### 배포 후 확인 항목

| 항목 | 확인 방법 | 정상 기준 |
|------|----------|----------|
| API 응답 | `curl /api/health` | 200 OK |
| Tool 로드 | `curl /api/health/tools` | total_tools > 0 |
| 기존 질의 동작 | CI 검색 질의 | 결과 반환 |
| 새 Tool 동작 | 동적 Tool 질의 | 결과 반환 |
| UI 접근 | `/admin/tools` 접근 | 페이지 렌더링 |
| 에러율 | Grafana 대시보드 | < 1% |
| 응답 시간 | Grafana 대시보드 | p95 < 2s |

#### 알림 설정

```yaml
# alertmanager.yml
groups:
  - name: orchestration
    rules:
      - alert: ToolLoadFailure
        expr: tool_load_failures_total > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Tool 로드 실패 발생"

      - alert: DynamicToolExecutionError
        expr: rate(dynamic_tool_errors_total[5m]) > 0.1
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "동적 Tool 실행 에러율 증가"
```

---

## 부록: 파일 변경 요약

### 신규 파일

| 파일 | Phase | 설명 |
|------|-------|------|
| `resources/mappings/ci_code_patterns.yaml` | 0 | CI 코드 패턴 |
| `resources/mappings/graph_view_keywords.yaml` | 0 | 그래프 뷰 키워드 |
| `resources/mappings/auto_view_preferences.yaml` | 0 | 자동 뷰 선호도 |
| `resources/mappings/output_type_priorities.yaml` | 0 | 출력 타입 우선순위 |
| `resources/mappings/filter_keywords.yaml` | 0 | 필터 키워드 |
| `resources/mappings/aggregation_keywords.yaml` | 0 | 집계 키워드 |
| `alembic/versions/xxxx_add_tool_asset_fields.py` | 1 | 마이그레이션 |
| `resources/tools/ci_search.yaml` | 1 | CI Search Tool 정의 |
| `resources/tools/graph_expand.yaml` | 1 | Graph Expand Tool 정의 |
| `scripts/migrate_tools_to_assets.py` | 1 | Tool 이관 스크립트 |
| `ops/services/ci/tools/dynamic_tool.py` | 2 | DynamicTool 클래스 |
| `ops/services/domain/tool_selector_llm.py` | 3 | LLM Tool Selector |
| `ops/services/domain/generic_planner.py` | 3 | Generic Planner |
| `resources/prompts/generic/tool_selector.yaml` | 3 | Tool 선택 프롬프트 |
| `ops/services/ci/orchestrator/chain_executor.py` | 4 | Chain Executor |
| `app/admin/tools/page.tsx` | 5 | Tool 목록 페이지 |
| `components/admin/CreateToolModal.tsx` | 5 | Tool 생성 모달 |
| `components/admin/ToolAssetPanel.tsx` | 5 | Tool 관리 패널 |
| `components/admin/ToolTestPanel.tsx` | 5 | Tool 테스트 패널 |

### 수정 파일

| 파일 | Phase | 변경 내용 |
|------|-------|----------|
| `ops/services/ci/planner/planner_llm.py` | 0 | `_get_*()` 함수 추가, 하드코딩 제거 |
| `asset_registry/models.py` | 1 | Tool 필드 4개 추가 |
| `asset_registry/schemas.py` | 1 | ToolAsset 스키마 추가 |
| `asset_registry/crud.py` | 1 | Tool CRUD 함수 추가 |
| `asset_registry/loader.py` | 1 | `load_tool_asset()` 추가 |
| `asset_registry/router.py` | 1, 5 | Tool API 엔드포인트 추가 |
| `ops/services/ci/tools/base.py` | 2 | Registry 확장 |
| `ops/services/ci/tools/registry_init.py` | 2 | DB 로딩 추가 |
| `ops/services/ci/planner/plan_schema.py` | 3 | GenericPlan 스키마 추가 |
| `ops/schemas.py` | 4 | ToolChain 스키마 추가 |
| `components/admin/AdminDashboard.tsx` | 5 | Tools 탭 추가 |

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| 1.0 | 2026-01-28 | 초기 작성 |
