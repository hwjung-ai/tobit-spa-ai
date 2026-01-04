## DEV_ENV.md

## 1. 전제
- Postgres/pgvector/Timescale, Neo4j, Redis는 서버에 직접 설치
- 앱은 환경변수(.env)로만 접속

## 2. Backend 환경변수 (apps/api/.env)
예시(커밋 금지, .env.example만 저장소에 둠)

APP_ENV=dev
API_PORT=8000
CORS_ORIGINS=http://localhost:3000

# PostgreSQL
PG_HOST=YOUR_PG_HOST
PG_PORT=5432
PG_DB=tobit
PG_USER=tobit_user
PG_PASSWORD=secret
# 또는 DATABASE_URL 사용 가능
# DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db

# Neo4j
NEO4J_URI=bolt://YOUR_NEO4J_HOST:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=secret
대체 URI 정책: 단일 노드는 `bolt://`, 클러스터는 `neo4j://`로 시작해야 함
예: `bolt://host:7687` 혹은 `neo4j://cluster-uri:7687`.

# Redis
REDIS_URL=redis://YOUR_REDIS_HOST:6379/0

# Seed helper
- `python apps/api/scripts/seed/seed_redis.py` : CEP 접두사(`cep:`)의 string/hash/list 샘플을 Redis에 적재
- `redis-cli -u ${REDIS_URL}` 로 접속 후 `SCAN 0 MATCH cep:* COUNT 100` 등의 명령으로 키를 확인

# Data Explorer (read-only)
ENABLE_DATA_EXPLORER=false
DATA_PG_ALLOW_SCHEMAS=public
DATA_PG_ALLOW_TABLES=tb_cep_*,tb_api_*,ci,ci_ext,event_log
DATA_REDIS_ALLOWED_PREFIXES=cep:
DATA_MAX_ROWS=200
DATA_QUERY_TIMEOUT_MS=3000

# OpenAI
OPENAI_API_KEY=
CHAT_MODEL=gpt-5-nano
EMBED_MODEL=text-embedding-3-small

# Document storage
DOCUMENT_STORAGE_ROOT=apps/api/storage

# SSE 테스트 메모
- Windows PowerShell에서는 기본 `curl`이 `Invoke-WebRequest`로 바인딩되므로 `curl.exe`를 명시 사용하세요.
- `req.json` 파일 예시:
  ```json
  {"message":"SSE 테스트"}
  ```
- 테스트 명령:
  ```
  curl.exe -N -H "Accept:text/event-stream" -H "Content-Type:application/json" -d @req.json http://localhost:8000/chat/stream
  ```
- 문서 스트림은 `curl.exe -N -H "Accept:text/event-stream" -H "Content-Type:application/json" -d "{\"query\":\"요약\"}" http://localhost:8000/documents/<id>/query/stream`로 확인하세요.

# Database migrations
- 테이블을 준비하려면 `apps/api`에서 `alembic upgrade head`를 실행하세요.
- `chat_thread`/`chat_message`는 `deleted_at` nullable이며, `thread_id` 기준으로 메시지를 가져옵니다.
- `alembic upgrade head`는 `documents`/`document_chunks` 테이블과 `vector` pgvector 확장을 함께 준비합니다.

# Worker(RQ)
- `cd apps/api` 후 `rq worker documents`로 문서 큐를 소비합니다 (환경변수 `REDIS_URL`/`DOCUMENT_STORAGE_ROOT` 준비).

## 3. Version Control
- **Format**: All commit messages must serve as a minimal, high-level summary of changes.
- **Workflow**: 
  - Check status: `git status`
  - Stage changes: `git add <file>`
  - Commit: `git commit -m "Concise message"`
