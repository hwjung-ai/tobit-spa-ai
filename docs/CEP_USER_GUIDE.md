# CEP User Guide

**Last Updated**: 2026-02-08

## 1. 목적

이 가이드는 CEP(Complex Event Processing)를 운영자가 실제로 설정/검증/운영하는 방법을 설명한다.
대상은 알림 규칙을 만들고, 이벤트를 모니터링하고, 장애 상황에서 원인을 추적해야 하는 사용자다.

## 2. 빠른 시작

1. `/cep-builder`에서 규칙을 생성한다.
2. 트리거(`metric`, `event`, `schedule`, `anomaly`)를 선택한다.
3. 액션(웹훅/알림/API 실행)을 연결한다.
4. `simulate`로 사전 검증한다.
5. 규칙을 활성화하고 `/cep-events`에서 이벤트를 확인한다.

## 3. 핵심 개념

### 3.1 처리 흐름

`Event Input -> Filter -> Aggregation -> Anomaly(optional) -> Window -> Action -> Notification`

### 3.2 트리거 타입

- `metric`: 임계값 기반
- `event`: 이벤트 페이로드 조건 기반
- `schedule`: cron 기반
- `anomaly`: 통계 이상 탐지 기반

### 3.3 액션 타입

- 알림 채널 발송
- API Engine 호출
- 후속 Rule 체이닝

## 4. 주요 화면

### 4.1 Rule Builder (`/cep-builder`)

- 규칙 목록/상세/생성/수정
- 트리거 조건 편집
- 액션 체인 구성
- 시뮬레이션 실행

### 4.2 Events (`/cep-events`)

- 발생 이벤트 목록
- 심각도/규칙/시간 필터
- 이벤트 상세 확인
- ACK 처리

### 4.3 Admin 연계

- `assets`: CEP 관련 Tool/Policy/Template 자산 관리
- `observability`: CEP 처리량/오류율/지연 관측
- `logs`: 실행 오류 및 예외 로그 확인

## 5. 운영 절차

### 5.1 규칙 신규 배포

1. Draft 규칙 생성
2. 테스트 이벤트로 `simulate`
3. 알림 채널 테스트
4. 활성화 토글
5. 초기 24시간 이벤트 품질 모니터링

### 5.2 장애 대응

1. `/cep-events`에서 실패 이벤트 확인
2. `/admin/logs`에서 오류 스택 확인
3. 채널 설정/외부 endpoint 상태 점검
4. 재시도 정책 조정
5. 필요 시 규칙 비활성화 후 수정 배포

## 6. API 요약

- `POST /cep/rules`
- `GET /cep/rules`
- `PUT /cep/rules/{rule_id}`
- `PATCH /cep/rules/{rule_id}/toggle`
- `POST /cep/rules/{rule_id}/simulate`
- `POST /cep/rules/{rule_id}/trigger`
- `GET /cep/events`
- `GET /cep/events/summary`

## 7. 체크리스트

- 트리거 조건이 과도하지 않은가
- 알림 폭주 방지 정책이 있는가
- 재시도/폴백 채널이 설정됐는가
- 테넌트 격리 조건이 유지되는가
- 시뮬레이션 결과가 기대와 일치하는가

## 8. 문제 해결

- 규칙은 동작하지만 알림이 오지 않음: 채널 credential/endpoint/timeout 점검
- 이벤트가 너무 많음: 임계값 상향, window/aggregation 적용
- false positive 많음: anomaly 설정값(threshold, alpha, multiplier) 조정
- UI에서 목록이 비어 있음: 시간 필터/tenant/header 확인

## 9. 개선/고도화 제안

- 알림 채널별 QoS 정책 분리
- 규칙별 rate limit 정책 표준화
- 이벤트 리플레이/백필 기능
- 운영용 대시보드(규칙 성능 순위, 실패 상위 규칙) 강화
