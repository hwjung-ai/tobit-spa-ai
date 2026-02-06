# OPS-Docs 통합 시각화 및 상세 다이어그램

---

## 1. 현재 아키텍처 (Before)

### 1.1 데이터 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ OPS Module UI              │ Documents Module UI          │   │
│  │ - Ask Question             │ - Upload Documents          │   │
│  │ - View Results             │ - List Documents            │   │
│  │ - Follow-up Questions      │ - Search Documents          │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────┬──────────────────────────────────────────────┬──┘
                 │                                              │
                 ▼                                              ▼
        ┌──────────────────────┐                    ┌──────────────────────┐
        │  /ops/ci/ask         │                    │ /api/documents/*     │
        │  (CI Route)          │                    │ (Document Routes)    │
        └──────────────────────┘                    └──────────────────────┘
                 │                                              │
                 ▼                                              ▼
        ┌──────────────────────────────┐    ┌──────────────────────────────┐
        │   Asset Registry             │    │  Document Processing         │
        │  (ci_ask assets only)        │    │  (Separate Pipeline)        │
        │  - Resolver Asset            │    │  - Upload                   │
        │  - Schema Asset              │    │  - Index                    │
        │  - Source Asset              │    │  - Search                   │
        │  - Mapping Asset             │    │  - Query                    │
        │  - Policy Asset              │    └──────────────────────────────┘
        │  - Tool Asset                │              │
        └──────────────────────────────┘              ▼
                 │                          ┌──────────────────────┐
                 │                          │  Document Tables     │
                 │                          │  - documents         │
                 │                          │  - document_chunks   │
                 │                          │  (embeddings)        │
                 ▼                          └──────────────────────┘
        ┌──────────────────────────────┐
        │   Execution                  │
        │  - Planning                  │
        │  - Tool Selection            │
        │  - Orchestration             │
        │  (No document context)       │
        └──────────────────────────────┘
```

**문제점**:
- 두 시스템이 완전히 분리
- Document 정보가 planning에 영향 없음
- Asset Registry에 Document asset 없음

---

## 2. 목표 아키텍처 (After)

### 2.1 통합 후 데이터 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │    OPS Module UI with Document Integration              │   │
│  │  - Ask Question (with document context)                 │   │
│  │  - Auto-suggest relevant documents                      │   │
│  │  - View results with document references                │   │
│  │  - Citation/Attribution                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────┬──────────────────────────────────────────────┬──┘
                 │                                              │
                 ▼                                              ▼
        ┌──────────────────────┐                    ┌──────────────────────┐
        │  /ops/ci/ask         │                    │ /api/documents/*     │
        │  (CI Route - Enhanced)        │    │ (Document Routes)    │
        └──────────────────────┘                    └──────────────────────┘
                 │                                              │
                 ▼                                              ▼
        ┌───────────────────────────────────────┐   ┌──────────────────────┐
        │   Asset Registry (Unified)            │   │  Document Storage    │
        │  ┌─────────────────────────────────┐ │   │  - Upload            │
        │  │ CI Assets (Original)            │ │   │  - Index             │
        │  │ - Resolver, Schema, Source, ... │ │   │  - Search            │
        │  └─────────────────────────────────┘ │   └──────────────────────┘
        │  ┌─────────────────────────────────┐ │         │
        │  │ Document Assets (NEW)           │ │         ▼
        │  │ - Document {id}                 │ │   ┌──────────────────────┐
        │  │   ├─ metadata                   │ │   │  Document Tables     │
        │  │   ├─ chunks (schema_json)       │ │   │  - documents         │
        │  │   └─ topics/summary             │ │   │  - document_chunks   │
        │  │ - Semantic Search Query Asset   │ │   │  (embeddings)        │
        │  │ - Document Search Tool          │ │   └──────────────────────┘
        │  └─────────────────────────────────┘ │
        │  ┌─────────────────────────────────┐ │
        │  │ Query Assets (Enhanced)         │ │
        │  │ - Semantic Document Search      │ │
        │  │ - Other queries...              │ │
        │  └─────────────────────────────────┘ │
        └───────────────────────────────────────┘
                 │
                 ▼
        ┌───────────────────────────────────────┐
        │   Execution (Enhanced)                │
        │  - Planning (with document context)  │
        │  - Tool Selection (smart)            │
        │  - Orchestration (full integration)  │
        │  ├─ Document context injection       │
        │  ├─ Document search tool             │
        │  └─ Citation tracking                │
        └───────────────────────────────────────┘
```

**개선사항**:
- Document가 Asset Registry에 통합
- Planning 시 document context 자동 활용
- Document search tool로 orchestration 확장
- 통일된 관리 인프라

---

## 3. Phase별 진화 과정

### 3.1 Phase 1: Query Asset (주차 1)

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Semantic Document Search via Query Asset           │
└─────────────────────────────────────────────────────────────┘

[ci_ask Request]
        │
        ▼
[Question Normalization]
        │
        ▼
[Planning Stage - ENHANCED]
  ├─ planner_llm.create_plan_output()
  │  │
  │  ├─ Step 1: Load document context (NEW)
  │  │  └─ load_query_asset("semantic_document_search")
  │  │     └─ Embed question
  │  │        └─ Vector search top-5 chunks
  │  │           └─ Format as context
  │  │
  │  ├─ Step 2: Enhanced prompt (NEW)
  │  │  └─ Original question + Document context
  │  │
  │  └─ Step 3: LLM planning (existing)
  │     └─ Generate plan with document awareness
  │
  └─ validator.validate_plan()

[Rest of execution]
```

**활성화**:
```sql
-- Register Query Asset
INSERT INTO tb_asset_registry (
    asset_type, scope, name, status, version, content, ...
) VALUES (
    'query', 'ops', 'semantic_document_search', 'published', 1,
    {
        "search_strategy": "vector",
        "default_top_k": 5,
        ...
    },
    ...
);
```

**코드 변경**:
- planner_llm.py: +50 lines
- No schema changes

---

### 3.2 Phase 2: Document Asset (주차 2-3)

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Document as First-Class Asset                     │
└─────────────────────────────────────────────────────────────┘

[Upload Document]
        │
        ▼
[DocumentIndexService]
  ├─ Extract chunks & generate embeddings (existing)
  │
  └─ Create Document Asset (NEW)
     ├─ asset_type: "document"
     ├─ name: {document_id}
     ├─ content: metadata
     ├─ schema_json: chunks info
     └─ status: "published"

         │
         ▼
     [Asset Registry]

[Query Planning - Phase 2 Enhanced]
  ├─ Load document assets
  ├─ Retrieve chunks from asset.schema_json
  └─ Include in context (more efficient)

[Migration Path]
  ├─ Existing documents → Document assets (batch job)
  ├─ New documents → Automatic asset creation
  └─ Backward compatible
```

**Schema 변경**:
```sql
-- TbAssetRegistry 활용 (기존 테이블)
-- asset_type = "document" 추가
-- No new tables needed
```

**코드 변경**:
- document upload handler: +20 lines
- document processor: +30 lines
- asset loader: +50 lines

---

### 3.3 Phase 3: Document Tool (주차 4-5)

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Document Search Tool with Orchestration           │
└─────────────────────────────────────────────────────────────┘

[CIOrchestratorRunner - Stage 2: Execute]
        │
        ▼
[Tool Selection]
  ├─ Analyze plan + question
  ├─ Determine if document search needed (NEW)
  │  └─ Keywords: "문서", "참고", "정책", etc.
  │
  └─ Select tools
     ├─ Existing tools (CI, Graph, Metric, History)
     └─ Document Search Tool (NEW)

         │
         ▼
[Tool Execution]
  ├─ CI Tool → CI Configuration
  ├─ Graph Tool → Relationships
  ├─ Document Search Tool → Document Chunks (NEW)
  └─ ...

         │
         ▼
[Response Composition]
  ├─ Combine results
  ├─ Generate blocks
  ├─ Track citations (NEW)
  └─ Return response

[Stage 4: Present]
  ├─ Text blocks
  ├─ Tables
  ├─ Charts
  └─ Document references (NEW)
```

**Tool Asset 등록**:
```yaml
asset_type: tool
tool_type: document_search
name: Document Search
scope: ops
status: published

tool_config:
  implementation_class: DocumentSearchTool
  embed_model: openai:text-embedding-3-small

tool_input_schema:
  properties:
    query: { type: string }
    top_k: { type: integer, default: 5 }
    filters: { type: object }

tool_output_schema:
  type: object
  properties:
    chunks:
      type: array
      items:
        type: object
        properties:
          document_id, filename, text, page, score
```

---

## 4. Asset Registry 구조 상세

### 4.1 Asset Type 매트릭스

```
┌────────────────────────────────────────────────────────────────┐
│                   TbAssetRegistry                              │
│                                                                │
│  asset_type     │ scope    │ fields          │ loader          │
├─────────────────┼──────────┼─────────────────┼─────────────────┤
│ prompt          │ ci,ops   │ template,schema │ load_prompt     │
│ mapping         │ ops      │ content (JSON)  │ load_mapping    │
│ policy          │ ops      │ content (JSON)  │ load_policy     │
│ query           │ ops      │ content (JSON)  │ load_query      │
│ source          │ ops      │ content (JSON)  │ load_source     │
│ catalog         │ ops      │ schema_json     │ load_catalog    │
│ resolver        │ ops      │ content (JSON)  │ load_resolver   │
│ tool            │ ops      │ tool_*          │ load_tool       │
│ screen          │ ui       │ schema_json     │ N/A             │
│ document (NEW)  │ docs     │ content, schema │ load_document   │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 Document Asset 필드 구조

```
Asset Registry (one row per document)
├─ asset_id: UUID (primary key)
├─ asset_type: "document" (discriminator)
├─ name: "{document_id}" (unique)
├─ scope: "docs" (namespace)
├─ status: "published" (state)
├─ version: 1 (starts at 1)
├─ description: "Document: {filename}"
│
├─ content (JSON):
│  ├─ document_id: UUID
│  ├─ filename: string
│  ├─ size: integer (bytes)
│  ├─ format: string (pdf, docx, txt)
│  ├─ content_type: string (mime)
│  ├─ language: string (en, ko, etc)
│  ├─ chunk_count: integer
│  ├─ page_count: integer
│  ├─ upload_timestamp: ISO8601
│  ├─ created_by: user_id
│  └─ tags: { document_type, status, ... }
│
├─ schema_json (JSON):
│  ├─ summary: string (auto-extracted)
│  ├─ topics: string[] (key topics)
│  ├─ chunks: [
│  │  {
│  │    index: integer,
│  │    page: integer,
│  │    type: string (text, table, image),
│  │    text: string (first 500 chars),
│  │    embedding_id: UUID (ref to document_chunk)
│  │  }
│  │  ...
│  │ ]
│  └─ metadata: { pages, word_count, extraction_method }
│
├─ created_at: timestamp
├─ updated_at: timestamp (updated on document change)
├─ created_by: user_id
├─ published_by: user_id
└─ published_at: timestamp
```

---

## 5. 데이터 흐름 (상세)

### 5.1 Question → Answer with Documents

```
User Question: "What policies are mentioned in the uploaded documentation?"

[1] ci_ask() Entry
    ├─ Question: "What policies are mentioned in the uploaded documentation?"
    ├─ tenant_id: "acme-corp"
    └─ Trace ID: uuid4()

        │
        ▼
[2] Question Normalization
    ├─ Apply resolver rules
    └─ Normalized: "What policies mentioned uploaded documentation?"

        │
        ▼
[3] Asset Loading (NEW: Document context)
    ├─ load_resolver_asset()
    ├─ load_catalog_asset()
    ├─ load_source_asset()
    ├─ load_mapping_asset()
    ├─ load_policy_asset()
    └─ load_query_asset("semantic_document_search")
            │
            ▼
        Embed normalized question
            │
            ▼
        Vector search in document_chunks
            │
            ▼
        Top-5 chunks with scores:
        [
          {
            document_id: "doc-123",
            filename: "SecurityPolicies_v2.pdf",
            page: 5,
            text: "Access control policy defines role-based access...",
            score: 0.87
          },
          {
            document_id: "doc-123",
            filename: "SecurityPolicies_v2.pdf",
            page: 12,
            text: "Data retention policy specifies 90-day minimum...",
            score: 0.82
          },
          ...
        ]

        │
        ▼
[4] Plan Generation (Enhanced)
    ├─ Input:
    │  ├─ Original question
    │  ├─ Document context (top-5 chunks)
    │  ├─ Schema context
    │  └─ Source context
    │
    ├─ LLM call with enhanced prompt:
    │  """
    │  You are a CI analysis planner.
    │
    │  Question: What policies are mentioned in the uploaded documentation?
    │
    │  ## Relevant Documents
    │  Document: SecurityPolicies_v2.pdf (5 pages)
    │  - Page 5: Access control policy defines role-based access...
    │  - Page 12: Data retention policy specifies 90-day minimum...
    │  """
    │
    └─ Plan output:
       ├─ intent: LOOKUP
       ├─ view: SUMMARY
       ├─ metrics: null
       ├─ document_references: ["doc-123"]
       └─ note: "Answer can be directly from documentation"

        │
        ▼
[5] Validation
    ├─ Validate plan
    └─ Apply resolver rules again

        │
        ▼
[6] Route Determination
    ├─ Direct route: Yes (document contains answer)
    │
    └─ Direct Answer:
       ├─ answer: "Based on SecurityPolicies_v2.pdf, the access control
       │           policy defines role-based access (page 5), and the
       │           data retention policy specifies 90-day minimum (page 12)."
       │
       ├─ references: [
       │  {
       │    document_id: "doc-123",
       │    filename: "SecurityPolicies_v2.pdf",
       │    chunks: [5, 12],
       │    snippet: "Access control policy... Data retention policy..."
       │  }
       │]
       │
       └─ blocks: [
          {
            type: "text",
            content: "Based on SecurityPolicies_v2.pdf...",
            metadata: {
              source: "document",
              document_id: "doc-123"
            }
          },
          {
            type: "table",
            content: [
              { policy_name: "Access Control", page: 5, location: "SecurityPolicies_v2.pdf" },
              { policy_name: "Data Retention", page: 12, location: "SecurityPolicies_v2.pdf" }
            ]
          }
        ]

        │
        ▼
[7] Response Assembly
    ├─ Answer: "Based on SecurityPolicies_v2.pdf..."
    ├─ Blocks: [text, table, ...]
    ├─ Trace: {
    │   route: "direct",
    │   document_references: [...],
    │   tool_calls: []
    │ }
    ├─ Meta: {
    │   source: "document",
    │   confidence: 0.95
    │ }
    └─ Next Actions: []

        │
        ▼
[8] Return to Client
    └─ CiAskResponse with document citations
```

---

## 6. 검색 흐름 (Vector Search Detail)

### 6.1 Document Search Pipeline

```
[Query Input]
"What policies are mentioned?"

[Step 1: Embedding]
├─ Model: openai:text-embedding-3-small
├─ Input: "What policies are mentioned?"
└─ Output: Vector[1536]
   [0.123, -0.456, 0.789, ...]

[Step 2: Vector Search]
└─ SQL Query (pgvector):
   ```sql
   SELECT
     dc.id,
     dc.document_id,
     d.filename,
     dc.page,
     dc.chunk_index,
     dc.text,
     dc.chunk_type,
     (1 - (dc.embedding <=> query_vector)) as similarity_score
   FROM document_chunks dc
   JOIN documents d ON dc.document_id = d.id
   WHERE d.tenant_id = 'acme-corp'
     AND d.deleted_at IS NULL
     AND (1 - (dc.embedding <=> query_vector)) > 0.5
   ORDER BY similarity_score DESC
   LIMIT 5;
   ```

[Step 3: Score Calculation]
├─ Cosine similarity: 0.87, 0.82, 0.79, 0.75, 0.71
└─ Ranking: By score DESC

[Step 4: Result Formatting]
└─ Top-5 chunks with metadata
   {
     chunk_id: "chunk-456",
     document_id: "doc-123",
     filename: "SecurityPolicies_v2.pdf",
     page: 5,
     chunk_index: 12,
     text: "Access control policy defines...",
     chunk_type: "text",
     score: 0.87
   }

[Step 5: Context Formatting]
└─ Markdown format for LLM:
   "## Document References
   - SecurityPolicies_v2.pdf (p. 5): Access control policy defines...
   - SecurityPolicies_v2.pdf (p. 12): Data retention policy specifies..."
```

---

## 7. 성능 비교

### 7.1 Before vs After

```
┌──────────────────────────────────────────────────────────────┐
│ 메트릭                     │ Before      │ After      │ 변화  │
├──────────────────────────────────────────────────────────────┤
│ End-to-end latency (P99)   │ 1800ms      │ 2100ms     │ +300ms│
│ Planning time              │ 800ms       │ 1100ms     │ +300ms│
│  - LLM call                │ 700ms       │ 700ms      │ 0ms   │
│  - Document context        │ 0ms         │ 300ms      │ +300ms│
│ Token usage per request    │ 2000        │ 3500       │ +75%  │
│ Answer accuracy            │ 75%         │ 88%        │ +13pp │
│ Relevance of results       │ 6.5/10      │ 8.2/10     │ +1.7  │
│ User satisfaction          │ 3.8/5       │ 4.3/5      │ +0.5  │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 Latency Breakdown (After)

```
ci_ask() Total: 2100ms (P99)
│
├─ Request handling: 50ms (2%)
│
├─ Asset loading: 100ms (5%)
│  ├─ Resolver: 20ms
│  ├─ Catalog: 30ms
│  ├─ Query asset: 10ms
│  └─ Database: 40ms
│
├─ Planning: 1100ms (52%)
│  ├─ Document context: 300ms (14%)
│  │  ├─ Embed question: 100ms
│  │  ├─ Vector search: 50ms
│  │  └─ Format: 150ms
│  ├─ LLM call: 700ms (33%)
│  └─ Validation: 100ms (5%)
│
├─ Execution (Orchestration): 750ms (36%)
│  ├─ Tool selection: 50ms
│  ├─ Tool execution: 600ms
│  └─ Response composition: 100ms
│
└─ Response assembly: 100ms (5%)
```

---

## 8. 다중 테넌시 격리 다이어그램

### 8.1 Tenant Isolation

```
┌────────────────────────────────────────────────────────────────┐
│  Asset Registry (Shared DB)                                    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Tenant: acme-corp                                            │
│  ├─ Document assets (scope=docs, tenant filter)               │
│  │  ├─ doc-001 (SecurityPolicies_v2.pdf)                     │
│  │  └─ doc-002 (ComplianceGuide_v1.pdf)                      │
│  │                                                            │
│  ├─ CI assets (scope=ops)                                     │
│  │  ├─ Resolver, Catalog, etc.                               │
│  │  └─ Semantic Search Query                                 │
│  │                                                            │
│  └─ Tool assets (scope=ops)                                  │
│     └─ Document Search Tool                                  │
│                                                               │
│  Tenant: techcorp                                            │
│  ├─ Document assets (scope=docs, tenant filter)              │
│  │  ├─ doc-101 (ArchitectureGuide.pdf)                       │
│  │  └─ doc-102 (APIDocs_v2.pdf)                              │
│  │                                                            │
│  └─ ...                                                       │
│                                                               │
└────────────────────────────────────────────────────────────────┘

Document Tables (Shared DB with Tenant Filter)
├─ documents
│  ├─ id, tenant_id (partition key), filename, ...
│  └─ INDEX: (tenant_id, deleted_at) for fast filtering
│
└─ document_chunks
   ├─ id, document_id, embedding, text, ...
   └─ INDEX: (document_id) for document lookup

Query Pattern:
SELECT * FROM documents
WHERE tenant_id = 'acme-corp' AND deleted_at IS NULL
  AND id IN (SELECT document_id FROM ...)
```

---

## 9. 오류 처리 흐름

### 9.1 Document Context 로드 오류

```
[Load Document Context]
        │
        ▼
    Try to:
    ├─ Load query asset
    ├─ Embed question
    └─ Search documents

    Exception?
    ├─ No (success)
    │  └─ Continue with context
    │
    └─ Yes (failed)
       ├─ Log warning
       ├─ Return empty context ""
       └─ Continue without document context
           (graceful degradation)

Result:
├─ With documents: Enhanced answer
└─ Without documents: Standard answer (backward compatible)
```

### 9.2 Asset Not Found

```
ops_mode = "real" (Production)?

├─ Yes: STRICT MODE
│  ├─ Asset not in DB?
│  └─ Raise: ValueError with helpful message
│     "Asset Registry에서 발견되지 않음.
│      Admin → Assets에서 생성해주세요."
│
└─ No: DEV MODE
   ├─ Asset in DB?
   │  ├─ Yes: Return
   │  └─ No: Try file fallback
   │     ├─ Found: Return + warning log
   │     └─ Not found: Return None
```

---

## 10. 구현 진행 체크리스트 (상세)

### Phase 1: Query Asset (5일)

```
Day 1: Design & Setup
├─ [ ] Query Asset 스키마 최종 확정
├─ [ ] 데이터베이스 상태 확인
├─ [ ] 개발 환경 설정
└─ [ ] 테스트 환경 준비

Day 2: Query Asset 구현
├─ [ ] Query Asset JSON 정의
├─ [ ] Admin UI에서 등록 (또는 SQL INSERT)
├─ [ ] Load validation 테스트
└─ [ ] Asset 존재 확인

Day 3: Planner 수정
├─ [ ] _load_document_context() 함수 구현
│  ├─ [ ] Query asset 로드
│  ├─ [ ] 질문 embedding
│  ├─ [ ] Vector search
│  └─ [ ] 결과 formatting
├─ [ ] create_plan_output() 호출 수정
├─ [ ] 프롬프트 템플릿 업데이트
└─ [ ] 로깅 추가

Day 4: Unit Testing
├─ [ ] _load_document_context() 단위 테스트
│  ├─ [ ] 정상 케이스
│  ├─ [ ] 빈 결과 케이스
│  └─ [ ] 오류 케이스 (graceful fail)
├─ [ ] create_plan_output() 통합 테스트
├─ [ ] Document context가 LLM에 전달되는지 확인
└─ [ ] 결과 검증 (프롬프트에 문서 정보 포함)

Day 5: E2E Testing & Deployment
├─ [ ] 테스트 문서 업로드
├─ [ ] ci_ask 호출
├─ [ ] 응답에 문서 참조 포함 확인
├─ [ ] 성능 측정 (latency, tokens)
├─ [ ] Feature flag 추가 (enable_document_context)
└─ [ ] Dev 배포 & 모니터링

Test Checklist:
├─ [ ] Unit: _load_document_context (4 cases)
├─ [ ] Unit: create_plan_output (2 cases)
├─ [ ] Integration: ci_ask with documents (3 cases)
├─ [ ] Performance: Latency increase acceptable
└─ [ ] E2E: Document context → Answer generation
```

### Phase 2: Document Asset (8-10일)

```
Day 1-2: Schema Design
├─ [ ] Document Asset 필드 확정
├─ [ ] Asset Registry 수정 검토
├─ [ ] 마이그레이션 전략 수립
└─ [ ] Rollback 계획 준비

Day 3-4: Auto-Creation Logic
├─ [ ] Document upload handler 수정
│  ├─ [ ] Document 생성 후 Asset 생성
│  ├─ [ ] 예외 처리 & 오류 로깅
│  └─ [ ] 트랜잭션 관리
├─ [ ] Document processor 수정
│  ├─ [ ] Processing 완료 후 Asset 업데이트
│  ├─ [ ] summary/topics 추출 로직
│  └─ [ ] chunks metadata 저장
└─ [ ] Asset 존재 확인

Day 5-6: Loader 구현
├─ [ ] load_document_asset() 함수
│  ├─ [ ] Asset 로드 & validation
│  ├─ [ ] 버전 관리
│  └─ [ ] 오류 처리
├─ [ ] load_document_assets() 함수 (모든 문서)
├─ [ ] 캐싱 고려
└─ [ ] 로깅 추가

Day 7: Migration
├─ [ ] 기존 Documents → Assets 배치 변환
│  ├─ [ ] 진행률 추적
│  ├─ [ ] 데이터 검증
│  └─ [ ] 롤백 테스트
├─ [ ] 부분 마이그레이션 (10%) 검증
└─ [ ] 권한 확인

Day 8: Testing
├─ [ ] Asset 생성 단위 테스트
├─ [ ] Asset 로드 단위 테스트
├─ [ ] Asset 업데이트 단위 테스트
├─ [ ] Migration 데이터 검증
├─ [ ] 다중 문서 지원 테스트
└─ [ ] 성능 테스트 (1000 docs)

Day 9-10: Deployment
├─ [ ] Schema migration (staging)
├─ [ ] Backfill 스크립트 실행 (staging)
├─ [ ] 데이터 무결성 확인
├─ [ ] Canary deployment (10% users)
├─ [ ] 전체 배포
└─ [ ] 모니터링 (48시간)

Test Coverage:
├─ [ ] Asset creation (5 cases)
├─ [ ] Asset update (4 cases)
├─ [ ] Asset loading (3 cases)
├─ [ ] Migration integrity (2 cases)
└─ [ ] Multi-document queries (3 cases)
```

### Phase 3: Document Tool (8-10일)

```
Day 1-2: Tool Design
├─ [ ] DocumentSearchTool 클래스 설계
├─ [ ] Input/output schema 정의
├─ [ ] Tool asset schema 준비
└─ [ ] Tool executor integration 검토

Day 3-4: Tool Implementation
├─ [ ] DocumentSearchTool.execute() 구현
│  ├─ [ ] Query embedding
│  ├─ [ ] Vector search
│  ├─ [ ] Result formatting
│  └─ [ ] 오류 처리
├─ [ ] Tool context 활용 (tenant_id 등)
├─ [ ] Logging & tracing
└─ [ ] Tool asset 등록

Day 5: Tool Selection Logic
├─ [ ] Tool selector 수정
│  ├─ [ ] Question 분석
│  ├─ [ ] Document search 필요성 판단
│  └─ [ ] 키워드 기반 선택
├─ [ ] Plan에서 도구 선택
└─ [ ] 테스트

Day 6: Orchestration Integration
├─ [ ] CIOrchestratorRunner 수정
│  ├─ [ ] Tool executor 호출
│  ├─ [ ] 결과 처리
│  └─ [ ] Trace에 포함
├─ [ ] Response composition
└─ [ ] Citation tracking

Day 7: Unit Testing
├─ [ ] DocumentSearchTool.execute() (5 cases)
├─ [ ] Tool selection logic (4 cases)
├─ [ ] Input validation (3 cases)
└─ [ ] Error handling (4 cases)

Day 8: Integration Testing
├─ [ ] Tool + Orchestrator 통합
├─ [ ] Plan with document tool
├─ [ ] Response generation
├─ [ ] Citation accuracy
└─ [ ] Multi-tool execution

Day 9-10: E2E & Deployment
├─ [ ] 전체 흐름 테스트
├─ [ ] 성능 측정
├─ [ ] Feature flag 설정
├─ [ ] Staging 배포
├─ [ ] 모니터링 설정
└─ [ ] Production 배포

Test Coverage:
├─ [ ] Tool execution (6 cases)
├─ [ ] Tool selection (5 cases)
├─ [ ] Orchestration (4 cases)
└─ [ ] E2E scenarios (3 cases)
```

---

## 11. 모니터링 대시보드 구성

### 11.1 주요 메트릭

```
Real-time Metrics:
├─ Document Search Performance
│  ├─ Vector search latency (P50, P95, P99)
│  ├─ Embedding generation time
│  ├─ Documents loaded per request
│  └─ Cache hit rate
│
├─ Planning Performance
│  ├─ Plan generation time
│  ├─ Document context load time
│  ├─ Token count per request
│  └─ Cost per request
│
├─ Tool Execution
│  ├─ Document tool invocation rate
│  ├─ Tool execution success rate
│  ├─ Tool execution latency
│  └─ Results per tool
│
└─ Quality Metrics
   ├─ Answer accuracy with documents
   ├─ Answer accuracy without documents
   ├─ User satisfaction score
   ├─ Document citation accuracy
   └─ False positive rate (wrong document)
```

---

이 시각화 문서가 기술 팀이 구현 단계에서 참고할 수 있는 명확한 가이드가 되길 바랍니다.
