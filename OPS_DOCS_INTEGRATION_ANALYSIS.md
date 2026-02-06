# OPS 모듈과 Docs 메뉴 통합 분석 보고서

**작성일**: 2026-02-06
**분석 범위**: /ops/ci/ask 엔드포인트와 Document 시스템 통합 전략
**상태**: 상세 분석 완료

---

## 1. 현재 아키텍처 다이어그램

### 1.1 /ops/ci/ask 엔드포인트 흐름

```
[Client Request (CiAskRequest)]
                │
                ▼
[ci_ask() - Route Handler]
├─ Request validation & history creation
├─ Trace ID initialization
│
├─ Asset Loading Layer
│  ├─ load_resolver_asset() → Resolver rules
│  ├─ load_catalog_asset()  → Schema context
│  ├─ load_source_asset()   → Source context
│  ├─ load_mapping_asset()  → Graph relations
│  └─ load_policy_asset()   → Plan budget
│
├─ Planning Stage
│  ├─ Question normalization (resolver rules)
│  ├─ planner_llm.create_plan_output()
│  │  └─ Generates: Plan (raw) with Intent, View, Metrics, etc.
│  └─ validator.validate_plan()
│     └─ Returns: Plan (validated)
│
├─ Route Determination
│  ├─ Direct Route → Direct answer response
│  ├─ Reject Route → Rejection response
│  └─ Orchestration Route → CIOrchestratorRunner
│
├─ Execution Stage (CIOrchestratorRunner)
│  ├─ Stage 1: Validate
│  ├─ Stage 2: Execute (Tool Registry execution)
│  │  ├─ Tool selector picks tools based on plan
│  │  └─ Tool executor runs tools
│  ├─ Stage 3: Compose (Response composition)
│  └─ Stage 4: Present (Block generation)
│
├─ Trace & History Persistence
│  ├─ Execution trace storage
│  └─ Query history update
│
└─ [Response (CiAskResponse)]
   ├─ answer: string
   ├─ blocks: Block[]
   ├─ trace: TracePayload
   ├─ next_actions: NextAction[]
   └─ meta: ResponseMetadata
```

### 1.2 Asset Registry 아키텍처

```
[TbAssetRegistry Database Table]
├─ asset_type: "prompt" | "mapping" | "policy" | "query" | "source" | "catalog" | "resolver" | "tool" | "screen"
├─ scope: "ci" | "ops" | custom
├─ status: "draft" | "published"
├─ version: integer
│
├─ Prompt Assets
│  ├─ scope, engine (openai, anthropic, etc)
│  ├─ template: string (system prompt)
│  ├─ input_schema, output_contract
│  └─ Loader: load_prompt_asset(scope, engine, name, version?)
│
├─ Mapping Assets
│  ├─ name (e.g., "graph_relation")
│  ├─ content: JSON dict
│  └─ Loader: load_mapping_asset(mapping_type, version?, scope?)
│
├─ Policy Assets
│  ├─ policy_type (e.g., "plan_budget", "view_depth")
│  ├─ content: JSON dict
│  └─ Loader: load_policy_asset(policy_type, version?, scope?)
│
├─ Query Assets
│  ├─ scope (e.g., "ops")
│  ├─ query_sql, query_cypher, query_http
│  ├─ query_params, query_metadata
│  └─ Loader: load_query_asset(scope, name, version?)
│
├─ Source Assets
│  ├─ name (connection name)
│  ├─ content: { source_type, connection, spec }
│  └─ Loader: load_source_asset(name, version?)
│
├─ Catalog Assets
│  ├─ name (database catalog name)
│  ├─ content: { source_ref, catalog, spec }
│  ├─ schema_json: Full catalog structure
│  └─ Loader: load_catalog_asset(name, version?)
│
├─ Resolver Assets
│  ├─ name (resolver name)
│  ├─ content: { rules, default_namespace }
│  └─ Loader: load_resolver_asset(name, version?)
│
├─ Tool Assets
│  ├─ tool_type: string
│  ├─ tool_config: JSON
│  ├─ tool_input_schema, tool_output_schema
│  └─ Usage: load_all_published_tools() → registry
│
└─ Screen Assets
   ├─ screen_id: string
   └─ schema_json: UI schema
```

### 1.3 Asset Loading 우선순위

각 Loader 함수는 다음 우선순위로 동작:

```
1. Published Asset from DB (TbAssetRegistry.status = "published")
   └─ If version specified: Load specific version
   └─ If version not specified: Load latest published

2. Fallback File (only in dev/test mode, NOT in REAL_MODE)
   └─ resources/{asset_type}/ directory
   └─ Example: resources/prompts/ci/openai.yaml

3. Legacy File (only for mappings)
   └─ app/modules/ops/services/ci/relation_mapping.yaml

4. Hardcoded Defaults (only for policies)
   └─ Built-in default values

ERROR in REAL_MODE if asset not found in DB
└─ Raises: ValueError with guidance to publish asset
```

---

## 2. Document 시스템 현황

### 2.1 Document 모델 구조

```
Table: documents
├─ id (UUID)
├─ tenant_id (multi-tenancy)
├─ user_id (creator)
├─ filename: string
├─ content_type: string (mime type)
├─ size: integer (bytes)
├─ status: DocumentStatus enum
│  ├─ queued
│  ├─ processing
│  ├─ done
│  └─ failed
├─ error_message: string
├─ format: string (pdf, docx, xlsx, pptx, image)
├─ processing_progress: integer (0-100)
├─ total_chunks: integer
├─ error_details: JSON
├─ doc_metadata: JSON (pages, word_count, language, etc)
├─ created_by: string (user ID)
├─ created_at, updated_at, deleted_at: timestamps

Table: document_chunks
├─ id (UUID)
├─ document_id (FK → documents)
├─ chunk_index: integer
├─ page: integer (page number for PDF)
├─ text: string (chunk content)
├─ embedding: Vector[1536] (OpenAI embeddings)
├─ chunk_version: integer
├─ chunk_type: string (text, table, image, mixed)
├─ position_in_doc: integer
├─ page_number, slide_number: integer
├─ table_data: JSON
├─ source_hash: string
├─ relevance_score: float
└─ created_at: timestamp
```

### 2.2 Document 처리 파이프라인

```
[Upload Document]
        │
        ▼
[DocumentIndexService]
├─ Extract chunks from file (PDF/DOCX/TXT)
├─ Generate embeddings using OpenAI embed-3-small
│  └─ Batch embedding: 16 chunks per request
├─ Store chunks in DB with vectors
└─ Mark status: done | failed

[Document Search]
        │
        ▼
[DocumentSearchService]
├─ Embed query string
├─ Vector similarity search (cosine distance)
├─ Retrieve top-k chunks
├─ Score each chunk
└─ Return ranked results
```

### 2.3 Document API 엔드포인트

```
POST /api/documents/upload
├─ Upload file for processing
├─ Create Document record
├─ Queue background processing
└─ Response: { status, document }

GET /api/documents/
├─ List all documents (with filtering)
└─ Response: { documents: Document[] }

GET /api/documents/{document_id}
├─ Get document details
├─ Include chunk count & status
└─ Response: { document: DocumentDetail }

DELETE /api/documents/{document_id}
├─ Soft delete document
└─ Response: { document_id }

GET /api/documents/{document_id}/chunks/{chunk_id}
├─ Get specific chunk details
└─ Response: { chunk: DocumentChunkDetail }

POST /api/documents/{document_id}/query/stream
├─ Query document with streaming response
├─ Vector search + LLM answer generation
└─ Response: Server-Sent Events stream
```

---

## 3. Asset Registry 상세 분석

### 3.1 Asset 타입별 특성

#### Prompt Assets
- **용도**: LLM 프롬프트 템플릿 관리
- **주요 필드**: template (system prompt), input_schema, output_contract
- **로더**: `load_prompt_asset(scope, engine, name, version?)`
- **예시**:
  ```yaml
  asset_type: prompt
  scope: ci
  engine: openai
  name: plan_generator
  template: "You are a CI analysis planner..."
  input_schema: { properties: { question: { type: string } } }
  ```

#### Mapping Assets
- **용도**: 데이터 관계 매핑 (그래프 관계식, 별칭 등)
- **주요 필드**: content (JSON dict)
- **로더**: `load_mapping_asset(mapping_type, version?, scope?)`
- **예시**: graph_relation_mapping.yaml
  ```json
  {
    "graph_relation": {
      "depends_on": ["component"],
      "is_exposed_in": ["api_gateway"],
      ...
    }
  }
  ```

#### Policy Assets
- **용도**: 실행 정책 및 제약사항
- **주요 필드**: policy_type, content
- **로더**: `load_policy_asset(policy_type, version?, scope?)`
- **정책 타입**:
  - `plan_budget`: CPU/메모리 예산
  - `view_depth`: 그래프 깊이 제약

#### Query Assets
- **용도**: 데이터 쿼리 템플릿 저장소
- **주요 필드**: query_sql, query_cypher, query_http, query_params, query_metadata
- **로더**: `load_query_asset(scope, name, version?)`
- **반환값**: (query_dict, asset_identifier)

#### Source Assets
- **용도**: 데이터 소스 연결 정보
- **주요 필드**: content { source_type, connection, spec }
- **로더**: `load_source_asset(name, version?)`
- **지원 타입**: postgres, mysql, oracle, neo4j, mongodb, etc.

#### Catalog Assets
- **용도**: 데이터베이스 스키마 정보
- **주요 필드**: content { source_ref, catalog, spec }, schema_json
- **로더**: `load_catalog_asset(name, version?)`
- **용도**:
  - LLM 프롬프트에 스키마 정보 제공
  - 쿼리 검증 및 자동 완성

#### Resolver Assets
- **용도**: 질문 정규화 및 엔티티 해석
- **주요 필드**: content { rules, default_namespace }
- **로더**: `load_resolver_asset(name, version?)`
- **규칙 타입**:
  - alias_mapping: 엔티티 별칭 매핑
  - pattern_rule: 정규식 패턴 치환
  - transformation: 문자열 변환 (대소문자, 공백 등)

#### Tool Assets
- **용도**: 동적 도구 정의 및 등록
- **주요 필드**: tool_type, tool_config, tool_input_schema, tool_output_schema
- **로더**: `load_all_published_tools() → list[dict]`
- **실행 방식**: DynamicTool을 통한 통일된 실행

### 3.2 Asset Registry 데이터 흐름

```
┌─────────────────────────────────────────────────────────────┐
│                    Admin Panel (UI)                          │
│  ├─ Asset Manager: Create/Edit/Publish Assets               │
│  ├─ Version Control: View/Rollback history                  │
│  └─ Status: Draft → Published → Deprecated                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            Database: TbAssetRegistry                         │
│  ├─ asset_type, name, version, status                       │
│  ├─ content, template, schema_json                          │
│  ├─ created_at, published_at, created_by, published_by      │
│  └─ TbAssetVersionHistory for audit trail                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
           ┌───────────┼───────────┐
           │           │           │
           ▼           ▼           ▼
      [Loader]   [Query]    [Search]
           │           │           │
           ▼           ▼           ▼
    [Asset Cache] [Validator] [Version Control]
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│           Runtime: Asset Usage in OPS                        │
│  ├─ ci_ask() loads assets for planning
│  ├─ planner_llm uses prompt + schema + catalog
│  ├─ validator uses resolver rules + policy constraints
│  └─ orchestrator uses tool registry + mappings
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Asset Loading 오류 처리

```python
# 모드별 동작
if ops_mode == "real":
    # 엄격 모드: DB에서만 로드 가능
    if asset not in DB:
        raise ValueError("[REAL MODE] Asset must be published to DB")
else:
    # 개발/테스트 모드: 파일 폴백 허용
    if asset in DB:
        return DB asset
    elif asset in resource file:
        return resource file (with warning)
    else:
        return None
```

---

## 4. Docs 메뉴와 OPS 통합 방식 분석

### 4.1 현재 Document 시스템의 한계

| 항목 | 현상 | 영향 |
|------|------|------|
| **범위** | Documents API와 OPS 시스템이 분리됨 | 질문 분석 시 문서 정보 미활용 |
| **로더** | Document 전용 로더 없음 | Asset Registry와 불연속 |
| **컨텍스트** | 플래너/검증기에 문서 정보 전달 안 됨 | 질문 생성 최적화 불가 |
| **검색** | Vector search만 지원 (RAG 미흡) | 문맥 이해도 낮음 |
| **정책** | 문서별 접근 제어 없음 | 다중 문서 활용 시 보안 문제 |

### 4.2 통합을 위한 기술적 선택지

#### **Option 1: Document Loader (권장 ⭐⭐⭐⭐⭐)**

**개념**: Document를 새로운 Asset 타입으로 통합

```
Document Asset Flow:
  [Upload Document]
    │
    ▼
  [Document Storage + Indexing]
    │
    ▼
  [Create Document Asset]
    ├─ asset_type: "document"
    ├─ name: {document_id}
    ├─ scope: "ops" | "docs" | custom
    ├─ content: {
    │   document_id: UUID,
    │   filename: string,
    │   size: integer,
    │   format: string,
    │   language: string,
    │   chunk_count: integer,
    │   summary: string,
    │   key_topics: string[],
    │   created_by: string,
    │   upload_timestamp: ISO8601
    │ }
    ├─ schema_json: {
    │   chunks: [{ index, page, text, type, embedding_id }]
    │ }
    └─ status: "published"
    │
    ▼
  [Asset Registry DB]
    │
    ▼
  [ci_ask Request]
    ├─ Load document asset
    ├─ Retrieve top-k chunks via vector search
    ├─ Include in planner context
    └─ Use for validation & answer generation
```

**장점**:
- Asset Registry와 완벽 통합
- 버전 관리 자동 제공
- 권한 제어 일원화
- 플래너/검증기에 seamless 접근

**단점**:
- Document ↔ Asset 동기화 필요
- 저장소 중복 가능성

**구현 난이도**: ★★★☆☆

---

#### **Option 2: Query Asset 기반 RAG (권장 ⭐⭐⭐⭐)**

**개념**: Document 검색을 Query Asset으로 정의

```
Document Query Asset:
  asset_type: "query"
  name: "document_search"
  scope: "ops"
  content: {
    query_type: "semantic_search",
    index: "documents_vector",
    vector_field: "embedding",
    text_fields: ["text", "chunk_type"],
    default_top_k: 5,
    min_relevance_score: 0.7,
    return_fields: ["document_id", "filename", "text", "page", "score"]
  }

Usage in Planner:
  1. Query asset 로드
  2. Semantic search 실행
  3. 결과를 prompt context에 주입
  4. LLM이 문서 정보 활용하여 계획 생성
```

**장점**:
- 기존 Query Asset 인프라 재사용
- 검색 로직 분리 (테스트 용이)
- 다양한 검색 전략 지원 (vector, text, hybrid)
- 캐싱 및 성능 최적화 용이

**단점**:
- Document 자체는 Asset이 아님 (메타 관리 필요)
- 검색 결과만 제공 (문서 메타 제한적)

**구현 난이도**: ★★★☆☆

---

#### **Option 3: Context Injection via Prompt (권장 ⭐⭐⭐)**

**개념**: 선택된 문서를 Prompt 컨텍스트에 직접 주입

```
Modified Planner Prompt Flow:

1. 원래 planner_llm.create_plan_output() 로직
2. 추가: Document Context 검색
   ├─ 질문에서 엔티티 추출
   ├─ Vector 검색으로 관련 문서 찾기
   └─ Top-k chunks 선택
3. 추가: Prompt Template에 문서 정보 포함
   ├─ Documents section in prompt
   ├─ Relevant chunks as context
   └─ Document metadata as sources
4. LLM이 전체 context로 plan 생성

Example Prompt Fragment:
  """
  # Relevant Documents
  Document: {filename} (uploaded {date}, {pages} pages)
  Topics: {topics}
  Relevant sections:
  - Chunk 1: {text} (page {page_no})
  - Chunk 2: {text} (page {page_no})

  Question: {user_question}
  """
```

**장점**:
- 최소 코드 변경
- 유연한 문서 활용
- LLM의 문맥 이해 최대화
- 여러 문서 동시 활용 가능

**단점**:
- 토큰 비용 증가 (긴 컨텍스트)
- 오버헤드 관리 필요
- 문서 메타 저장 별도 필요

**구현 난이도**: ★★☆☆☆

---

#### **Option 4: Document Tool (Tool Registry 확장) (권장 ⭐⭐)**

**개념**: Document 검색을 새로운 도구로 등록

```
Dynamic Tool: DocumentSearchTool

asset_type: "tool"
tool_type: "document_search"
tool_name: "Search Documents"
tool_config: {
  index: "document_chunks",
  vector_model: "openai",
  default_top_k: 5
}
tool_input_schema: {
  properties: {
    query: { type: "string" },
    document_ids: { type: "array", items: "string" },
    top_k: { type: "integer" },
    filters: { type: "object" }
  }
}
tool_output_schema: {
  type: "object",
  properties: {
    chunks: {
      type: "array",
      items: {
        document_id, filename, chunk_index, text, page, score
      }
    }
  }
}

Execution Flow:
  1. CIOrchestratorRunner selects DocumentSearchTool
  2. Tool executor calls DocumentSearchTool.execute()
  3. Returns ranked document chunks
  4. Included in answer/trace
```

**장점**:
- Tool Registry와 일관된 패턴
- 오케스트레이션에 통합
- 재사용 가능한 도구
- 감시/로깅 자동

**단점**:
- Tool 실행 오버헤드
- 런타임 의존성
- 인 플랜 선택 필요 (플래너가 문서 검색 필요성 판단)

**구현 난이도**: ★★★☆☆

---

### 4.3 통합 방식 비교 매트릭스

| 요소 | Option 1<br/>Document Asset | Option 2<br/>Query Asset | Option 3<br/>Context Injection | Option 4<br/>Document Tool |
|------|:---:|:---:|:---:|:---:|
| **Asset Registry 통합** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| **구현 복잡도** | 중간 | 낮음 | 매우낮음 | 중간 |
| **성능** | 우수 | 우수 | 보통 | 보통 |
| **확장성** | 우수 | 우수 | 보통 | 우수 |
| **유지보수** | 좋음 | 좋음 | 좋음 | 우수 |
| **버전 관리** | 자동 | 수동 | 수동 | 자동 |
| **권한 제어** | 일원화 | 분산 | 분산 | 분산 |
| **토큰 효율성** | 우수 | 우수 | 낮음 | 우수 |
| **학습곡선** | 중간 | 낮음 | 매우낮음 | 중간 |
| **기존 인프라 재사용** | 새로 구축 | Query Asset | Prompt | Tool Registry |

---

## 5. 권장 구현 방식: 하이브리드 접근법

### 5.1 최적의 통합 전략 (3단계)

#### **Phase 1: Query Asset 기반 Document Search (즉시 구현 가능)**

```python
# 1. Query Asset 생성
document_search_query = {
    "asset_type": "query",
    "scope": "ops",
    "name": "semantic_document_search",
    "status": "published",
    "query_type": "semantic_search",
    "description": "Search document chunks by semantic similarity",
    "content": {
        "search_strategy": "vector",
        "embedding_model": "openai:text-embedding-3-small",
        "index_source": "document_chunks",
        "vector_field": "embedding",
        "text_field": "text",
        "metadata_fields": ["document_id", "filename", "page", "chunk_index"],
        "default_top_k": 5,
        "min_relevance_score": 0.5
    }
}

# 2. Planner에서 활용
# apps/api/app/modules/ops/services/ci/planner/planner_llm.py

def _load_document_context(question: str, top_k: int = 3) -> str:
    """Load relevant documents for the question."""
    query_asset = load_query_asset("ops", "semantic_document_search")
    if not query_asset:
        return ""

    # Embed question
    query_embedding = embed_text(question)

    # Search documents
    chunks = search_document_chunks(query_embedding, top_k)

    # Format as context
    context = "## Relevant Documents\n"
    for chunk in chunks:
        context += f"- **{chunk['filename']}** (p.{chunk['page']}): {chunk['text'][:200]}...\n"

    return context

# 3. Plan 생성 시 문서 컨텍스트 포함
def create_plan_output(question, schema_context, source_context, **kwargs):
    # ... 기존 로직 ...
    doc_context = _load_document_context(question)

    # 플래너 프롬프트에 추가
    enhanced_question = f"{question}\n\n{doc_context}"

    # ... 계획 생성 ...
```

**Benefits**:
- 기존 Query Asset 인프라 활용
- 최소 코드 변경
- 즉시 구현 가능
- 성능 최적화 (검색 전용)

---

#### **Phase 2: Document Asset로 고도화 (1-2주 작업)**

```python
# 1. Document Upload 시 Asset 자동 생성
# apps/api/api/routes/documents.py

@router.post("/upload")
async def upload_document(file: UploadFile, ...):
    # 기존: Document record 생성
    document = Document(...)
    session.add(document)
    session.commit()

    # NEW: Document Asset 생성
    doc_asset = TbAssetRegistry(
        asset_type="document",
        name=str(document.id),
        scope="docs",
        description=f"Document: {file.filename}",
        content={
            "document_id": document.id,
            "filename": file.filename,
            "size": file.size,
            "format": file_ext,
            "language": detect_language(content),
            "upload_timestamp": datetime.now().isoformat(),
            "created_by": user_id
        },
        status="published"
    )
    session.add(doc_asset)
    session.commit()

    # Queue processing
    enqueue_parse_document(document.id)

# 2. Document Processing 완료 시 Asset 업데이트
# apps/api/workers/parse_document_worker.py

def process_document(document_id: str):
    # 기존: Chunk 생성 및 embedding
    chunks = extract_chunks(document)
    embeddings = embed_chunks(chunks)

    # NEW: Asset metadata 업데이트
    asset = get_asset(asset_type="document", name=document_id)
    if asset:
        asset.schema_json = {
            "chunks": [
                {
                    "index": chunk.chunk_index,
                    "page": chunk.page,
                    "text": chunk.text[:500],
                    "type": chunk.chunk_type
                }
                for chunk in chunks
            ],
            "summary": extract_summary(chunks),
            "topics": extract_topics(chunks)
        }
        asset.version += 1
        session.add(asset)
        session.commit()

# 3. Planner에서 Document Asset 직접 로드
def _load_document_assets() -> list[dict]:
    """Load all published document assets."""
    with get_session_context() as session:
        query = (
            select(TbAssetRegistry)
            .where(TbAssetRegistry.asset_type == "document")
            .where(TbAssetRegistry.scope == "docs")
            .where(TbAssetRegistry.status == "published")
        )
        assets = session.exec(query).all()
        return [
            {
                "document_id": asset.content.get("document_id"),
                "filename": asset.content.get("filename"),
                "summary": asset.schema_json.get("summary"),
                "topics": asset.schema_json.get("topics"),
                "chunks": asset.schema_json.get("chunks", [])
            }
            for asset in assets
        ]
```

**Benefits**:
- Asset Registry와 완벽 통합
- 자동 버전 관리
- 중앙화된 접근 제어
- 감시/로깅 자동

---

#### **Phase 3: Document Tool로 오케스트레이션 확장 (2-3주 작업)**

```python
# 1. DocumentSearchTool 생성
# apps/api/app/modules/ops/services/ci/tools/document_search_tool.py

from app.modules.ops.services.ci.tools import BaseTool, ToolContext, ToolResult

class DocumentSearchTool(BaseTool):
    @property
    def tool_type(self) -> str:
        return "document_search"

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for document chunks"
                },
                "document_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Filter by specific document IDs (optional)"
                },
                "top_k": {
                    "type": "integer",
                    "default": 5,
                    "description": "Number of chunks to return"
                },
                "min_score": {
                    "type": "number",
                    "default": 0.5,
                    "description": "Minimum relevance score"
                }
            },
            "required": ["query"]
        }

    def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        query = kwargs.get("query")
        document_ids = kwargs.get("document_ids")
        top_k = kwargs.get("top_k", 5)
        min_score = kwargs.get("min_score", 0.5)

        try:
            # Embed query
            embedding = embed_text(query)

            # Search chunks
            chunks = search_document_chunks(
                embedding,
                document_ids=document_ids,
                top_k=top_k,
                min_score=min_score,
                tenant_id=context.tenant_id
            )

            return ToolResult(
                success=True,
                data={
                    "query": query,
                    "result_count": len(chunks),
                    "chunks": [
                        {
                            "document_id": chunk.document_id,
                            "filename": chunk.document.filename,
                            "chunk_index": chunk.chunk_index,
                            "page": chunk.page,
                            "text": chunk.text,
                            "score": chunk.relevance_score
                        }
                        for chunk in chunks
                    ]
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
                error_details={"exception_type": type(e).__name__}
            )

# 2. Tool Asset로 등록
document_search_asset = {
    "asset_type": "tool",
    "tool_type": "document_search",
    "name": "Document Search",
    "description": "Search uploaded documents by semantic similarity",
    "scope": "ops",
    "status": "published",
    "tool_config": {
        "implementation_class": "DocumentSearchTool",
        "embed_model": "openai:text-embedding-3-small"
    },
    "tool_input_schema": {
        # ... from DocumentSearchTool.input_schema ...
    },
    "tool_output_schema": {
        "type": "object",
        "properties": {
            "chunks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string"},
                        "filename": {"type": "string"},
                        "text": {"type": "string"},
                        "score": {"type": "number"}
                    }
                }
            }
        }
    }
}

# 3. Planner에서 도구 선택
def determine_tools(question: str, plan: Plan) -> list[str]:
    tools = []

    # 기존 로직...

    # NEW: Document search 필요 여부 판단
    document_keywords = {"문서", "참고", "기록", "정책", "document", "policy", "reference"}
    if any(kw in question.lower() for kw in document_keywords):
        tools.append("document_search")

    return tools

# 4. CIOrchestratorRunner에서 자동 실행
class CIOrchestratorRunner:
    def run(self, plan_output):
        # Stage 2: Execute
        selected_tools = self.tool_selector.select_tools(self.plan)

        for tool_name in selected_tools:
            if tool_name == "document_search":
                result = self.get_tool_executor().execute(
                    tool_type="document_search",
                    kwargs={
                        "query": self.question,
                        "top_k": 5
                    }
                )
                # 결과를 trace에 포함
                self.trace["document_results"] = result.data
```

**Benefits**:
- 오케스트레이션 완전 통합
- 동적 도구 선택
- 감시/로깅/성능 추적
- 재사용 가능한 컴포넌트

---

### 5.2 구현 체크리스트

#### **즉시 구현 (Week 1)**

```
□ Phase 1: Query Asset 기반 Document Search
  □ Query Asset 정의 생성
    □ asset_type: "query"
    □ name: "semantic_document_search"
    □ scope: "ops"

  □ planner_llm.py 수정
    □ _load_document_context() 함수 추가
    □ create_plan_output() 호출 시 문서 컨텍스트 주입
    □ 프롬프트 템플릿 업데이트 (Document section 추가)

  □ 테스트
    □ Unit: _load_document_context() 테스트
    □ Integration: ci_ask with document context
    □ E2E: 문서 로드 → 계획 생성 → 답변

  □ 배포
    □ Query Asset 등록
    □ Feature flag: ops_enable_document_context
    □ A/B 테스트
```

#### **1-2주 구현 (Week 2-3)**

```
□ Phase 2: Document Asset 통합
  □ Document Asset 자동 생성
    □ upload_document() 수정
    □ Document → TbAssetRegistry 변환 로직

  □ Asset 메타데이터 업데이트
    □ process_document() 완료 후 asset.schema_json 업데이트
    □ 요약, 토픽, chunks 정보 추가

  □ Planner 통합
    □ load_document_assets() 함수 추가
    □ Asset 기반 문서 로드 로직

  □ 마이그레이션
    □ 기존 Documents → Document Assets 변환
    □ 배치 처리 (background job)

  □ 테스트
    □ Asset 생성/업데이트 테스트
    □ 다중 문서 로드 테스트
    □ 권한 제어 테스트

  □ 배포
    □ Schema migration
    □ Backfill scripts
    □ Rollback plan
```

#### **2-3주 구현 (Week 4-5)**

```
□ Phase 3: Document Tool
  □ DocumentSearchTool 구현
    □ BaseTool 상속
    □ input_schema, output_schema 정의
    □ execute() 메서드 구현

  □ Tool Asset 등록
    □ DocumentSearchTool을 Tool Asset으로 변환
    □ Registry에 published 상태로 등록

  □ Tool 선택 로직
    □ tool_selector 수정
    □ 질문 분석 → document_search 필요 여부 판단

  □ 오케스트레이션 통합
    □ CIOrchestratorRunner 수정
    □ 도구 실행 → 결과 trace에 포함

  □ 테스트
    □ Tool 단위 테스트
    □ Tool selection 테스트
    □ 종단 간 테스트

  □ 배포
    □ Tool Asset 등록
    □ Feature flag: ops_enable_document_tool
    □ 모니터링 설정
```

---

## 6. 기술 스택 및 성능 고려사항

### 6.1 기술 스택 호환성

```
현재 스택 분석:
├─ 데이터베이스
│  └─ PostgreSQL (pgvector 지원: embedding 저장)
│
├─ ORM
│  └─ SQLModel / SQLAlchemy (Asset Registry 사용 중)
│
├─ 임베딩 모델
│  └─ OpenAI text-embedding-3-small (1536 dimensions)
│
├─ 검색
│  └─ PostgreSQL pgvector (cosine distance)
│
├─ Asset Registry
│  └─ TbAssetRegistry 테이블 (타입: document 추가)
│
└─ 벡터 연산
   └─ scikit-learn (cosine_similarity) - 이미 있음
```

**추가 필요 라이브러리**: None (기존 스택으로 충분)

### 6.2 성능 예상치

```
Document Search 성능:
┌─────────────────────────────────────────┐
│ Operation              │ Duration        │
├───────────────────────┼─────────────────┤
│ Embed query (1536D)   │ ~100-200ms      │
│ Vector search (top-5) │ ~5-10ms         │
│ Score + rank          │ ~1-2ms          │
│ Total (per search)    │ ~110-212ms      │
└─────────────────────────────────────────┘

Batch Processing:
├─ Document upload (100MB): ~2-5s
├─ Chunk extraction: ~1-2s
├─ Batch embedding (16 chunks): ~200-400ms
├─ Vector storage: ~50ms
└─ Total indexing: ~3-7s per document

Memory Usage:
├─ Query Asset cache: ~1MB
├─ Document Asset (1000 docs): ~50-100MB (metadata)
├─ Embedding index (10K chunks): ~20-30MB
└─ Total: ~100-150MB (10K documents)

Concurrency:
├─ Embedding API rate limit: 3500 requests/min
├─ Vector search: ~1000 QPS
├─ Document storage: ~100 concurrent uploads
└─ Recommendation: Connection pool = 20
```

### 6.3 확장성 고려사항

```
스케일링 전략:

Small Scale (< 1,000 docs):
├─ Single PostgreSQL instance
├─ No caching needed
└─ Direct vector search OK

Medium Scale (1,000-10,000 docs):
├─ Add Redis cache for embeddings
├─ Index optimization (B-tree on document_id)
├─ Batch embedding optimization
└─ Connection pooling

Large Scale (> 10,000 docs):
├─ Dedicated embedding service
├─ Vector DB (pgvector → Milvus/Weaviate migration option)
├─ Multi-replica read for search
├─ Document sharding by tenant
└─ Cache warming strategies
```

---

## 7. 보안 및 접근 제어

### 7.1 다중 테넌시 (Multi-tenancy)

```
Document Isolation:
┌─────────────────────────────────────────┐
│ Tenant A                                │
│  ├─ Document 1 → embedding             │
│  ├─ Document 2 → chunks                │
│  └─ Asset: Document (scope: "docs")    │
│                                         │
│ Tenant B                                │
│  ├─ Document 3 → embedding             │
│  ├─ Document 4 → chunks                │
│  └─ Asset: Document (scope: "docs")    │
└─────────────────────────────────────────┘

검색 시 tenant_id 필터링 필수:
WHERE document.tenant_id = current_tenant_id
  AND asset.scope = "docs"
```

### 7.2 접근 제어 (RBAC)

```
Document Asset 권한:
┌─────────────────────────────────────────┐
│ Document Owner (문서 업로드자)          │
│  ├─ Read own documents: Y               │
│  ├─ Share documents: Y                  │
│  ├─ Edit metadata: Y                    │
│  └─ Delete: Y                           │
│                                         │
│ Admin                                   │
│  ├─ Read all: Y                        │
│  ├─ Share: Y                           │
│  ├─ Edit: Y                            │
│  └─ Delete: Y                          │
│                                         │
│ Other Users (공유받음)                 │
│  ├─ Read: Y (권한 있는 경우만)         │
│  ├─ Share: Y (권한 설정 시)            │
│  └─ Delete: N                          │
└─────────────────────────────────────────┘

구현:
├─ asset.created_by: user_id
├─ document_access table: user_id, permission
├─ Query filter: user in (created_by, document_access)
└─ Audit log: document access tracking
```

### 7.3 데이터 보안

```
Sensitive Data Handling:
├─ Document content
│  └─ 암호화: Client-side (전송 중) + Storage (저장 시)
│
├─ Embedding vectors
│  └─ 보호: 민감하지 않음 (역변환 불가능)
│
├─ 메타데이터
│  └─ 보호: 파일명, 페이지 수 등 최소화
│
└─ Access logs
   └─ 저장: Audit trail for compliance
```

---

## 8. 구현 로드맵 및 소요 시간

### 8.1 전체 타임라인

```
Total Effort: 4-6 weeks

┌─────────────┬──────────────────────────────────┬─────────────────┐
│ Phase       │ Activities                       │ Effort (days)   │
├─────────────┼──────────────────────────────────┼─────────────────┤
│ Phase 1     │ Query Asset + Planner Integration│ 5 days          │
│ (Week 1)    │ ├─ Design Query Asset            │ 1 day           │
│             │ ├─ Implement document loader     │ 1.5 days        │
│             │ ├─ Modify planner_llm.py         │ 1.5 days        │
│             │ ├─ Testing & debugging           │ 1 day           │
│             │ └─ Deployment & monitoring       │ 1 day           │
├─────────────┼──────────────────────────────────┼─────────────────┤
│ Phase 2     │ Document Asset + Auto Sync       │ 8-10 days       │
│ (Week 2-3)  │ ├─ Schema: Document Asset fields │ 1 day           │
│             │ ├─ Auto asset creation on upload │ 2 days          │
│             │ ├─ Asset update on processing    │ 2 days          │
│             │ ├─ Loader functions              │ 1 day           │
│             │ ├─ Migration scripts             │ 1 day           │
│             │ ├─ Testing (unit + integration)  │ 2 days          │
│             │ └─ Deployment + backfill         │ 2 days          │
├─────────────┼──────────────────────────────────┼─────────────────┤
│ Phase 3     │ Document Tool + Orchestration    │ 8-10 days       │
│ (Week 4-5)  │ ├─ DocumentSearchTool 구현       │ 2 days          │
│             │ ├─ Tool Asset 등록               │ 1 day           │
│             │ ├─ Tool Selector 수정            │ 2 days          │
│             │ ├─ Orchestrator 통합             │ 1 day           │
│             │ ├─ Testing (unit + E2E)          │ 2 days          │
│             │ └─ Feature flags + deployment    │ 2 days          │
├─────────────┼──────────────────────────────────┼─────────────────┤
│ Documentation│ API docs, guides, runbooks      │ 3 days          │
├─────────────┼──────────────────────────────────┼─────────────────┤
│ Buffer      │ Contingency for issues           │ 5 days          │
└─────────────┴──────────────────────────────────┴─────────────────┘

Total: 4-6 weeks (depending on parallelization)
```

### 8.2 병렬 구현 가능성

```
병렬 진행 가능 (팀 규모 3명):
├─ Developer A: Phase 1 (Query Asset)
├─ Developer B: Phase 2 prep (Schema design, migration)
├─ Developer C: Phase 3 prep (Tool framework)

Checkpoint (Week 2):
├─ Phase 1 완료 및 배포
├─ Phase 2 기본 구조 완료
└─ Phase 3 프레임워크 준비

따라서 단독 개발 시: 4-6주
팀 개발 (3명): 2-3주
```

---

## 9. 위험 요소 및 완화 전략

### 9.1 식별된 위험

```
Risk Matrix:
┌─────────────────────────────────────────────────────────────┐
│ Risk                      │ Probability │ Impact │ Mitigation │
├──────────────────────────┼─────────────┼────────┼────────────┤
│ Embedding API rate limit │ Medium (4)  │ High   │ Queue, batch│
├──────────────────────────┼─────────────┼────────┼────────────┤
│ Vector search latency    │ Low-Medium  │ Medium │ Index optim │
├──────────────────────────┼─────────────┼────────┼────────────┤
│ Token cost explosion     │ Medium (5)  │ High   │ Cache, limit│
├──────────────────────────┼─────────────┼────────┼────────────┤
│ Migration data loss      │ Low (2)     │ High   │ Backup,test │
├──────────────────────────┼─────────────┼────────┼────────────┤
│ Permission regression    │ Low-Medium  │ High   │ RBAC tests  │
├──────────────────────────┼─────────────┼────────┼────────────┤
│ Asset sync conflicts     │ Low (3)     │ Medium │ Versioning  │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 완화 전략

```
Embedding API Quota:
├─ Batch size limit: 16 (현재)
├─ Rate limiting: 3500 req/min
├─ Fallback: Local embedding model (e.g., sentence-transformers)
└─ Monitoring: Alert if > 80% quota used

Vector Search Performance:
├─ Indexing strategy: B-tree on document_id, pgvector HNSW
├─ Query optimization: Limit default top_k to 5
├─ Caching: Redis for recent searches
└─ Monitoring: Track p99 latency

Token Cost Control:
├─ Document context size: Limited to top-3 chunks
├─ Chunk size: Max 1100 chars (existing)
├─ Prompt engineering: Concise format
└─ Monitoring: Track tokens per request

Data Migration:
├─ Dry run: Convert 10% first
├─ Backup: Full DB backup before migration
├─ Rollback: 1-week rollback window
└─ Verification: Data integrity checks

Permission Testing:
├─ RBAC unit tests: 100% coverage
├─ Integration tests: Multi-tenant scenarios
├─ Regression tests: Existing permission logic
└─ Manual testing: Permission combinations

Asset Sync:
├─ Version control: Increment on document change
├─ Timestamps: Update document.updated_at → asset.updated_at
├─ Audit: Log all asset changes
└─ Reconciliation: Weekly sync verification
```

---

## 10. 최종 권장사항

### 10.1 선택 이유: 하이브리드 3단계 접근

**Why not single approach?**
- Option 1 alone: 초기 복잡도 높음
- Option 2 alone: 제한적 기능
- Option 3 alone: 토큰 비효율
- Option 4 alone: 런타임 오버헤드

**Why hybrid?**
```
Phase 1: 빠른 가치 제공 (Quick Win)
  ├─ 1주일 내 기본 기능
  ├─ 즉시 문서 활용
  └─ 사용자 피드백 수집

Phase 2: 체계적 통합 (Systematic)
  ├─ Asset Registry 완벽 통합
  ├─ 버전 관리/권한 제어
  └─ 장기 유지보수성

Phase 3: 고도 활용 (Advanced)
  ├─ 자동 도구 선택
  ├─ 오케스트레이션 완전 통합
  └─ 확장 가능한 아키텍처
```

### 10.2 성공 지표

```
Phase 1 Success Metrics:
├─ Document context loaded in < 500ms
├─ Plan accuracy improvement: +10-15%
├─ User satisfaction: 4.0+/5.0
└─ No performance regression: P99 latency < 2s increase

Phase 2 Success Metrics:
├─ 100% 문서 자동 asset 변환
├─ Migration data integrity: 99.99%
├─ Multi-document support: 5+ docs
└─ Permission error rate: < 0.1%

Phase 3 Success Metrics:
├─ Tool auto-selection accuracy: > 90%
├─ Document tool execution success: > 95%
├─ Answer improvement with docs: +20-25%
└─ Query latency (with docs): < 3s P99
```

### 10.3 다음 단계

1. **이 분석에 대한 피드백 수렴** (1-2일)
   - 팀 검토 및 승인
   - 우선순위 조정
   - 리소스 할당

2. **Phase 1 상세 설계** (2-3일)
   - Query Asset 스키마 확정
   - Planner 프롬프트 템플릿 작성
   - 테스트 계획 수립

3. **구현 시작** (Week 1)
   - 개발 환경 설정
   - 기본 기능 구현
   - 일일 스탠드업

---

## 부록: 코드 스니펫

### A.1 Query Asset 예시

```yaml
# assets/documents_search.yaml
asset_type: query
scope: ops
name: semantic_document_search
version: 1
status: published
description: Search document chunks by semantic similarity

content:
  search_strategy: vector
  embedding_model: openai:text-embedding-3-small
  index_source: document_chunks
  vector_field: embedding
  text_field: text
  metadata_fields:
    - document_id
    - filename
    - page
    - chunk_index
    - chunk_type

  default_parameters:
    top_k: 5
    min_relevance_score: 0.5
    max_chunk_length: 500

  filter_options:
    by_document_id: true
    by_tenant_id: true
    by_date_range: true
    by_format: true

input_schema:
  properties:
    query:
      type: string
      description: Search query text
    document_ids:
      type: array
      items:
        type: string
      description: Filter by specific documents
    top_k:
      type: integer
      default: 5
    min_score:
      type: number
      default: 0.5

output_schema:
  type: object
  properties:
    chunks:
      type: array
      items:
        type: object
        properties:
          document_id:
            type: string
          filename:
            type: string
          page:
            type: integer
          text:
            type: string
          score:
            type: number
```

### A.2 Document Asset 자동 생성 로직

```python
# apps/api/app/modules/document_processor/asset_creator.py

from app.modules.asset_registry.models import TbAssetRegistry
from models import Document
from sqlmodel import Session

def create_document_asset(
    session: Session,
    document: Document,
    summary: str | None = None,
    topics: list[str] | None = None
) -> TbAssetRegistry:
    """
    Create or update Document Asset in Asset Registry.

    Called after document upload/processing.
    """
    asset = TbAssetRegistry(
        asset_type="document",
        name=str(document.id),
        scope="docs",
        description=f"Document: {document.filename}",
        status="published",
        version=1,
        created_by=document.created_by,
        content={
            "document_id": str(document.id),
            "filename": document.filename,
            "size": document.size,
            "format": document.format,
            "content_type": document.content_type,
            "language": detect_language_from_chunks(session, document.id),
            "upload_timestamp": document.created_at.isoformat(),
            "created_by": document.created_by,
            "status": document.status.value
        },
        schema_json={
            "summary": summary,
            "topics": topics or [],
            "chunk_count": count_chunks(session, document.id),
            "page_count": get_max_page_number(session, document.id),
            "document_metadata": document.doc_metadata or {}
        },
        tags={
            "document_type": document.format,
            "tenant_id": document.tenant_id,
            "status": document.status.value
        }
    )

    session.add(asset)
    session.commit()
    session.refresh(asset)

    return asset


def update_document_asset(
    session: Session,
    document: Document,
    summary: str | None = None,
    topics: list[str] | None = None
) -> TbAssetRegistry | None:
    """
    Update existing Document Asset after processing.
    """
    asset = session.exec(
        select(TbAssetRegistry)
        .where(TbAssetRegistry.asset_type == "document")
        .where(TbAssetRegistry.name == str(document.id))
    ).first()

    if not asset:
        return None

    asset.version += 1
    asset.status = "published"
    asset.schema_json = {
        "summary": summary,
        "topics": topics or [],
        "chunk_count": count_chunks(session, document.id),
        "page_count": get_max_page_number(session, document.id),
        "document_metadata": document.doc_metadata or {}
    }

    session.add(asset)
    session.commit()
    session.refresh(asset)

    return asset
```

### A.3 Planner 통합 코드

```python
# apps/api/app/modules/ops/services/ci/planner/planner_llm.py (수정)

from app.modules.asset_registry.loader import load_query_asset
from services.document import DocumentSearchService

def _load_document_context(
    question: str,
    tenant_id: str,
    top_k: int = 3,
    min_score: float = 0.5
) -> str:
    """
    Load relevant documents for enhancing planning context.

    Uses semantic search via Query Asset.
    """
    try:
        # Load semantic search query asset
        query_asset = load_query_asset("ops", "semantic_document_search")
        if not query_asset:
            logger.warning("Document search query asset not found")
            return ""

        # Embed the question
        search_service = DocumentSearchService(get_settings())
        query_embedding = search_service.embed_query(question)

        # Search for relevant chunks
        with get_session_context() as session:
            chunks = search_service.fetch_top_chunks(
                session,
                query_embedding,
                top_k=top_k,
                tenant_id=tenant_id,
                min_relevance_score=min_score
            )

        if not chunks:
            return ""

        # Format documents context
        context = "## 참고 문서\n\n"
        doc_groups = {}

        for chunk in chunks:
            doc_id = chunk.document_id
            if doc_id not in doc_groups:
                doc_groups[doc_id] = {
                    "filename": chunk.document.filename,
                    "chunks": []
                }
            doc_groups[doc_id]["chunks"].append({
                "page": chunk.page,
                "text": chunk.text[:300],
                "score": search_service.score_chunk(chunk, query_embedding)
            })

        for doc_id, doc_info in doc_groups.items():
            context += f"**문서: {doc_info['filename']}**\n"
            for chunk in doc_info["chunks"]:
                page_str = f"(p.{chunk['page']})" if chunk['page'] else ""
                context += f"- {chunk['text']}... {page_str}\n"
            context += "\n"

        return context

    except Exception as e:
        logger.warning(f"Failed to load document context: {e}")
        return ""


def create_plan_output(
    question: str,
    schema_context: dict | None = None,
    source_context: dict | None = None,
    tenant_id: str | None = None,
    **kwargs
) -> PlanOutput:
    """
    Create plan output with document context support.
    """
    # Load document context if tenant_id provided
    doc_context = ""
    if tenant_id:
        doc_context = _load_document_context(
            question,
            tenant_id,
            top_k=3,
            min_score=0.5
        )

    # Enhance question with document context
    enhanced_question = question
    if doc_context:
        enhanced_question = f"{question}\n\n{doc_context}"

    # ... existing planner logic using enhanced_question ...

    # Rest of implementation
    return plan_output
```

---

## 결론

### 핵심 포인트

1. **현재 상태**: OPS와 Document 시스템이 분리되어 있음
2. **권장 방식**: 3단계 하이브리드 접근 (Query Asset → Document Asset → Document Tool)
3. **소요 시간**: 4-6주 (병렬 구현 시 2-3주)
4. **즉시 가치**: Phase 1으로 1주일 내 기본 기능 제공 가능
5. **장기 이점**: Asset Registry 통합으로 관리성/확장성 극대화

### 다음 액션

```
[NOW] ✓ 이 분석 리뷰
         └─ 피드백 수렴 (1-2일)

[THIS WEEK] → Phase 1 상세 설계
            ├─ Query Asset 정확한 구조 정의
            ├─ Planner 프롬프트 템플릿 작성
            └─ 테스트 계획 수립

[NEXT WEEK] → Phase 1 구현 시작
             ├─ Query Asset 등록
             ├─ Planner 통합
             └─ 초기 테스트

[2주차] → Phase 1 배포 + Phase 2 준비

[3주차] → Phase 2 구현

[4-5주차] → Phase 3 구현

[6주차] → 통합 테스트 및 배포
```

---

**문서 작성**: Claude Code AI Assistant
**최종 검토**: 아직 미완료 (팀 검토 대기)
**버전**: 1.0
**상태**: 검토 준비 완료
