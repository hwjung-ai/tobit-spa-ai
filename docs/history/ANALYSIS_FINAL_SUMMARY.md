# 문서 시스템 분석 최종 요약

**작성일**: 2026-02-06
**분석 상태**: ✅ 완료
**결론**: **Tools 설정만으로는 불충분 - 3단계 개발 필요**

---

## 🎯 핵심 결론

### "Tools 설정만으로 충분한가?"
**답변**: ❌ **아니오. 개발이 필요합니다.**

### 이유

| 항목 | 현황 | 필요성 |
|------|------|--------|
| **DocumentSearchService** | 구조만 있고 미완성 (Mock code) | ✅ 완성 필요 |
| **DocumentSearchTool** | 존재하지 않음 | ✅ 생성 필요 |
| **DB 쿼리 구현** | pgvector/BM25 쿼리 미구현 | ✅ 구현 필요 |
| **ToolRegistry 등록** | 다른 도구는 있지만 문서 검색 없음 | ✅ 등록 필요 |
| **Asset Registry** | Document와 분리된 시스템 | ❌ 선택사항 (미래) |
| **Redis 캐싱** | CEP에만 사용 중 | ❌ 선택사항 (후) |

---

## 📊 현재 상황 분석

### 1. Document System 현황

✅ **잘 구축된 것**:
- `DocumentChunk` 모델: pgvector embedding 필드 (1536-dim) 있음
- API 라우터: `/api/documents/upload`, `/api/documents/search` 엔드포인트 있음
- `DocumentSearchService`: 클래스 구조 완성
- `ChunkingStrategy`: 문장/단어 기반 청킹 로직 있음

❌ **미완성된 것**:
- `_vector_search()`: Mock 구현만 있음 (DB 쿼리 없음)
- `_text_search()`: Mock 구현만 있음 (DB 쿼리 없음)
- 라우터: `DocumentSearchService` 호출 안 함 (주석 처리됨)

```python
# router.py:258-263 - 주석 처리된 코드!
# results = await search_service.search(
#     query=request.query,
#     filters=filters,
#     top_k=request.top_k,
#     search_type=request.search_type
# )
```

### 2. OPS CI Tool System

✅ **잘 구축된 것**:
- `BaseTool` 추상 인터페이스 (완벽함)
- `ToolRegistry`: 동적 도구 등록/실행 (완벽함)
- `DynamicTool`: Asset Registry에서 Tool 로드 (있음)
- 기존 도구: CITool, MetricTool 등 등록됨

❌ **문서 검색 도구가 없음**:
- DocumentSearchTool 클래스 존재 안 함
- ToolRegistry에 등록되지 않음

### 3. Asset Registry

✅ **기능**:
- Tool Asset 타입 지원
- Query Asset 타입 지원
- JSONB 기반 유연한 필드

❌ **Document와의 관계**:
- Document와 Asset Registry는 완전히 분리됨
- Asset Registry에는 embedding 필드가 없음
- Document 검색은 Asset으로 관리 불가능

---

## 🔍 3가지 통합 방식 비교 (재평가)

### Option 1: DocumentSearchTool (⭐⭐⭐ 권장)

**구조**:
```
OPS CI Pipeline
    ↓
Tool: "document_search"
    ↓
DocumentSearchTool.execute()
    ↓
DocumentSearchService.search()
    ↓
pgvector + BM25 + RRF
    ↓
ToolResult
```

**필요한 개발**:
1. DocumentSearchService DB 쿼리 구현
2. DocumentSearchTool 클래스 생성
3. ToolRegistry 등록

**소요 시간**: ~3-4시간

**장점**:
- 깔끔한 아키텍처
- 기존 OPS CI 패턴과 동일
- 쉬운 유지보수
- 캐싱/모니터링 용이

**단점**:
- 개발 필요

---

### Option 2: Query Asset (⭐ 미권장)

**구조**:
```
QueryAssetRegistry.get_query_asset()
    ↓
Query Asset (tool_type=search, operation=document_search)
    ↓
DynamicTool (tool_type=http_api)
    ↓
DocumentSearchService ← HTTP 호출
```

**문제점**:
- HTTP 오버헤드 불필요
- Tool 인터페이스 어색함
- 내부 서비스 호출이 HTTP로 변환됨

---

### Option 3: Tool Asset + DynamicTool 확장 (⭐ 비권장)

**구조**:
```
Tool Asset (tool_type="document_search")
    ↓
DynamicTool._execute_custom()
    ↓
DocumentSearchService
```

**문제점**:
- DynamicTool 수정 필요
- "document_search" type 인식 로직 추가 필요
- 추후 다른 custom tool 추가 시 DynamicTool 계속 수정 필요

---

## ✅ 권장 구현 경로 (Option 1)

### Phase 1: DocumentSearchService 완성 (우선순위 1)

**파일**: `/apps/api/app/modules/document_processor/services/search_service.py`

```python
# 이 부분을 구현해야 함:
async def _vector_search(self, query, filters, top_k):
    """pgvector 검색 - SQL 쿼리 실행"""
    # 1. Query embedding 생성
    # 2. pgvector <=> cosine similarity 쿼리
    # 3. 결과 파싱 & SearchResult 반환

async def _text_search(self, query, filters, top_k):
    """BM25 검색 - PostgreSQL FTS"""
    # 1. tsvector + plainto_tsquery 사용
    # 2. ts_rank() scoring
    # 3. 결과 파싱 & SearchResult 반환
```

**구현 시간**: 1-1.5시간
**테스트 시간**: 0.5시간

### Phase 2: DocumentSearchTool 생성 (우선순위 1)

**파일**: 신규 파일 생성
`/apps/api/app/modules/ops/services/ci/tools/document_search_tool.py`

```python
class DocumentSearchTool(BaseTool):
    """OPS CI를 위한 Document Search Tool"""

    tool_type = "document_search"
    input_schema = {
        "query": str (필수),
        "top_k": int (기본값: 10),
        "search_type": "hybrid"/"vector"/"text",
        "min_relevance": float (0-1, 기본값: 0.5)
    }

    async def execute(context, input_data) -> ToolResult
```

**구현 시간**: 1시간
**테스트 시간**: 1시간

### Phase 3: ToolRegistry 등록 (우선순위 1)

**파일**: `/apps/api/app/modules/ops/services/ci/tools/base.py`

```python
# ToolRegistry.initialize() 메서드에 추가:
doc_search_tool = DocumentSearchTool(
    search_service=DocumentSearchService()
)
self.register_tool("document_search", doc_search_tool)
```

**구현 시간**: 0.5시간

### Phase 4: 통합 테스트 (우선순위 1)

**테스트 작성**: 0.5시간
**테스트 실행**: 0.5시간

**총 예상 소요 시간**: 3-4시간

---

## 📋 상세 구현 체크리스트

### DocumentSearchService 완성

```
□ _vector_search() 구현
  □ 1. embedding_service.embed(query) 호출
  □ 2. pgvector SQL 쿼리 작성
     SELECT ... WHERE 1 - (embedding <=> $1) > threshold
  □ 3. 결과를 SearchResult[] 파싱
  □ 4. 에러 핸들링 추가

□ _text_search() 구현
  □ 1. PostgreSQL FTS SQL 작성
     WHERE to_tsvector(text) @@ plainto_tsquery($1)
  □ 2. ts_rank() scoring 적용
  □ 3. 결과를 SearchResult[] 파싱
  □ 4. 에러 핸들링 추가

□ 단위 테스트 (test_document_search_service.py)
  □ Vector search 기본 테스트
  □ Text search 기본 테스트
  □ Hybrid search 조합 테스트
  □ min_relevance 필터링 테스트
  □ DB 에러 핸들링 테스트
```

### DocumentSearchTool 생성

```
□ 파일 생성: document_search_tool.py
  □ BaseTool 상속
  □ tool_type = "document_search"
  □ input_schema 정의 (JSON Schema)
  □ execute() 메서드 구현
    □ 입력 검증
    □ SearchFilters 생성
    □ search_service.search() 호출
    □ ToolResult 반환
  □ 에러 처리

□ 단위 테스트 (test_document_search_tool.py)
  □ Tool 메타데이터 테스트
  □ Execute 성공 케이스
  □ Execute 실패 케이스
  □ 입력 검증 테스트
  □ 서비스 에러 핸들링
```

### ToolRegistry 등록

```
□ base.py의 ToolRegistry.initialize() 수정
  □ DocumentSearchTool import 추가
  □ 도구 인스턴스 생성
  □ register_tool("document_search", tool) 호출
  □ 로깅 추가

□ 도구 발견 가능성 확인
  □ get_tool("document_search") 작동
  □ get_available_tools() 포함됨
```

### 통합 테스트

```
□ API 엔드포인트 테스트
  □ POST /api/documents/search 호출
  □ 결과 검증

□ OPS CI 도구 테스트
  □ ToolRegistry에서 도구 로드
  □ execute_tool("document_search", context, input) 호출
  □ ToolResult 검증

□ 엔드-투-엔드 테스트
  □ 문서 업로드 → 임베딩 → 검색 전체 흐름
```

---

## 🚀 배포 계획

### 1단계: 개발 (3-4시간)
- DocumentSearchService 완성
- DocumentSearchTool 생성
- 단위 테스트 작성

### 2단계: 통합 (1시간)
- ToolRegistry 등록
- 통합 테스트 작성
- API 수동 테스트

### 3단계: 최적화 (1시간, 선택)
- Redis 캐싱 추가
- 성능 벤치마킹
- 인덱스 최적화

### 4단계: 배포 (0.5시간)
- 코드 리뷰
- 환경 변수 설정
- 배포

---

## 💡 향후 개선사항 (Phase 2+)

### 즉시 (배포 후 1주)
- [ ] Redis 캐싱 추가 (5분 TTL)
- [ ] 성능 모니터링 설정
- [ ] 사용자 피드백 수집

### 단기 (1-2개월)
- [ ] Tool Asset으로 선택적 등록
- [ ] 검색 결과 랭킹 개선 (LLM reranking)
- [ ] 검색 쿼리 로깅 & 분석

### 중기 (2-3개월)
- [ ] RAG (Retrieval-Augmented Generation) 통합
- [ ] 다국어 지원 (language detection)
- [ ] Faceted search (필터링)

---

## 📁 생성된 문서

이번 분석에서 생성된 3개의 상세 문서:

| 문서 | 용도 | 대상 |
|------|------|------|
| **DOCUMENT_SYSTEM_COMPLETE_ANALYSIS.md** | 전체 아키텍처 + 3가지 옵션 비교 | 아키텍트/리드 |
| **ARCHITECTURE_DIAGRAMS.md** | 상세 다이어그램 + 데이터 흐름 | 모든 개발자 |
| **DOCUMENT_SEARCH_IMPLEMENTATION_GUIDE.md** | 단계별 구현 가이드 + 코드 예제 | 개발자 |

---

## 🎓 핵심 학습 사항

### Document와 Asset Registry는 완전히 다른 시스템
```
Document System:
├─ 목적: 파일 저장 + 임베딩 + 검색
├─ pgvector와 tightly coupled
└─ embedding 필드 보유

Asset Registry:
├─ 목적: 비즈니스 에셋 관리 (도구, 쿼리, 프롬프트 등)
├─ JSONB 기반 유연성
└─ embedding 필드 없음
```

### DocumentSearchService는 구조만 있고 미완성
```
구조 있음:
├─ search() 메서드 완성
├─ _combine_results() (RRF) 완성
└─ SearchFilters/SearchResult 타입 정의

구현 부족:
├─ _vector_search() - Mock only
├─ _text_search() - Mock only
└─ 라우터에서 호출 안 함
```

### OPS CI Tool System은 매우 잘 설계됨
```
완벽함:
├─ BaseTool 추상 인터페이스
├─ ToolRegistry (동적 등록/실행)
├─ ToolContext (컨텍스트 전달)
└─ ToolResult (표준화된 출력)

문서 검색 도구만 빠져있음:
└─ DocumentSearchTool 클래스 생성하면 끝!
```

---

## ⚠️ 주의사항

### 1. Embedding Service 의존성
DocumentSearchTool은 embedding_service에 의존합니다.
- OpenAI API 키 필요
- 네트워크 레이턴시 고려 (캐싱 권장)

### 2. pgvector 확장
PostgreSQL에 pgvector 확장이 설치되어 있어야 합니다.
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. 인덱싱
대규모 문서 검색을 위해 HNSW 인덱스 필수:
```sql
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
```

### 4. 캐싱 (Optional)
Redis 캐싱 없이도 작동하지만, 동일 쿼리 반복 시 성능 저하:
- Vector 임베딩 생성: 2-5초
- 캐싱으로 -> ~10ms

---

## ✅ 최종 체크리스트

이전 분석과의 주요 차이점:

| 항목 | 이전 분석 | 이번 분석 | 변경 사항 |
|------|---------|---------|---------|
| **분류** | 불명확 | 명확 (Option 1) | ✅ 결론 명확화 |
| **필요 개발** | 추측 | 상세 명시 | ✅ 구현 경로 제시 |
| **Code 예제** | 없음 | 완전한 구현 코드 | ✅ 바로 사용 가능 |
| **Test 가이드** | 없음 | 테스트 코드 포함 | ✅ 검증 방법 제공 |
| **소요 시간** | 불명확 | 3-4시간 | ✅ 정확한 예측 |
| **우선순위** | 모두 동등 | 1/2/3 분류 | ✅ 순서 명확화 |

---

## 🎯 결론

### "OPS CI Ask에 대한 최적의 답변"

**질문**: "Document Search를 OPS CI Tool로 통합하려면?"

**답변**:
> **Option 1: DocumentSearchTool** 구현 (3-4시간)
>
> 1. DocumentSearchService에 DB 쿼리 추가 (1.5h)
> 2. DocumentSearchTool 클래스 생성 (1h)
> 3. ToolRegistry에 등록 (0.5h)
> 4. 테스트 (1h)
>
> Tools 설정만으로는 부족합니다.
> 하지만 구현은 매우 직관적이고 명확합니다.

---

**분석 완료**: 2026-02-06
**다음 단계**: DOCUMENT_SEARCH_IMPLEMENTATION_GUIDE.md 참고하여 구현 시작
