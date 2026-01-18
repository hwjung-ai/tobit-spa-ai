# 자산(Asset) 운영 가이드

**작성 일시**: 2026-01-18
**상태**: 최신 (통합 문서)
**대상**: 개발팀, 운영팀

이 문서는 Query Asset, Prompt Asset, Mapping Asset, Policy Asset의 통합 운영 절차를 설명합니다.

---

## 📋 개요

### 자산 종류 및 역할

| 자산 | 용도 | 저장소 | 관리 도구 |
|------|------|--------|---------|
| **Query Asset** | OPS AI의 데이터 조회 | DB (Asset Registry) | Assets Admin UI |
| **Prompt Asset** | LLM 프롬프트 템플릿 | DB (Asset Registry) | Assets Admin UI |
| **Mapping Asset** | 데이터 변환 규칙 | DB (Asset Registry) | Assets Admin UI |
| **Policy Asset** | 시스템 정책 (Rate Limit, 권한 등) | DB (Asset Registry) | Assets Admin UI |

### 생명주기

모든 자산은 동일한 생명주기를 따릅니다:

```
Draft (개발)
  ↓
Publish (릴리즈)
  ↓
Running (운영 중)
  ↓
Rollback (문제 발생 시)
  ↓
Draft (수정) → 다시 Publish
```

---

## 1. Query Asset 운영

### 1.1 개요

#### 정의
- **File Query**: `resources/queries/**/*.sql` 파일 기반 쿼리
- **Query Asset**: Asset Registry(DB)에 저장된 쿼리
- **Published Query**: 실제 운영에 적용 중인 Query Asset

#### 원칙
1. **정본은 Query Asset(DB)**
   - 운영 중에는 Query Asset에서 읽음
   - File Query는 참고/백업 용도로만 사용
2. **File Query는 Seed 용도**
   - 최초 기준이 되는 쿼리 모음
   - 납품(오프라인) 환경 복구용
   - 문서 및 버전 관리 용도

### 1.2 새로운 Query 추가 절차

#### 단계 1: 파일 기반 개발 (개발팀)
```bash
# 1. SQL 파일 작성
$ cat resources/queries/custom/calculate_revenue.sql
SELECT
  DATE_TRUNC('day', created_at) AS date,
  SUM(amount) AS total_revenue
FROM transactions
WHERE status = 'completed'
GROUP BY DATE_TRUNC('day', created_at)
ORDER BY date DESC
LIMIT 30;

# 2. YAML 메타데이터 추가
$ cat resources/queries/custom/calculate_revenue.yaml
name: "Calculate Revenue (30d)"
description: "Calculate daily revenue for the last 30 days"
category: "financial"
tags:
  - revenue
  - daily
  - financial-reporting
version: "1.0"
author: "dev-team"
created_at: "2026-01-18"
```

#### 단계 2: Query Asset 생성 (관리자)
```
1. Assets Admin → [+ New Asset]
2. Type: Query 선택
3. 내용 입력:
   - Name: "Calculate Revenue (30d)"
   - Description: "Calculate daily revenue for the last 30 days"
   - Category: "financial"
   - Tags: revenue, daily, financial-reporting
   - Query Content: [위의 SQL 복사]
4. [Save Draft]
```

#### 단계 3: 검증 및 발행 (관리자)
```
1. Assets Admin → 상세 페이지
2. 테스트 (선택):
   - [Test] 버튼 클릭
   - 샘플 파라미터 입력
   - 결과 확인
3. [Publish] 클릭
4. 감사 로그 자동 기록
```

**완료**: Query Asset이 실제 운영에 적용됨

### 1.3 Query Asset 수정 절차

#### 기존 Query 업데이트

```
1. Assets Admin → Query 검색
2. [Edit] 클릭
   - Status 자동으로 draft로 변경
   - 버전 +0.1 (예: 1.0 → 1.1)
3. 쿼리 수정
4. [Test] 또는 [Save Draft]
5. 테스트 완료 후 [Publish]
```

#### Rollback 절차

```
1. 문제 발견 (오류, 느린 성능, 잘못된 결과)
2. Assets Admin → [Rollback]
3. 이전 Published 버전 선택
4. 롤백 사유 입력: "쿼리 성능 문제 (n+1 쿼리 발생)"
5. [Confirm Rollback]
6. 즉시 이전 버전 적용
```

### 1.4 Query Asset 명명 규칙

```
{domain}_{operation}_{variant}

예:
- ci_get_all_services
- ci_get_services_by_status
- ci_get_service_dependencies
- transaction_calculate_revenue_30d
- transaction_get_top_customers
- user_find_by_email_with_roles
```

### 1.5 Query Asset 체크리스트

발행 전 확인 사항:

- [ ] SQL 문법 검증 (문법 에러 없음)
- [ ] 성능 검증 (EXPLAIN 분석)
- [ ] 보안 검증 (SQL injection 없음, 적절한 권한)
- [ ] 데이터 검증 (올바른 결과값)
- [ ] 명명 규칙 준수 (snake_case, 의미 명확)
- [ ] 주석 추가 (복잡한 로직)
- [ ] 테스트 데이터 (샘플 결과 확인)

---

## 2. Prompt Asset 운영

### 2.1 개요

#### 정의
- **Prompt Asset**: LLM에 전달되는 프롬프트 템플릿
- 변수 치환: `{{inputs.x}}`, `{{state.x}}`, `{{context.x}}`
- 버전 관리: draft/published

### 2.2 새로운 Prompt 추가 절차

#### 단계 1: Prompt 작성 (개발팀)

```
Task: Classify customer message

You are a customer support AI. Classify the following customer message into one of these categories:
- billing
- technical
- general_inquiry
- complaint

Customer Message:
{{inputs.message}}

Additional Context:
- Previous Interactions: {{context.previous_messages}}
- Customer Tier: {{context.customer_tier}}

Respond with JSON:
{
  "category": "...",
  "confidence": 0.0-1.0,
  "reasoning": "..."
}
```

#### 단계 2: Prompt Asset 생성 (관리자)

```
1. Assets Admin → [+ New Asset]
2. Type: Prompt 선택
3. 내용 입력:
   - Name: "Customer Message Classifier"
   - Template: [위의 프롬프트]
   - Input Schema:
     {
       "type": "object",
       "properties": {
         "message": {"type": "string"}
       },
       "required": ["message"]
     }
4. [Save Draft]
```

#### 단계 3: 테스트 및 발행

```
1. [Test] 클릭
2. 샘플 입력:
   message: "내 카드가 거절되었어요"
3. 결과 확인
4. 만족하면 [Publish]
```

### 2.3 Prompt Asset 수정 절차

#### 프롬프트 개선

```
1. 성능 이슈 발견 (정확도 낮음, 느림)
2. Assets Admin → [Edit]
3. 프롬프트 수정:
   - 더 명확한 지시문
   - 예시 추가 (few-shot)
   - 컨텍스트 조정
4. 테스트 (샘플 입력으로 결과 확인)
5. [Publish]
```

#### 변수 변경

```
기존: {{inputs.message}}
신규: {{inputs.customer_message}} (더 명확한 이름)

영향 범위 확인:
- 이 프롬프트를 사용하는 모든 Policy 확인
- Action Handler 코드 확인
- 호환성 유지 또는 동시 업데이트
```

### 2.4 Prompt Asset 체크리스트

발행 전 확인 사항:

- [ ] 템플릿 문법 검증 (`{{variable}}` 형식 올바름)
- [ ] Input Schema 검증 (모든 필수 입력 정의)
- [ ] 테스트 실행 (샘플 입력으로 동작 확인)
- [ ] 출력 형식 검증 (JSON, 텍스트 등)
- [ ] 문화/언어 검수 (오타, 부적절한 표현)
- [ ] 보안 검증 (프롬프트 인젝션 위험 없음)

---

## 3. Mapping Asset 운영

### 3.1 개요

#### 정의
- **Mapping Asset**: 데이터 형식 변환 규칙
- 사용 예: API 응답 → 내부 형식, 데이터 정규화

### 3.2 Mapping Asset 예제

```json
{
  "name": "External API Response to Internal Format",
  "type": "mapping",
  "status": "draft",
  "content": {
    "input_format": "json",
    "output_format": "json",
    "transformations": [
      {
        "from": "data.user.id",
        "to": "userId"
      },
      {
        "from": "data.user.full_name",
        "to": "userName"
      },
      {
        "from": "data.created_timestamp",
        "to": "createdAt",
        "transform": "toISOString"
      },
      {
        "from": "data.status_code",
        "to": "status",
        "mapping": {
          "200": "success",
          "400": "bad_request",
          "500": "error"
        }
      }
    ]
  }
}
```

### 3.3 Mapping Asset 체크리스트

- [ ] 입출력 샘플 데이터 검증
- [ ] 필드 매핑 완전성 (누락된 필드 없음)
- [ ] 타입 변환 정확성 (날짜, 숫자 등)
- [ ] 에지 케이스 처리 (null, 빈 값 등)
- [ ] 성능 검증 (대용량 데이터)

---

## 4. Policy Asset 운영

### 4.1 개요

#### 정의
- **Policy Asset**: 시스템 정책 (Rate Limit, 권한, 타임아웃 등)
- 중앙 집중식 관리로 코드 변경 없이 정책 변경 가능

### 4.2 Policy Asset 예제

#### Rate Limit Policy
```json
{
  "name": "API Rate Limit",
  "type": "policy",
  "status": "published",
  "content": {
    "type": "rate_limit",
    "max_requests_per_minute": 100,
    "max_requests_per_hour": 5000,
    "burst_size": 10,
    "allowed_roles": ["admin", "user"],
    "blocked_roles": [],
    "exemptions": ["system_admin"]
  }
}
```

#### Token Usage Policy
```json
{
  "name": "Token Usage Limits",
  "type": "policy",
  "status": "published",
  "content": {
    "type": "token_limit",
    "max_tokens_per_request": 5000,
    "max_tokens_per_day": 100000,
    "max_tokens_per_month": 1000000,
    "by_role": {
      "admin": {"max_tokens_per_request": 10000},
      "user": {"max_tokens_per_request": 5000},
      "viewer": {"max_tokens_per_request": 1000}
    }
  }
}
```

### 4.3 Policy 변경 절차

#### 영향도 분석
```
1. 어떤 API/기능에 영향?
2. 현재 정책 상태 (Published version)
3. 변경 범위 (모든 사용자 vs 특정 역할)
4. 롤백 계획 (이전 정책 기록)
```

#### 점진적 변경
```
예: Rate Limit 100 → 50으로 감소

1. Draft 생성 (신규 Policy: 50)
2. 10% 사용자 대상 카나리 테스트
3. 이슈 없으면 25%, 50%, 100% 순차 적용
4. 모니터링 (에러율, 사용자 불만)
5. 필요시 원래 값으로 Rollback
```

### 4.4 Policy Asset 체크리스트

- [ ] 정책 충돌 없음 (다른 정책과 모순)
- [ ] 영향도 평가 (주요 기능에 미치는 영향)
- [ ] 테스트 (정책 적용 시나리오)
- [ ] 알림 계획 (사용자 공지)
- [ ] 롤백 계획 (문제 발생 시)

---

## 5. 일반 운영 절차

### 5.1 자산 변경 이력 추적

모든 자산 변경은 자동으로 기록됩니다:

```
Query Asset: ci_get_services
Version History:
- v1.0 (2026-01-10 10:30 by john_dev)
  - Initial version
  - Query: SELECT * FROM ci...

- v1.1 (2026-01-15 14:20 by jane_admin) [Published]
  - Performance optimization
  - Added index on service_id

- v1.2 (2026-01-18 09:15 by john_dev)
  - Draft
  - Added retry logic
```

### 5.2 자산 검색 및 필터

```
Assets Admin 검색 기능:

1. 이름 검색: "revenue" → 관련 Query 찾기
2. 태그 필터: #financial, #revenue → 카테고리별 자산
3. 상태 필터: draft / published / all
4. 타입 필터: query / prompt / mapping / policy
5. 수정자 필터: john_dev → 특정 사용자의 변경사항
6. 날짜 필터: 지난 7일 변경된 자산
```

### 5.3 자산 간 의존성 관리

```
예: Query Asset이 변경되면

1. 이 Query를 사용하는 Policy 찾기
2. 이 Policy를 사용하는 API/기능 찾기
3. 영향도 평가
4. 필요시 관련 자산도 함께 업데이트

의존성 그래프:
Query A → Policy B → Action Handler C → API Endpoint D
         ↘ Mapping E ↗
```

### 5.4 자산 회의 (주간)

```
주간 Asset Review 회의

참석: 개발팀 리드, 운영팀, 관리자

항목:
1. 신규 자산 검토 (이번 주 생성)
2. 문제 자산 롤백 (지난주 발생 이슈)
3. 성능 개선 (느린 Query 최적화)
4. 정책 업데이트 (새로운 요구사항)
5. 삭제 신청 (미사용 자산 정리)

산출물:
- 승인 목록 (Publish 권한)
- 개선 할일 (다음주 우선순위)
- 문서 업데이트 (변경사항 기록)
```

---

## 6. 마이그레이션: File Query → Query Asset

### 6.1 기존 File Query 마이그레이션

#### 1단계: 목록 작성
```bash
$ find resources/queries -name "*.sql" | wc -l
42개의 기존 Query

목록:
- resources/queries/ci/get_services.sql
- resources/queries/ci/get_services_by_status.sql
- ...
```

#### 2단계: 배치 생성
```
각 File Query에 대해:
1. YAML 메타데이터 생성
2. Assets Admin에서 Query Asset 생성
3. Publish
```

#### 3단계: 검증
```
- 모든 Query Asset Published 상태 확인
- File Query 제거 (또는 backup 폴더로 이동)
```

---

## 7. 문제 해결

### Q&A

**Q: Draft 상태의 자산을 삭제할 수 없어요**
A: Draft 자산 삭제는 Admin 권한이 필요합니다. 운영팀 관리자에게 요청하세요.

**Q: Rollback 후 원래 버전으로 돌아갈 수 있나요?**
A: 네. Rollback도 역사 버전이 되므로, 다시 Rollback하여 원래 버전으로 돌아갈 수 있습니다.

**Q: Query 수정 중에 실수로 Publish했어요**
A: 괜찮습니다. 이전 버전으로 Rollback한 후, Draft 모드에서 다시 수정하세요.

**Q: 새 Query를 만들 때 템플릿이 있나요?**
A: CRUD_TEMPLATE.md를 참고하세요 (apps/web/src/lib/ui-screen/CRUD_TEMPLATE.md).

---

**최종 업데이트**: 2026-01-18
**작성자**: Asset Management Team
**검수**: DevOps, Operations
