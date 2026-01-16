# Tobit SPA AI - 프로젝트 안내

## 1. 문서 개요

이 문서는 Tobit SPA AI 프로젝트의 **최소 실행 안내서**입니다. 설치, 실행, 프로젝트 구조 등 개발에 필요한 가장 기본적인 정보를 제공합니다.

---

## 2. 프로젝트 구조

- `apps/api`: FastAPI 백엔드
- `apps/web`: Next.js 프론트엔드

### 백엔드 (`apps/api`)
- `main.py`: 어플리케이션 진입점 (미들웨어, 라우터 포함)
- `api/`: 핵심 라우터 (비즈니스 로직 또는 DB 접근 지양)
- `app/modules/<도메인>`: 도메인별 모듈 (라우터, 스키마, CRUD, 서비스, 모델 포함)
- `core/`: 공통 인프라 (설정, DB/Redis/Neo4j 연결, 로깅)

### 프론트엔드 (`apps/web`)
- `src/app`: App Router 기반 페이지 및 레이아웃
- `src/components`: 재사용 가능한 UI 컴포넌트
- `src/lib`: 공통 클라이언트 유틸리티 및 API 클라이언트
- `public`: 정적 에셋

---

## 3. 프로젝트 문서

- **[AGENTS.md](./AGENTS.md)**: AI 에이전트가 반드시 준수해야 할 프로젝트 규칙과 기술 스택을 정의합니다.
- **[README.md](./README.md)**: 프로젝트 설치, 실행, 구조에 대한 **Source of Truth** 입니다.
- **[DEV_ENV.md](./DEV_ENV.md)**: 로컬 개발 환경 구축 및 DB 접속 정보 설정 가이드입니다.
- **[docs/FEATURES.md](./docs/FEATURES.md)**: 각 기능의 상세 명세, API 노트, 사용 예시를 제공합니다.
- **[docs/OPERATIONS.md](./docs/OPERATIONS.md)**: 기능 검증을 위한 운영 체크리스트 및 절차를 안내합니다.
- **[docs/PRODUCTION_GAPS.md](./docs/PRODUCTION_GAPS.md)**: MVP에서 프로덕션으로 전환하기 위한 기술 부채 및 개선 항목(TODO) 목록입니다.

---

## 4. 빠른 시작 (로컬 개발)

1.  **백엔드 설정**:
    - `apps/api/.env.example` 파일을 복사하여 `apps/api/.env` 파일을 생성하고, DB 및 외부 서비스 접속 정보를 입력합니다.
    - `python -m venv .venv`로 가상 환경을 생성하고, `source .venv/bin/activate` (Linux/macOS) 또는 `.\.venv\Scripts\activate` (Windows)로 활성화합니다.
    - `pip install -r apps/api/requirements.txt`로 의존성을 설치합니다.
    - `make api-migrate`로 데이터베이스 스키마를 최신 상태로 마이그레이션합니다.

2.  **프론트엔드 설정**:
    - `apps/web/.env.example` 파일을 복사하여 `apps/web/.env.local` 파일을 생성하고, API 서버 주소 등 필요한 환경변수를 설정합니다.
    - `npm install`로 의존성을 설치합니다.
    - Playwright 기반 UI 테스트를 실행하려면 `npx playwright install`로 Playwright와 브라우저 바이너리를 설치합니다.

3.  **전체 실행**:
    - 프로젝트 루트에서 `make dev`를 실행하여 백엔드와 프론트엔드를 동시에 시작합니다.

---

## 5. 주요 명령어 (`Makefile` 기반)

- **전체 실행**:
  - `make dev`: 백엔드와 프론트엔드 개발 서버를 동시에 실행합니다.

- **백엔드**:
  - `make api-dev`: 백엔드 개발 서버를 실행합니다.
  - `make api-lint`: 백엔드 코드 품질을 검사합니다.
  - `make api-format`: 백엔드 코드를 포맷팅합니다.
  - `make api-test`: 백엔드 테스트를 실행합니다.
  - `make api-migrate`: 데이터베이스 스키마를 마이그레이션합니다.

- **프론트엔드**:
  - `make web-dev`: 프론트엔드 개발 서버를 실행합니다.
  - `make web-lint`: 프론트엔드 코드 품질을 검사합니다.
  - `make web-format`: 프론트엔드 코드를 포맷팅합니다.
  - `make web-test`: Playwright 기반 UI 테스트를 실행합니다 (`npx playwright install` 후 실행).

---

## 6. 코드 품질 및 Git 규칙

- **Pre-commit**: `pre-commit`이 Git 커밋 시 자동으로 코드 품질(Ruff, Prettier)을 검사하고 교정합니다.
  - 최초 설정: `pip install pre-commit && pre-commit install`
- **Git 워크플로우**:
  - 큰 변경 전: `git commit -m "checkpoint: before <작업 내용>"`
  - 작업 성공 후: 명확한 메시지와 함께 다시 커밋

---

## 7. 트러블슈팅

- **프론트엔드 API 호출 실패**: `apps/web/.env.local` 파일에 `NEXT_PUBLIC_API_BASE_URL` 환경변수가 올바르게 설정되었는지 확인하세요.
- **DB 테이블 없음 오류**: `make api-migrate`를 실행하여 데이터베이스 스키마를 최신 상태로 업데이트했는지 확인하세요.
- **Python 패키지 오류**: `pip install -r apps/api/requirements.txt`를 다시 실행하여 모든 의존성이 설치되었는지 확인하세요.
