# API User Guide

**Last Updated**: 2026-02-08

## 1. 목적

이 가이드는 API Manager를 사용해 동적 API를 생성/실행/검증/운영하는 실무 절차를 설명한다.

## 2. 빠른 시작

1. `/api-manager` 접속
2. API 기본 정보 입력(`name`, `method`, `endpoint`, `logic_type`)
3. Logic 작성(SQL/HTTP/Script/Workflow)
4. Test 실행
5. 저장 후 실행 로그 확인

## 3. API 타입별 작성 가이드

### 3.1 SQL API

- `SELECT`/`WITH` 중심 조회 쿼리 권장
- 파라미터 바인딩 사용(`:tenant_id` 등)
- `limit`/runtime policy로 안전장치 적용

### 3.2 HTTP API

- `method`, `url`, `headers`, `params`, `body` 구성
- 템플릿 치환(`{{params.xxx}}`) 검증
- 외부 endpoint timeout/에러 처리 확인

### 3.3 Script API

- `main(params, input_payload)` 패턴 유지
- 예외 처리와 명시적 반환 구조 권장
- 실행 시간 제한(runtime_policy) 적용

### 3.4 Workflow API

- 노드 순차 실행 구조
- `{{params.*}}`, `{{steps.<id>.*}}` 매핑 사용
- 각 노드 실패 시 처리 정책 사전 정의

## 4. 주요 운영 화면

- Definition 탭: 메타데이터/스키마
- Logic 탭: 타입별 빌더 및 원본 편집
- Test 탭: 실행/결과 확인
- Logs 패널: 실행 이력/오류 추적

## 5. 핵심 API 엔드포인트

- `GET /api-manager/apis`
- `POST /api-manager/apis`
- `PUT /api-manager/apis/{api_id}`
- `DELETE /api-manager/apis/{api_id}`
- `POST /api-manager/apis/{api_id}/execute`
- `GET /api-manager/apis/{api_id}/execution-logs`
- `POST /api-manager/dry-run`

## 6. 보안 및 운영 규칙

- 테넌트 필터 적용 확인
- 민감정보 하드코딩 금지
- 요청/응답 payload 크기 제한
- SQL 인젝션/위험 키워드 차단
- 실행 timeout/row limit 필수

## 7. 배포 전 체크리스트

- 기능 테스트 성공
- 실패 케이스 메시지 확인
- 실행 로그 정상 기록
- 권한/인증 헤더 동작 확인
- 문서(설명, 파라미터, 예시) 업데이트

## 8. 장애 대응

- "Failed to load API definitions": `/api-manager/apis` 응답코드/DB 마이그레이션 점검
- 실행 500: logic body 및 param schema 정합성 확인
- workflow 실패: node별 입력/출력 매핑 검사
- timeout: 외부 API/쿼리 성능 및 정책값 점검

## 9. 개선/고도화 제안

- workflow 고급 DAG/재시도 정책
- 분산 rate limiting
- 캐시 통계 대시보드 강화
- script sandbox 격리 강화
