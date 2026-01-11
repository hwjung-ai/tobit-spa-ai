# 개발 환경 설정 (DEV_ENV)

## 1. 전제
- Postgres/pgvector/Timescale, Neo4j, Redis는 서버에 직접 설치되어 있다고 가정합니다.
- 애플리케이션은 환경변수(.env)를 통해 각 서비스에 접속합니다.

## 2. 백엔드 환경변수 (apps/api/.env)

`.env` 파일은 민감한 정보를 포함하므로 Git 저장소에 커밋해서는 안 됩니다. 대신 `.env.example` 파일을 참고하여 각자 환경에 맞게 `.env` 파일을 생성하세요.

### 기본 설정
```env
APP_ENV=dev
API_PORT=8000
CORS_ORIGINS=http://localhost:3000
```

### PostgreSQL
```env
# PostgreSQL
PG_HOST=YOUR_PG_HOST
PG_PORT=5432
PG_DB=tobit
PG_USER=tobit_user
PG_PASSWORD=secret
# 또는 DATABASE_URL 형식 사용 가능
# DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db
```

### Neo4j
```env
# Neo4j
NEO4J_URI=bolt://YOUR_NEO4J_HOST:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secret
```
- **URI 정책**: 단일 노드는 `bolt://`, 클러스터는 `neo4j://`로 시작해야 합니다. (예: `bolt://host:7687` 혹은 `neo4j://cluster-uri:7687`)

### Redis
```env
# Redis
REDIS_URL=redis://YOUR_REDIS_HOST:6379/0
```

### OpenAI
```env
# OpenAI
OPENAI_API_KEY=
CHAT_MODEL=gpt-5-nano
EMBED_MODEL=text-embedding-3-small
```

### Document Storage
```env
# Document storage
DOCUMENT_STORAGE_ROOT=apps/api/storage
```

### Data Explorer (읽기 전용)
```env
# Data Explorer (read-only)
ENABLE_DATA_EXPLORER=false
DATA_PG_ALLOW_SCHEMAS=public
DATA_PG_ALLOW_TABLES=tb_cep_*,tb_api_*,ci,ci_ext,event_log
DATA_REDIS_ALLOWED_PREFIXES=cep:
DATA_MAX_ROWS=200
DATA_QUERY_TIMEOUT_MS=3000
```

## 3. 개발 유틸리티

### 데이터 시딩 (Seed Helper)
- CEP 접두사(`cep:`)를 사용하는 string/hash/list 샘플 데이터를 Redis에 적재합니다.
  ```bash
  python apps/api/scripts/seed/seed_redis.py
  ```
- `redis-cli`로 접속하여 키를 확인할 수 있습니다.
  ```bash
  redis-cli -u ${REDIS_URL}
  # SCAN 0 MATCH cep:* COUNT 100
  ```

### SSE (Server-Sent Events) 테스트
- **참고**: Windows PowerShell에서는 기본 `curl`이 `Invoke-WebRequest`의 별칭이므로, `curl.exe`를 명시적으로 사용해야 합니다.
- `req.json` 파일 예시:
  ```json
  {"message":"SSE 테스트"}
  ```
- **채팅 스트림 테스트**:
  ```bash
  curl.exe -N -H "Accept:text/event-stream" -H "Content-Type:application/json" -d @req.json http://localhost:8000/chat/stream
  ```
- **문서 요약 스트림 테스트**:
  ```bash
  curl.exe -N -H "Accept:text/event-stream" -H "Content-Type:application/json" -d "{\"query\":\"요약\"}" http://localhost:8000/documents/<id>/query/stream
  ```

### 데이터베이스 마이그레이션
- `apps/api` 디렉토리에서 아래 명령을 실행하여 최신 스키마로 업데이트합니다.
  ```bash
  alembic upgrade head
  ```
- `alembic upgrade head`는 `documents`/`document_chunks` 테이블과 `vector` pgvector 확장을 함께 준비합니다.
- `chat_thread`/`chat_message` 테이블은 논리적 삭제를 위해 `deleted_at` 컬럼을 사용합니다.

### RQ (Redis Queue) Worker
- `apps/api` 디렉토리에서 아래 명령을 실행하여 문서 처리 큐 워커를 시작합니다.
- (실행 전 `REDIS_URL`과 `DOCUMENT_STORAGE_ROOT` 환경변수가 설정되어 있어야 합니다.)
  ```bash
  rq worker documents
  ```

## 4. 버전 관리 (Version Control)

### 커밋 메시지 형식 (Format)
- 모든 커밋 메시지는 변경 사항에 대한 최소한의, 높은 수준의 요약으로 작성해야 합니다.

### 작업 흐름 (Workflow)
- 상태 확인: `git status`
- 변경 사항 스테이징: `git add <file>`
- 커밋: `git commit -m "Concise message"`
