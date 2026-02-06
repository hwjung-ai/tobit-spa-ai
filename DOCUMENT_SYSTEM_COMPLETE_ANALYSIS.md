# 문서 시스템 완전 분석: pgvector + Redis + Asset Registry 통합

## 작성일: 2026-02-06
## 상태: 완전 분석 완료

---

## 📊 Executive Summary

### 현재 상황
- **Document System**: pgvector 기반 벡터 검색, Redis 캐싱 인프라 완성
- **Asset Registry**: 9가지 asset type (prompt, mapping, policy, query, source, catalog, resolver, tool, screen)
- **OPS CI Tools**: BaseTool 추상 인터페이스, DynamicTool 구현
- **이미 있는 것**: DocumentSearchService (Hybrid search), QueryAssetRegistry (Tool-specific queries)

### 핵심 발견
1. **Document과 Asset은 분리되어 있음** - embedding 필드는 Document에만 있음
2. **Document Search Service는 이미 구현됨** - 벡터 + BM25 하이브리드 검색 준비됨
3. **QueryAssetRegistry는 OPS CI용** - tool_type/operation 기반 쿼리 인덱싱
4. **Redis는 부분적으로 활용** - CEP, Data Explorer에만 사용, Document 캐싱은 미구현

---

## 🏗️ 현재 아키텍처 분석

### 1. Document System 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    Document 관리 계층                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────┐         ┌──────────────┐                │
│  │  File Upload   │         │ Chunking     │                │
│  │  (router.py)   │────────>│ Strategy     │                │
│  └────────────────┘         └──────────────┘                │
│         │                           │                        │
│         │                           ▼                        │
│         │                   ┌──────────────────┐             │
│         │                   │ DocumentChunk    │             │
│         │                   │ - id             │             │
│         │                   │ - embedding      │             │
│         │                   │ - text           │             │
│         │                   │ - chunk_type     │             │
│         │                   │ - page_number    │             │
│         │                   └──────────────────┘             │
│         │                           │                        │
│         │                           ▼                        │
│         └──────────┬────────────┐                            │
│                    ▼            ▼                            │
│            ┌──────────────┐ ┌──────────────┐               │
│            │ pgvector DB  │ │ PostgreSQL   │               │
│            │ (1536-dim)   │ │ (BM25, etc)  │               │
│            └──────────────┘ └──────────────┘               │
│                    ▲            ▲                            │
│                    │            │                            │
│         ┌──────────┴────────────┴──────┐                    │
│         │  DocumentSearchService       │                    │
│         │  ├─ _vector_search()         │                    │
│         │  ├─ _text_search()           │                    │
│         │  ├─ _combine_results() (RRF) │                    │
│         │  └─ search() [hybrid]        │                    │
│         └──────────────────────────────┘                    │
│                    │                                         │
│                    ▼                                         │
│         SearchResult[] 반환                                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Document Model (Document + DocumentChunk)
├─ Document (문서 메타데이터)
│  ├─ id, tenant_id, user_id
│  ├─ filename, content_type, size
│  ├─ status (queued/processing/done/failed)
│  ├─ format, processing_progress, total_chunks
│  ├─ doc_metadata (JSON: pages, word_count, language)
│  └─ error_details (JSON)
│
└─ DocumentChunk (청크 + embedding)
   ├─ id, document_id, chunk_index
   ├─ text, chunk_type (text/table/image/mixed)
   ├─ embedding (Vector(1536) with pgvector)
   ├─ page_number, slide_number, position_in_doc
   ├─ table_data (JSON)
   ├─ source_hash (변경 감지용)
   ├─ chunk_version (증분 업데이트용)
   └─ relevance_score (검색 결과용)
```

### 2. Asset Registry 구조

```
┌─────────────────────────────────────────────────────────────┐
│                 Asset Registry 저장소 (tb_asset_registry)     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐
│  │ TbAssetRegistry (JSONB 중심 설계)                        │
│  ├─────────────────────────────────────────────────────────┤
│  │ 공통 필드                                                 │
│  │ ├─ asset_id (UUID, PK)                                  │
│  │ ├─ asset_type (prompt/mapping/policy/query/source/     │
│  │ │              catalog/resolver/tool/screen)             │
│  │ ├─ name, description, version, status                  │
│  │ ├─ created_at, updated_at, published_at                │
│  │ ├─ created_by, published_by                            │
│  │ └─ tags (JSONB)                                         │
│  │                                                           │
│  │ Prompt Asset 필드                                        │
│  │ ├─ scope, engine, template                             │
│  │ ├─ input_schema (JSONB)                                │
│  │ └─ output_contract (JSONB)                             │
│  │                                                           │
│  │ Mapping Asset 필드                                       │
│  │ ├─ mapping_type                                        │
│  │ └─ content (JSONB)                                     │
│  │                                                           │
│  │ Query Asset 필드 ★★★ (OPS CI와의 핵심!)                │
│  │ ├─ query_sql (TEXT)                                   │
│  │ ├─ query_cypher (TEXT)                                │
│  │ ├─ query_http (JSONB)                                 │
│  │ ├─ query_params (JSONB)                               │
│  │ └─ query_metadata (JSONB: {tool_type, operation})     │
│  │                                                           │
│  │ Tool Asset 필드 ★★★ (Tool Registry와의 핵심!)         │
│  │ ├─ tool_type (custom, database_query, http_api, etc)  │
│  │ ├─ tool_config (JSONB)                                │
│  │ ├─ tool_input_schema (JSONB)                          │
│  │ └─ tool_output_schema (JSONB)                         │
│  │                                                           │
│  │ Source Asset 필드                                        │
│  │ ├─ [connection 정보 저장, 필드 확인 필요]               │
│  │                                                           │
│  │ Policy/Screen/Catalog/Resolver 필드                    │
│  │ ├─ [asset_type별 특화 필드]                           │
│  │                                                           │
│  └─────────────────────────────────────────────────────────┘
│            │                           │
│            ▼                           ▼
│   ┌─────────────────┐      ┌─────────────────┐
│   │ QueryAssetReg.  │      │ ToolAssetRouter │
│   │ (OPS CI용)      │      │ (Asset 관리)    │
│   │                 │      │                 │
│   │ Index:          │      │ API Endpoints   │
│   │ {tool_type:     │      │ ├─ list_tools() │
│   │  {operation:    │      │ ├─ create()     │
│   │   asset_name}   │      │ ├─ update()     │
│   │ }               │      │ └─ delete()     │
│   └─────────────────┘      └─────────────────┘
│            │                           │
│            ▼                           ▼
│     OPS CI Tools             Tool Execution
│     (DynamicTool)            (via BaseTool interface)
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 3. OPS CI Tool Registry 구조

```
┌─────────────────────────────────────────────────────────────┐
│              OPS Tool Registry & Execution                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────┐                         │
│  │ BaseTool (Abstract Interface)  │                         │
│  │ ├─ @abstractmethod tool_type   │                         │
│  │ ├─ @abstractmethod execute()   │                         │
│  │ ├─ input_schema property       │                         │
│  │ └─ output_schema property      │                         │
│  └────────────────────────────────┘                         │
│              ▲                                                │
│              │ (implement)                                    │
│    ┌─────────┼─────────────┬──────────────┐                │
│    │         │             │              │                │
│    ▼         ▼             ▼              ▼                │
│  DynamicTool CITool  MetricTool  HistoryTool ...          │
│  (Asset-based)                                              │
│                                                               │
│  DynamicTool = Asset Registry의 Tool Asset로부터            │
│  ├─ tool_type: database_query, http_api, graph_query      │
│  ├─ tool_config: 실행 설정                                 │
│  ├─ tool_input_schema: 입력 파라미터                      │
│  └─ tool_output_schema: 출력 포맷                         │
│                                                               │
│  ┌──────────────────────────────┐                          │
│  │ ToolRegistry                 │                          │
│  │ ├─ register_tool()           │                          │
│  │ ├─ execute_tool()            │                          │
│  │ └─ get_available_tools()     │                          │
│  └──────────────────────────────┘                          │
│           │                                                  │
│           ├─> Tool Execution (Async)                       │
│           │   ├─ Input validation                          │
│           │   ├─ Context setup (tenant_id, user_id)        │
│           │   ├─ Tool.execute(context, input_data)         │
│           │   └─ ToolResult 반환                           │
│           │                                                  │
│           └─> Tool Discovery                               │
│               ├─ get_available_tools()                     │
│               └─ filter by tool_type                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Tool Result Format:
{
  "success": bool,
  "data": Any,           # 실제 결과
  "error": str | None,
  "error_details": dict | None,
  "warnings": [str],
  "metadata": {
    "execution_time_ms": int,
    "rows_returned": int,
    ...
  }
}
```

### 4. Redis 현황

```
┌─────────────────────────────────────────────────────────────┐
│                  Redis 사용 현황                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  core/redis.py (Redis 클라이언트)                            │
│  └─ create_redis_client(settings)                           │
│     ├─ synchronous Redis (decode_responses=True)            │
│     └─ used by: Data Explorer, Cache Manager               │
│                                                               │
│  app/modules/cep_builder/redis_state_manager.py            │
│  ├─ Async Redis (redis.asyncio)                            │
│  ├─ Features:                                               │
│  │  ├─ save_retry_record()       [Notification 재시도]      │
│  │  ├─ load_retry_record()                                 │
│  │  ├─ get_rule_state()          [규칙 상태]               │
│  │  ├─ save_rule_state()                                   │
│  │  ├─ publish_event()           [Pub/Sub]                │
│  │  ├─ subscribe_events()                                  │
│  │  └─ TTL 자동 만료 (24시간)                              │
│  └─ Key prefix: "cep:*"                                   │
│                                                               │
│  app/modules/data_explorer/services/redis_service.py       │
│  ├─ 조회 결과 캐싱                                          │
│  ├─ 메타데이터 캐싱                                        │
│  └─ TTL 기반 만료                                           │
│                                                               │
│  *** Document Search 캐싱은 미구현 ***                      │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Redis Key 구조 (현재):
├─ cep:retry_record:{notification_id}:{channel_id}
├─ cep:rule_state:{rule_id}
├─ cep:event_queue
├─ data_explorer:cache:{cache_key}
└─ data_explorer:metadata
```

---

## 🔍 핵심 발견: Document ↔ Asset Registry 관계

### Issue 1: Embedding 필드는 Document에만 있음
```python
# DocumentChunk (apps/api/models/document.py:68)
embedding: list[float] = Field(sa_column=Column(Vector(1536), nullable=False))

# TbAssetRegistry (apps/api/app/modules/asset_registry/models.py)
# ❌ embedding 필드 없음!
# Query/Prompt/Tool Asset은 embedding을 저장할 수 없음
```

### Issue 2: Document과 Asset은 독립적인 테이블
```
documents                      tb_asset_registry
├─ id (String)                ├─ asset_id (UUID)
├─ tenant_id                  ├─ asset_type (enum-like)
├─ filename                   ├─ name
└─ [metadata]                 └─ [asset-specific fields]

관계: 없음 (현재)
```

### Issue 3: DocumentSearchService는 "이미 있지만 미완성"
```python
# apps/api/app/modules/document_processor/services/search_service.py

class DocumentSearchService:
    async def search(self, query, filters, top_k, search_type):
        # search_type: "text", "vector", "hybrid"

        # ❌ 실제 구현이 아직 미완성 (placeholder)
        # - _vector_search(): Mock results (line 178: pass)
        # - _text_search(): Mock results (line 135: pass)
        # - _combine_results(): RRF 로직만 구현됨

    # ✓ 라우터는 있음 (router.py:222, /search endpoint)
    # ✓ 모델/스키마는 있음 (SearchRequest, SearchResult)
    # ✓ 하지만 DB 쿼리 실행은 구현 안 됨!
```

---

## 🤔 OPS CI Ask 재분석: 세 가지 통합 경로

### **Option 1: Document Search Tool (권장)**

**개념**: Document를 새로운 Tool로 등록

```
User Query
    │
    ▼
┌─────────────────────────────────┐
│ OPS CI Tool Execution           │
│ ├─ Tool Name: "document_search" │
│ ├─ Tool Type: "search"          │
│ └─ Input: {query, top_k, ...}   │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ DocumentSearchService.search()   │
│ ├─ Vector search (pgvector)     │
│ ├─ Text search (BM25)           │
│ └─ Hybrid RRF combination       │
└─────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────┐
│ ToolResult                      │
│ ├─ data: SearchResult[]         │
│ ├─ success: bool                │
│ └─ metadata: {exec_time, ...}   │
└─────────────────────────────────┘
```

**구현 요소**:
1. DocumentSearchTool (BaseTool 구현)
2. DocumentSearchService 완성 (DB 쿼리)
3. ToolRegistry에 등록
4. Asset Registry에 tool asset 생성 (선택)

**장점**:
- 기존 DocumentSearchService 재사용
- OPS CI 통합 깔끔
- 캐싱/모니터링 기존 인프라 사용

---

### **Option 2: Document as Query Asset**

**개념**: Document Search를 Query Asset으로 등록

```
User Query
    │
    ▼
QueryAssetRegistry.get_query_asset(
  tool_type="search",
  operation="document_search"
)
    │
    ▼
Query Asset:
{
  "asset_id": "...",
  "asset_type": "query",
  "query_metadata": {
    "tool_type": "search",
    "operation": "document_search"
  },
  "query_sql": NULL,
  "query_cypher": NULL,
  "query_http": {
    "endpoint": "/documents/search",
    "method": "POST"
  },
  "query_params": {
    "query": "${query}",
    "top_k": 10
  }
}
    │
    ▼
DynamicTool (tool_type="http_api")
_execute_http_api(context, input_data)
    │
    ▼
DocumentSearchService.search()
```

**구현 요소**:
1. Query Asset 생성 (asset_registry)
2. DynamicTool이 http_api type으로 실행
3. DocumentSearchService와 연결

**단점**:
- HTTP 오버헤드
- Tool 인터페이스와 어긋남 (http_api는 내부 서비스 호출용)

---

### **Option 3: Document Tool Asset**

**개념**: Document Search를 Tool Asset으로 등록 + DynamicTool로 실행

```
Tool Asset (tb_asset_registry):
{
  "asset_type": "tool",
  "name": "DocumentSearch",
  "tool_type": "document_search",  # ← 커스텀 type
  "tool_config": {
    "search_service": "DocumentSearchService",
    "default_top_k": 10
  },
  "tool_input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "top_k": {"type": "integer"},
      "search_type": {"type": "string", "enum": ["text", "vector", "hybrid"]}
    }
  }
}
    │
    ▼
DynamicTool.execute()
    │
    ├─ tool_type="document_search"
    └─ _execute_custom() → DocumentSearchService
    │
    ▼
ToolResult
```

**단점**:
- DynamicTool이 "document_search" type을 인식해야 함
- 기존 tool_type (database_query, http_api, graph_query)과 다른 패턴

---

## 📋 최종 권장안: Option 1 상세 구현 계획

### 1️⃣ **DocumentSearchService 완성** (Priority 1)

```python
# apps/api/app/modules/document_processor/services/search_service.py

class DocumentSearchService:

    async def _vector_search(self, query, filters, top_k):
        """pgvector 검색 구현"""
        # 1. Query embedding 생성
        query_embedding = await self.embedding_service.embed(query)

        # 2. pgvector cosine similarity 쿼리 실행
        query_sql = """
        SELECT dc.id, dc.document_id, d.filename, dc.text,
               dc.page_number, dc.chunk_type,
               1 - (dc.embedding <=> $1) as similarity
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.tenant_id = $2
        AND 1 - (dc.embedding <=> $1) > $3
        ORDER BY similarity DESC
        LIMIT $4
        """
        # [실제 구현]

    async def _text_search(self, query, filters, top_k):
        """BM25 전문 검색 구현"""
        # PostgreSQL full-text search
        query_sql = """
        SELECT dc.id, dc.document_id, d.filename, dc.text,
               dc.page_number, dc.chunk_type,
               ts_rank(to_tsvector(dc.text), plainto_tsquery($1)) as rank
        FROM document_chunks dc
        JOIN documents d ON d.id = dc.document_id
        WHERE d.tenant_id = $2
        AND to_tsvector(dc.text) @@ plainto_tsquery($1)
        ORDER BY rank DESC
        LIMIT $3
        """
        # [실제 구현]
```

### 2️⃣ **DocumentSearchTool 구현** (Priority 1)

```python
# apps/api/app/modules/ops/services/ci/tools/document_search_tool.py

from .base import BaseTool, ToolContext, ToolResult

class DocumentSearchTool(BaseTool):
    """Tool for searching documents with vector + BM25 hybrid search"""

    def __init__(self, search_service=None):
        super().__init__()
        self.search_service = search_service or DocumentSearchService()

    @property
    def tool_type(self) -> str:
        return "document_search"

    @property
    def tool_name(self) -> str:
        return "Document Search"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query text"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of top results",
                    "default": 10
                },
                "search_type": {
                    "type": "string",
                    "enum": ["text", "vector", "hybrid"],
                    "description": "Search strategy",
                    "default": "hybrid"
                },
                "min_relevance": {
                    "type": "number",
                    "description": "Minimum relevance score",
                    "default": 0.5
                }
            },
            "required": ["query"]
        }

    async def execute(
        self, context: ToolContext, input_data: dict
    ) -> ToolResult:
        """Execute document search"""

        try:
            query = input_data.get("query", "")
            top_k = input_data.get("top_k", 10)
            search_type = input_data.get("search_type", "hybrid")
            min_relevance = input_data.get("min_relevance", 0.5)

            if not query:
                return ToolResult(success=False, error="Query required")

            filters = SearchFilters(
                tenant_id=context.tenant_id,
                min_relevance=min_relevance
            )

            results = await self.search_service.search(
                query=query,
                filters=filters,
                top_k=top_k,
                search_type=search_type
            )

            return ToolResult(
                success=True,
                data={
                    "results": [asdict(r) for r in results],
                    "count": len(results)
                },
                metadata={
                    "query": query,
                    "search_type": search_type
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_details={"exception_type": type(e).__name__}
            )
```

### 3️⃣ **ToolRegistry 등록** (Priority 1)

```python
# apps/api/app/modules/ops/services/ci/tools/base.py

class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def initialize(self):
        """Initialize with built-in tools"""
        from .document_search_tool import DocumentSearchTool

        # Document Search Tool 등록
        doc_search_tool = DocumentSearchTool()
        self.register_tool("document_search", doc_search_tool)

        logger.info("ToolRegistry initialized with document_search tool")
```

### 4️⃣ **Redis 캐싱 추가** (Priority 2)

```python
# app/modules/document_processor/services/search_service.py

class DocumentSearchService:

    def __init__(self, db_session=None, embedding_service=None, redis_client=None):
        self.redis = redis_client

    async def search(self, query, filters, top_k, search_type="hybrid"):
        """Perform search with Redis caching"""

        # Cache key
        cache_key = f"doc_search:{filters.tenant_id}:{query}:{search_type}:{top_k}"

        # Try cache
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        # Execute search
        results = await self._execute_search(query, filters, top_k, search_type)

        # Cache result (5분)
        if self.redis and results:
            await self.redis.setex(
                cache_key,
                300,  # 5 minutes
                json.dumps([asdict(r) for r in results])
            )

        return results
```

### 5️⃣ **API 통합** (Priority 2)

```python
# OPS CI에서 호출
tool = get_tool_registry().get_tool("document_search")
result = await tool.execute(
    context=ToolContext(tenant_id="..."),
    input_data={
        "query": "payment processing system",
        "top_k": 10,
        "search_type": "hybrid"
    }
)
```

---

## 📊 3가지 옵션 비교표

| 항목 | Option 1: Tool | Option 2: Query Asset | Option 3: Tool Asset |
|------|:---:|:---:|:---:|
| **구현 복잡도** | 중간 | 낮음 | 높음 |
| **성능** | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **유지보수성** | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| **기존 코드 재사용** | 높음 | 중간 | 낮음 |
| **캐싱 지원** | 원활 | 제한적 | 원활 |
| **확장성** | ⭐⭐⭐ | ⭐ | ⭐ |
| **Asset Registry 통합** | ✗ | ✓ | ✓ |
| **권장도** | **1위** | 3위 | 2위 |

---

## 🛠️ 구현 체크리스트: Option 1

### Phase 1: DocumentSearchService 완성
- [ ] 1.1 `_vector_search()` DB 쿼리 구현
  - [ ] pgvector embedding 생성
  - [ ] SQL 쿼리 실행
  - [ ] 결과 파싱
- [ ] 1.2 `_text_search()` DB 쿼리 구현
  - [ ] PostgreSQL tsvector 사용
  - [ ] plainto_tsquery 구현
  - [ ] 결과 파싱
- [ ] 1.3 `_combine_results()` 테스트
  - [ ] RRF 알고리즘 검증
  - [ ] 상위 K개 결과 반환
- [ ] 1.4 `search()` 통합 테스트
  - [ ] 텍스트 검색
  - [ ] 벡터 검색
  - [ ] 하이브리드 검색
  - [ ] 캐싱 제외 상태

### Phase 2: DocumentSearchTool 구현
- [ ] 2.1 DocumentSearchTool 클래스 생성
  - [ ] BaseTool 상속
  - [ ] tool_type/tool_name 정의
  - [ ] input_schema 정의
- [ ] 2.2 execute() 메서드 구현
  - [ ] 입력 검증
  - [ ] SearchFilters 생성
  - [ ] search_service.search() 호출
  - [ ] ToolResult 반환
- [ ] 2.3 단위 테스트
  - [ ] 정상 케이스
  - [ ] 에러 케이스
  - [ ] 입력 검증

### Phase 3: ToolRegistry 통합
- [ ] 3.1 ToolRegistry에 등록
  - [ ] DocumentSearchTool 인스턴스 생성
  - [ ] register_tool("document_search", tool) 호출
- [ ] 3.2 도구 발견 테스트
  - [ ] get_tool("document_search") 작동
  - [ ] list_tools() 포함됨
- [ ] 3.3 도구 실행 테스트
  - [ ] OPS CI에서 호출
  - [ ] 결과 검증

### Phase 4: Redis 캐싱 추가 (선택)
- [ ] 4.1 DocumentSearchService에 캐싱 로직 추가
  - [ ] redis_client 의존성 주입
  - [ ] cache_key 생성
  - [ ] get/setex 구현
- [ ] 4.2 캐시 TTL 설정
  - [ ] 기본 TTL: 5분
  - [ ] 캐시 무효화 전략 수립
- [ ] 4.3 캐싱 테스트
  - [ ] 첫 조회 (캐시 미스)
  - [ ] 반복 조회 (캐시 히트)
  - [ ] TTL 만료

### Phase 5: 문서화 및 배포
- [ ] 5.1 DocumentSearchTool 문서화
  - [ ] API 문서
  - [ ] 사용 예제
  - [ ] 성능 특성
- [ ] 5.2 배포 준비
  - [ ] 환경 변수 설정 (REDIS_URL)
  - [ ] 마이그레이션 (필요시)
  - [ ] 배포 순서 수립
- [ ] 5.3 검증
  - [ ] 통합 테스트
  - [ ] 성능 벤치마크
  - [ ] 캐싱 동작 확인

---

## 🔌 Redis 캐싱 계획 (부가)

### 현재 미사용 Redis 리소스
```
Key patterns to add:

1. Document Search Cache:
   doc_search:{tenant_id}:{query_hash}:{search_type}
   TTL: 5분
   Value: SearchResult[] (JSON)

2. Embedding Cache (선택):
   doc_embedding:{doc_id}:{chunk_id}
   TTL: 24시간
   Value: [float] (embedding vector)

3. Document Metadata Cache:
   doc_metadata:{tenant_id}:{doc_id}
   TTL: 1시간
   Value: Document metadata (JSON)
```

### 캐싱 전략
1. **Search Results**: 동일 쿼리 반복 조회 시 5분 재사용
2. **Embedding**: 벡터 생성 후 캐싱 (생성 비용이 높음)
3. **Invalidation**: Document 업데이트 시 관련 캐시 삭제

---

## 💡 Asset Registry 통합 (Future)

### 선택사항: Tool Asset로 등록

```python
# 배포 후 선택적으로 Asset Registry에 등록 가능

from app.modules.asset_registry.crud import create_asset

tool_asset = TbAssetRegistry(
    asset_type="tool",
    name="DocumentSearch",
    description="Hybrid document search (vector + text)",
    tool_type="document_search",
    tool_config={
        "embedding_model": "openai.text-embedding-3-small",
        "search_service": "DocumentSearchService",
        "cache_ttl": 300
    },
    tool_input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 10},
            "search_type": {"type": "string", "enum": ["text", "vector", "hybrid"], "default": "hybrid"},
            "min_relevance": {"type": "number", "default": 0.5}
        },
        "required": ["query"]
    },
    tool_output_schema={
        "type": "object",
        "properties": {
            "results": {"type": "array"},
            "count": {"type": "integer"}
        }
    },
    status="published"
)

await create_asset(tool_asset)
```

**이점**:
- Asset 관리 UI에서 Document Search 도구 관리 가능
- 버전 관리
- 다른 에셋과의 관계 설정

---

## 🎯 최종 결론

### 즉시 구현 필요 (Core)

1. **DocumentSearchService 완성** ← 핵심
   - _vector_search() 구현
   - _text_search() 구현
   - 하이브리드 검색 테스트

2. **DocumentSearchTool 생성** ← OPS CI 통합
   - BaseTool 구현
   - ToolRegistry 등록

3. **단위 + 통합 테스트**

### 선택적 (Enhancement)

1. **Redis 캐싱** (5분 후 추가)
2. **Tool Asset 등록** (배포 후)
3. **성능 모니터링**

---

## 📁 영향받는 파일

| 파일 | 변경 사항 | Priority |
|------|---------|----------|
| `/apps/api/app/modules/document_processor/services/search_service.py` | DB 쿼리 구현 | 1 |
| `/apps/api/app/modules/ops/services/ci/tools/document_search_tool.py` | 新 파일 생성 | 1 |
| `/apps/api/app/modules/ops/services/ci/tools/base.py` | ToolRegistry 등록 | 1 |
| `/apps/api/app/modules/document_processor/router.py` | (변경 불필요, 이미 끝점 있음) | - |
| `/apps/api/tests/test_document_search.py` | 新 테스트 파일 | 1 |
| `/apps/api/app/modules/asset_registry/models.py` | (변경 불필요) | - |

---

## 🚀 배포 순서

1. DocumentSearchService 완성 + 테스트
2. DocumentSearchTool 구현 + 테스트
3. ToolRegistry 통합 + 통합 테스트
4. Redis 캐싱 추가 (선택)
5. 문서화 + 배포

---

Generated: 2026-02-06 by Claude Code Analysis
