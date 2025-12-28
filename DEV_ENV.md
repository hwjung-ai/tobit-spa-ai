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

# Redis
REDIS_URL=redis://YOUR_REDIS_HOST:6379/0

# LangSmith(Optional)
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=tobit-spa-ai
LANGSMITH_TRACING=false
