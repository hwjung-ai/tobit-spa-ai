# Document System Architecture Diagrams

## 1. 현재 시스템 전체 구조

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          OPS CI Orchestration Layer                          │
│  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────────┐  │
│  │   Stage Executor   │  │  Tool Executor     │  │  Query Registry      │  │
│  └────────────────────┘  └────────────────────┘  └──────────────────────┘  │
│         │                        │                         │               │
└─────────┼────────────────────────┼─────────────────────────┼───────────────┘
          │                        │                         │
          ▼                        ▼                         ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │                      Tool Execution Interface                    │
   │                                                                   │
   │  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────┐ │
   │  │   BaseTool      │  │  CITool        │  │ MetricTool       │ │
   │  │ (Abstract)      │  │  (Existing)    │  │ (Existing)       │ │
   │  └─────────────────┘  └────────────────┘  └──────────────────┘ │
   │         ▲                     │                    │             │
   │         │                     │                    │             │
   │         └─────┬───────────────┴────────────────────┘             │
   │               │                                                   │
   │         ┌─────▼──────────────────┐                              │
   │         │  DocumentSearchTool    │ ◄── NEW!                    │
   │         │  (To be implemented)   │                              │
   │         └─────────────────────────┘                              │
   │                    │                                             │
   └────────────────────┼─────────────────────────────────────────────┘
                        │
                        ▼
   ┌─────────────────────────────────────────────────────────────────┐
   │                 Document Processing Services                     │
   │                                                                   │
   │  ┌────────────────────────────────────────────────────────────┐ │
   │  │  DocumentSearchService (Hybrid Search Implementation)      │ │
   │  │                                                             │ │
   │  │  async def search(                                         │ │
   │  │    query: str,                                            │ │
   │  │    filters: SearchFilters,                                │ │
   │  │    top_k: int,                                           │ │
   │  │    search_type: "text"/"vector"/"hybrid"                 │ │
   │  │  ) -> List[SearchResult]:                                │ │
   │  │                                                             │ │
   │  │    if search_type in ["vector", "hybrid"]:               │ │
   │  │      vector_results = await _vector_search()             │ │
   │  │                                                             │ │
   │  │    if search_type in ["text", "hybrid"]:                 │ │
   │  │      text_results = await _text_search()                 │ │
   │  │                                                             │ │
   │  │    if search_type == "hybrid":                           │ │
   │  │      results = _combine_results(               ◄── RRF   │ │
   │  │        text_results, vector_results, top_k)              │ │
   │  │                                                             │ │
   │  │    return results[:top_k]                                 │ │
   │  │                                                             │ │
   │  └────────────────────────────────────────────────────────────┘ │
   │                          │                                       │
   │                          ├──> _vector_search()                  │
   │                          │    - Embed query (1536-dim)          │
   │                          │    - pgvector <=> cosine similarity  │
   │                          │                                       │
   │                          ├──> _text_search()                    │
   │                          │    - to_tsvector(text)               │
   │                          │    - plainto_tsquery($1)             │
   │                          │    - ts_rank() scoring               │
   │                          │                                       │
   │                          └──> _combine_results()                │
   │                               - RRF: 1/(60+rank)                │
   │                               - Merge results                   │
   │                               - Sort by combined score          │
   │                                                                   │
   └────────────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
   ┌─────────┐  ┌──────────┐  ┌────────────────┐
   │ pgvector│  │ BM25     │  │ Redis Cache    │
   │ (Vector │  │(Text)    │  │ (Optional)     │
   │ Search) │  │(Search)  │  │                │
   └─────────┘  └──────────┘  └────────────────┘
        │            │              │
        └────────────┼──────────────┘
                     │
                     ▼
   ┌──────────────────────────────────────────────────────┐
   │          PostgreSQL Database                         │
   │                                                       │
   │  ┌──────────────────────────────────────────────────┐│
   │  │ documents                                        ││
   │  │ ├─ id (PK)                                       ││
   │  │ ├─ tenant_id, user_id                            ││
   │  │ ├─ filename, content_type, size                  ││
   │  │ ├─ status (queued/processing/done/failed)        ││
   │  │ ├─ doc_metadata (JSON)                           ││
   │  │ ├─ processing_progress, total_chunks             ││
   │  │ └─ deleted_at (soft delete)                      ││
   │  └──────────────────────────────────────────────────┘│
   │                      │                                │
   │                      │ FK                            │
   │                      ▼                                │
   │  ┌──────────────────────────────────────────────────┐│
   │  │ document_chunks                                  ││
   │  │ ├─ id (PK)                                       ││
   │  │ ├─ document_id (FK) ────┐                        ││
   │  │ ├─ chunk_index                                   ││
   │  │ ├─ text                                          ││
   │  │ ├─ embedding: Vector(1536) ◄── pgvector! ││
   │  │ ├─ chunk_type (text/table/image/mixed)          ││
   │  │ ├─ page_number, slide_number                     ││
   │  │ ├─ table_data (JSON)                             ││
   │  │ ├─ source_hash (change detection)                ││
   │  │ ├─ chunk_version (incremental updates)           ││
   │  │ └─ relevance_score (search results)              ││
   │  └──────────────────────────────────────────────────┘│
   │                                                       │
   │  Indexes:                                             │
   │  ├─ document_id                                      │
   │  ├─ status (documents)                              │
   │  ├─ embedding (Vector Index for HNSW)               │
   │  └─ text (Full-text search index)                   │
   │                                                       │
   └──────────────────────────────────────────────────────┘

   ┌──────────────────────────────────────────────────────┐
   │          Asset Registry (Future Integration)          │
   │                                                       │
   │  tb_asset_registry                                   │
   │  ├─ asset_id (UUID, PK)                             │
   │  ├─ asset_type: "tool"                              │
   │  ├─ name: "DocumentSearch"                          │
   │  ├─ tool_type: "document_search"                    │
   │  ├─ tool_config: {...}                              │
   │  ├─ tool_input_schema: {...}                        │
   │  ├─ tool_output_schema: {...}                       │
   │  └─ status: "published"                             │
   │                                                       │
   │  (Currently Optional - Tool Class is sufficient)     │
   │                                                       │
   └──────────────────────────────────────────────────────┘
```

---

## 2. Document Search Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Request                              │
│                                                                   │
│  POST /api/documents/search                                      │
│  {                                                               │
│    "query": "payment processing system",                         │
│    "search_type": "hybrid",                                      │
│    "top_k": 10,                                                 │
│    "min_relevance": 0.5                                         │
│  }                                                               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│          DocumentRouter.search_documents() (router.py)           │
│                                                                   │
│  1. Validate query length (≥ 2 chars)                           │
│  2. Extract filters from request                                │
│  3. Call DocumentSearchService.search()                         │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│       DocumentSearchService.search(                              │
│         query, filters, top_k, search_type                      │
│       )                                                          │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ 1. Log search query                                    │    │
│  │ 2. Start timer                                         │    │
│  │                                                        │    │
│  │    if search_type == "text":                          │    │
│  │      results = _text_search(query, filters, top_k*2) │    │
│  │                                                        │    │
│  │    elif search_type == "vector":                      │    │
│  │      results = _vector_search(query, filters, top_k*2)│   │
│  │                                                        │    │
│  │    else:  # hybrid (default)                          │    │
│  │      text_results = _text_search(...)                │    │
│  │      vector_results = _vector_search(...)            │    │
│  │      results = _combine_results(text_results,        │    │
│  │                                  vector_results,      │    │
│  │                                  top_k*2)            │    │
│  │                                                        │    │
│  │ 3. Filter by min_relevance                            │    │
│  │ 4. Return top_k results                               │    │
│  │ 5. Log search execution                               │    │
│  │                                                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼

BRANCH 1              BRANCH 2          BRANCH 3
_vector_search()      _text_search()    _combine_results()


BRANCH 1: Vector Search
──────────────────────────

  1. Embed Query
     query_embedding = await embedding_service.embed(query)
     └─> 1536-dimensional vector

  2. PostgreSQL Vector Search
     ```sql
     SELECT dc.id, dc.document_id, d.filename, dc.text,
            dc.page_number, dc.chunk_type,
            1 - (dc.embedding <=> $1) as similarity
     FROM document_chunks dc
     JOIN documents d ON d.id = dc.document_id
     WHERE d.tenant_id = $2
     AND 1 - (dc.embedding <=> $1) > 0.5
     ORDER BY similarity DESC
     LIMIT 20
     ```

  3. Parse Results to SearchResult[]
     ├─ chunk_id
     ├─ document_id
     ├─ document_name
     ├─ chunk_text
     ├─ page_number
     ├─ relevance_score (similarity)
     └─ chunk_type


BRANCH 2: Text Search
──────────────────────

  1. Build Full-Text Query
     ```sql
     SELECT dc.id, dc.document_id, d.filename, dc.text,
            dc.page_number, dc.chunk_type,
            ts_rank(to_tsvector(dc.text), plainto_tsquery($1)) as rank
     FROM document_chunks dc
     JOIN documents d ON d.id = dc.document_id
     WHERE d.tenant_id = $2
     AND to_tsvector(dc.text) @@ plainto_tsquery($1)
     ORDER BY rank DESC
     LIMIT 20
     ```

  2. Parse Results to SearchResult[]
     ├─ chunk_id
     ├─ document_id
     ├─ document_name
     ├─ chunk_text
     ├─ page_number
     ├─ relevance_score (ts_rank)
     └─ chunk_type


BRANCH 3: Combine Results (RRF)
────────────────────────────────

  Input: text_results[], vector_results[], top_k

  1. Initialize scores dict: {}
  2. Score text results
     for rank, result in enumerate(text_results):
       rrf_score = 1 / (60 + rank)
       scores[result.chunk_id] += rrf_score
       result_map[result.chunk_id] = result

  3. Score vector results
     for rank, result in enumerate(vector_results):
       rrf_score = 1 / (60 + rank)
       scores[result.chunk_id] += rrf_score
       if not in result_map:
         result_map[result.chunk_id] = result

  4. Sort by combined score
     sorted_ids = sorted(scores.keys(),
                        key=lambda x: scores[x],
                        reverse=True)[:top_k]

  5. Build final results
     for chunk_id in sorted_ids:
       result = result_map[chunk_id]
       result.relevance_score = scores[chunk_id]
       combined_results.append(result)

  Return: combined_results


                        │
                        ▼
      ┌─────────────────────────────────┐
      │      Apply min_relevance filter  │
      │                                  │
      │ Filter by min_relevance >= 0.5   │
      │                                  │
      └─────────────────────────────────┘
                        │
                        ▼
      ┌─────────────────────────────────┐
      │      Return top_k results        │
      │                                  │
      │ Slice results[:top_k]            │
      │                                  │
      └─────────────────────────────────┘
                        │
                        ▼
                  SearchResult[]
                  [
                    {
                      chunk_id: "...",
                      document_id: "...",
                      document_name: "file.pdf",
                      chunk_text: "...",
                      page_number: 3,
                      relevance_score: 0.85,
                      chunk_type: "text"
                    },
                    {...},
                    ...
                  ]
                        │
                        ▼
      ┌─────────────────────────────────┐
      │    Router Response               │
      │                                  │
      │ {                                │
      │   "status": "ok",                │
      │   "query": "...",                │
      │   "search_type": "hybrid",       │
      │   "results_count": 10,           │
      │   "results": [...]               │
      │ }                                │
      │                                  │
      └─────────────────────────────────┘
                        │
                        ▼
                  HTTP 200 OK
```

---

## 3. Option 1: DocumentSearchTool Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                      OPS CI Pipeline                             │
│                                                                   │
│  POST /ops/stage/execute                                         │
│  {                                                               │
│    "stage_name": "search_documents",                             │
│    "tools": [                                                    │
│      {                                                           │
│        "tool_name": "document_search",                           │
│        "input": {                                                │
│          "query": "payment system",                              │
│          "top_k": 10,                                           │
│          "search_type": "hybrid"                                │
│        }                                                         │
│      }                                                           │
│    ]                                                             │
│  }                                                               │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│         StageExecutor (OPS CI Orchestration)                     │
│                                                                   │
│  1. Parse stage definition                                       │
│  2. Extract tools: [tool_name, input, ...]                      │
│  3. Create execution context                                     │
│     ├─ tenant_id (from auth)                                    │
│     ├─ user_id (from auth)                                      │
│     ├─ request_id (generate)                                    │
│     └─ trace_id (from headers)                                  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│          ToolRegistry.get_tool("document_search")               │
│                                                                   │
│  Lookup: _tools["document_search"]                              │
│  └─> DocumentSearchTool instance                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│     DocumentSearchTool.execute(context, input_data)             │
│                                                                   │
│  class DocumentSearchTool(BaseTool):                             │
│                                                                   │
│    async def execute(self, context, input_data):                │
│      1. Validate input_data                                     │
│         ├─ query (required)                                     │
│         ├─ top_k (default: 10)                                  │
│         ├─ search_type (default: "hybrid")                      │
│         └─ min_relevance (default: 0.5)                         │
│                                                                   │
│      2. Create SearchFilters                                    │
│         filters = SearchFilters(                                │
│           tenant_id=context.tenant_id,                          │
│           min_relevance=input_data["min_relevance"]             │
│         )                                                        │
│                                                                   │
│      3. Call search_service.search()                            │
│         results = await self.search_service.search(             │
│           query=input_data["query"],                            │
│           filters=filters,                                      │
│           top_k=input_data["top_k"],                           │
│           search_type=input_data["search_type"]                │
│         )                                                        │
│                                                                   │
│      4. Build ToolResult                                        │
│         return ToolResult(                                      │
│           success=True,                                         │
│           data={                                                │
│             "results": [asdict(r) for r in results],          │
│             "count": len(results)                              │
│           },                                                    │
│           metadata={                                            │
│             "query": input_data["query"],                      │
│             "search_type": input_data["search_type"],          │
│             "execution_time_ms": elapsed_time                  │
│           }                                                     │
│         )                                                        │
│                                                                   │
│      Exception Handling:                                        │
│      except Exception as e:                                     │
│        return ToolResult(                                       │
│          success=False,                                         │
│          error=str(e),                                          │
│          error_details={"exception_type": type(e).__name__}    │
│        )                                                        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
                  │ DocumentSearchService.search()
                  │ (See Flow #2 above)
                  │
                  ▼
                  SearchResult[]
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              ToolResult (Standardized Output)                    │
│                                                                   │
│  {                                                               │
│    "success": true,                                             │
│    "data": {                                                    │
│      "results": [                                               │
│        {                                                        │
│          "chunk_id": "...",                                     │
│          "document_id": "...",                                  │
│          "document_name": "file.pdf",                           │
│          "chunk_text": "...",                                   │
│          "page_number": 3,                                      │
│          "relevance_score": 0.85,                               │
│          "chunk_type": "text"                                   │
│        }                                                        │
│      ],                                                         │
│      "count": 10                                                │
│    },                                                           │
│    "error": null,                                               │
│    "error_details": null,                                       │
│    "warnings": [],                                              │
│    "metadata": {                                                │
│      "query": "payment system",                                 │
│      "search_type": "hybrid",                                   │
│      "execution_time_ms": 245                                   │
│    }                                                            │
│  }                                                              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│          StageExecutor (Process Results)                        │
│                                                                   │
│  1. Store tool outputs                                          │
│  2. Apply output mapping (if configured)                        │
│  3. Prepare next stage input                                    │
│  4. Update execution status                                     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
                  Return to Client
                  HTTP 200 OK
```

---

## 4. Data Model Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                  Current Data Models                             │
│                 (Document & Asset Registry)                      │
└─────────────────────────────────────────────────────────────────┘

Document System:
┌────────────────────────────┐
│      Document             │
├────────────────────────────┤
│ id: str (UUID)            │
│ tenant_id: str            │
│ user_id: str              │
│ filename: str             │
│ content_type: str         │
│ size: int                 │
│ status: DocumentStatus    │
│ format: str               │
│ processing_progress: int  │
│ total_chunks: int         │
│ doc_metadata: JSON        │
│ error_details: JSON       │
│ created_at: datetime      │
│ updated_at: datetime      │
│ deleted_at: datetime|null │
└────────┬───────────────────┘
         │ 1:N
         │ (document_id FK)
         ▼
┌────────────────────────────────────────┐
│      DocumentChunk                     │
├────────────────────────────────────────┤
│ id: str (UUID)                         │
│ document_id: str (FK)                  │
│ chunk_index: int                       │
│ text: str                              │
│ embedding: Vector(1536) ◄── pgvector! │
│ chunk_type: str                        │
│ page_number: int|null                  │
│ slide_number: int|null                 │
│ position_in_doc: int|null              │
│ table_data: JSON|null                  │
│ source_hash: str|null                  │
│ chunk_version: int                     │
│ relevance_score: float|null            │
│ created_at: datetime                   │
└────────────────────────────────────────┘


Asset Registry System:
┌────────────────────────────────────────┐
│      TbAssetRegistry                   │
├────────────────────────────────────────┤
│ asset_id: UUID (PK)                    │
│ asset_type: str                        │
│ │ ├─ "prompt"                          │
│ │ ├─ "mapping"                         │
│ │ ├─ "policy"                          │
│ │ ├─ "query"                           │
│ │ ├─ "source"                          │
│ │ ├─ "catalog"                         │
│ │ ├─ "resolver"                        │
│ │ ├─ "tool"                            │
│ │ └─ "screen"                          │
│ name: str                              │
│ description: str|null                  │
│ version: int                           │
│ status: str                            │
│ tags: JSON                             │
│ created_at, updated_at: datetime       │
│                                         │
│ Query Asset Fields:                    │
│ ├─ query_sql: str|null                │
│ ├─ query_cypher: str|null             │
│ ├─ query_http: JSON|null              │
│ ├─ query_params: JSON|null            │
│ └─ query_metadata: JSON|null          │
│    └─ {tool_type, operation, ...}     │
│                                         │
│ Tool Asset Fields:                     │
│ ├─ tool_type: str                     │
│ ├─ tool_config: JSON                  │
│ ├─ tool_input_schema: JSON            │
│ └─ tool_output_schema: JSON           │
│                                         │
│ Prompt Asset Fields:                   │
│ ├─ scope: str|null                    │
│ ├─ engine: str|null                   │
│ ├─ template: str|null                 │
│ ├─ input_schema: JSON|null            │
│ └─ output_contract: JSON|null         │
│                                         │
│ [Mapping, Policy, Source, etc. fields]│
│                                         │
└────────┬─────────────────────────────┘
         │ 1:N
         │ (asset_id FK)
         ▼
┌────────────────────────────────────────┐
│      TbAssetVersionHistory             │
├────────────────────────────────────────┤
│ history_id: UUID (PK)                  │
│ asset_id: UUID (FK)                    │
│ version: int                           │
│ snapshot: JSON (full asset state)      │
│ published_by: str|null                 │
│ published_at: datetime                 │
│ rollback_from_version: int|null        │
└────────────────────────────────────────┘


Key Observations:

1. NO relationship between Document and Asset Registry
   └─ They are completely independent

2. Embedding field EXISTS ONLY in DocumentChunk
   └─ Asset Registry has NO embedding field
   └─ Document Search uses DocumentChunk.embedding

3. SearchResult is OUTPUT ONLY (not persisted)
   └─ Scores are computed at query time
   └─ Not stored in database

4. Tool Asset (TbAssetRegistry with asset_type="tool")
   └─ Can reference DocumentSearchService
   └─ But not required - Tool class is sufficient
```

---

## 5. Redis Caching Architecture (Optional Enhancement)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Redis Cache Layer                             │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Cache Keys Structure                                     │  │
│  │                                                          │  │
│  │ 1. Search Results Cache:                                │  │
│  │    Key: doc_search:{tenant_id}:{query_hash}:{search_type}:top_k
│  │    TTL: 300s (5 minutes)                               │  │
│  │    Value: JSON(SearchResult[])                         │  │
│  │    Purpose: Avoid recomputing identical queries        │  │
│  │                                                          │  │
│  │ 2. Query Embedding Cache:                              │  │
│  │    Key: doc_embed_query:{query_hash}                   │  │
│  │    TTL: 86400s (24 hours)                              │  │
│  │    Value: JSON([float])  # 1536-dim vector            │  │
│  │    Purpose: Avoid re-embedding same query             │  │
│  │                                                          │  │
│  │ 3. Document Metadata Cache:                            │  │
│  │    Key: doc_meta:{tenant_id}:{doc_id}                 │  │
│  │    TTL: 3600s (1 hour)                                │  │
│  │    Value: JSON(Document)                              │  │
│  │    Purpose: Cache document metadata                   │  │
│  │                                                          │  │
│  │ 4. Chunk Vector Cache (Optional):                      │  │
│  │    Key: doc_chunk_embed:{chunk_id}                    │  │
│  │    TTL: 86400s (24 hours)                              │  │
│  │    Value: JSON([float])  # Pre-computed embedding     │  │
│  │    Purpose: Cache chunk embeddings if re-indexed      │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                   │
│                    Caching Flow:                                 │
│                                                                   │
│  DocumentSearchService.search() with Redis:                     │
│  ────────────────────────────────────────────                  │
│                                                                   │
│  1. Generate cache_key from (tenant_id, query, search_type)    │
│                                                                   │
│  2. Try Redis GET                                               │
│     if cached_result:                                          │
│       return SearchResult[]  ◄── Cache HIT!                   │
│                                                                   │
│  3. Execute search (vector + text + RRF)                        │
│                                                                   │
│  4. Store in Redis with TTL                                     │
│     redis.setex(cache_key, 300, json.dumps(results))           │
│                                                                   │
│  5. Return SearchResult[]                                       │
│                                                                   │
│  Cache Invalidation:                                            │
│  ──────────────────                                            │
│  When Document is updated/deleted:                             │
│                                                                   │
│  Pattern 1: Full invalidation                                   │
│             redis.delete_pattern(f"doc_search:{tenant_id}:*")  │
│                                                                   │
│  Pattern 2: Selective invalidation (if keywords known)          │
│             for each query_in_cache:                           │
│               if document_keywords in query:                    │
│                 redis.delete(cache_key)                        │
│                                                                   │
│  Pattern 3: Timestamp-based (explicit TTL expiry)              │
│             Let Redis TTL handle expiration naturally          │
│                                                                   │
│  Recommendation: Use Pattern 1 (simplest & most reliable)      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

Integration with DocumentSearchService:

┌────────────────────────────────────────┐
│  DocumentSearchService                 │
│  ├─ redis_client: Redis|None          │
│  └─ async def search(...)              │
│                                         │
│  __init__(                              │
│    db_session=None,                    │
│    embedding_service=None,             │
│    redis_client=None  ◄── NEW param   │
│  ):                                     │
│    self.redis = redis_client           │
│                                         │
│  async def search(...):                 │
│    cache_key = self._make_cache_key(...) │
│                                         │
│    if self.redis:                       │
│      cached = await self.redis.get(cache_key)
│      if cached:                         │
│        return json.loads(cached)        │
│                                         │
│    results = await self._execute_search(...)
│                                         │
│    if self.redis and results:           │
│      await self.redis.setex(            │
│        cache_key,                       │
│        300,  # 5 minutes                │
│        json.dumps([asdict(r) for r in results])
│      )                                   │
│                                         │
│    return results                       │
│                                         │
└────────────────────────────────────────┘
```

---

## 6. Tool Registry Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                     ToolRegistry                                 │
│                                                                   │
│  Singleton Pattern: _global_tool_registry                        │
│                                                                   │
│  class ToolRegistry:                                             │
│    def __init__(self):                                          │
│      self._tools: Dict[str, BaseTool] = {}                     │
│                                                                   │
│    def register_tool(self, name: str, tool: BaseTool):         │
│      self._tools[name] = tool                                   │
│                                                                   │
│    def get_tool(self, name: str) -> BaseTool|None:             │
│      return self._tools.get(name)                               │
│                                                                   │
│    def get_available_tools() -> Dict[str, BaseTool]:            │
│      return self._tools                                          │
│                                                                   │
│    async def execute_tool(                                      │
│      name: str,                                                 │
│      context: ToolContext,                                      │
│      input_data: dict                                           │
│    ) -> ToolResult:                                             │
│      tool = self.get_tool(name)                                │
│      if not tool:                                              │
│        raise ToolNotFoundError(name)                           │
│      return await tool.execute(context, input_data)            │
│                                                                   │
│  Built-in Tools Registered:                                     │
│  └─ At module initialization (registry_init.py)                 │
│     ├─ "ci_search" → CITool                                    │
│     ├─ "metric_aggregate" → MetricTool                         │
│     ├─ "history_query" → HistoryTool                           │
│     ├─ "graph_expand" → GraphTool                              │
│     ├─ "document_search" → DocumentSearchTool ◄── NEW!         │
│     └─ [Any other registered tools]                            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘

Initialization Flow:

┌──────────────────────────┐
│ Application Startup      │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ registry_init.py                     │
│ initialize_tool_registry()           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ ToolRegistry.initialize()            │
│                                      │
│ # Register built-in tools            │
│ registry.register_tool(              │
│   "ci_search",                       │
│   CITool()                           │
│ )                                    │
│                                      │
│ registry.register_tool(              │
│   "metric_aggregate",                │
│   MetricTool()                       │
│ )                                    │
│                                      │
│ registry.register_tool(              │
│   "document_search",  ◄── NEW!      │
│   DocumentSearchTool(                │
│     search_service=DocumentSearchService()
│   )                                  │
│ )                                    │
│                                      │
│ # Load dynamic tools from Asset DB   │
│ assets = session.exec(               │
│   select(TbAssetRegistry)            │
│   .where(asset_type == "tool")       │
│   .where(status == "published")      │
│ ).all()                              │
│                                      │
│ for asset in assets:                 │
│   tool = DynamicTool(asset)          │
│   registry.register_tool(asset.name, tool)
│                                      │
└──────────────────────────────────────┘
               │
               ▼
         Ready for use!

Tool Discovery Usage:

┌───────────────────────────────────────────┐
│ Client Code                               │
└───────────────┬─────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────┐
│ registry = get_tool_registry()            │
│                                           │
│ # Option 1: Get specific tool             │
│ tool = registry.get_tool("document_search")
│ result = await tool.execute(context, input)
│                                           │
│ # Option 2: List all tools                │
│ tools = registry.get_available_tools()    │
│ for name, tool in tools.items():          │
│   print(f"{name}: {tool.tool_type}")      │
│                                           │
│ # Option 3: Execute tool by name          │
│ result = await registry.execute_tool(     │
│   "document_search",                      │
│   context,                                │
│   {"query": "...", "top_k": 10}          │
│ )                                         │
│                                           │
└───────────────────────────────────────────┘
```

---

Generated: 2026-02-06 | Mermaid diagrams can be rendered on GitHub/GitLab
