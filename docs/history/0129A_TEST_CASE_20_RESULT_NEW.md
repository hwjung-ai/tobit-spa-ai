# 📊 20개 테스트 케이스 실행 결과

**실행일시**: 2026-01-29 11:48:59
**API**: /ops/ask
**결과**: ❌ 2/20 (통과율: 10.0%)

---

## Test 1

**질의**: What is the current system status? Tell me the total number of CIs.

**예상 답변에 포함할 단어**: `280`

**Trace ID**: 00d2c7f8-977f-4568-9055-2e3d21ed1cc6

**응답 시간**: 9.62s

**LLM 답변**:
```
259
```

**결과**: FAIL

---

## Test 2

**질의**: What is the most common CI type in the system?

**예상 답변에 포함할 단어**: `SW`

**Trace ID**: 5429a296-4626-4822-bb5b-dd1bde3e3888

**응답 시간**: 1.41s

**LLM 답변**:
```
7b397dde-20cd-4bce-b317-3e468d9468e5
```

**결과**: FAIL

---

## Test 3

**질의**: How many events are recorded in the system?

**예상 답변에 포함할 단어**: `31,243`

**Trace ID**: 8c93d436-4f70-4e5c-a515-0fc5e5930556

**응답 시간**: 5.74s

**LLM 답변**:
```
31243
```

**결과**: PASS

---

## Test 4

**질의**: What is the most common event type?

**예상 답변에 포함할 단어**: `threshold_alarm`

**Trace ID**: 6d10afa6-0bc8-499e-8f69-9641647e1eca

**응답 시간**: 8.86s

**LLM 답변**:
```
31243
```

**결과**: FAIL

---

## Test 5

**질의**: How many events occurred in the last 24 hours?

**예상 답변에 포함할 단어**: `0`

**Trace ID**: 6d094602-1187-4c09-b8d0-6da3887da8d4

**응답 시간**: 5.72s

**LLM 답변**:
```
31243
```

**결과**: FAIL

---

## Test 6

**질의**: How many metrics are defined in the system?

**예상 답변에 포함할 단어**: `120`

**Trace ID**: 668d6296-3dd1-4263-a223-48943b2d9203

**응답 시간**: 9.22s

**LLM 답변**:
```
120
```

**결과**: PASS

---

## Test 7

**질의**: How many metric data points are recorded?

**예상 답변에 포함할 단어**: `10,800,000`

**Trace ID**: c54fa728-e45c-47bc-b520-0fd76130a997

**응답 시간**: 6.89s

**LLM 답변**:
```
120
```

**결과**: FAIL

---

## Test 8

**질의**: How many CIs are currently in active status?

**예상 답변에 포함할 단어**: `259`

**Trace ID**: bd84b3b9-1794-4251-b689-48679d3ab6c3

**응답 시간**: 12.03s

**LLM 답변**:
```
7b397dde-20cd-4bce-b317-3e468d9468e5
```

**결과**: FAIL

---

## Test 9

**질의**: How many software and hardware CIs do we have?

**예상 답변에 포함할 단어**: `272`

**Trace ID**: dee2fec0-4533-40d0-9daa-30968a2ae259

**응답 시간**: 9.24s

**LLM 답변**:
```
259
```

**결과**: FAIL

---

## Test 10

**질의**: How many audit log entries are there?

**예상 답변에 포함할 단어**: `667`

**Trace ID**: 2133c528-10d2-4e3f-a843-c1fd9967136f

**응답 시간**: 5.31s

**LLM 답변**:
```
259
```

**결과**: FAIL

---

## Test 11

**질의**: How many system-type CIs exist?

**예상 답변에 포함할 단어**: `8`

**Trace ID**: 6069db71-19a9-4d78-9112-d1fd99e8b3a6

**응답 시간**: 1.45s

**LLM 답변**:
```
259
```

**결과**: FAIL

---

## Test 12

**질의**: How many events occurred today?

**예상 답변에 포함할 단어**: `0`

**Trace ID**: c360a6b6-ef51-4e94-8378-5a7b6b069749

**응답 시간**: 5.67s

**LLM 답변**:
```
31243
```

**결과**: FAIL

---

## Test 13

**질의**: How many metric values were recorded today?

**예상 답변에 포함할 단어**: `360,000`

**Trace ID**: 337b77c2-5f9f-48c7-befd-7d42a16cbfd2

**응답 시간**: 9.64s

**LLM 답변**:
```
120
```

**결과**: FAIL

---

## Test 14

**질의**: What was the most recent event type?

**예상 답변에 포함할 단어**: `threshold_alarm`

**Trace ID**: 22a929e2-008d-434c-841e-5c0113cdd8a7

**응답 시간**: 1.25s

**LLM 답변**:
```
Error during execution: 'str' object has no attribute 'value'
```

**결과**: FAIL

---

## Test 15

**질의**: How many threshold alarms have occurred?

**예상 답변에 포함할 단어**: `6,291`

**Trace ID**: c05b1aee-4667-44f6-91c8-3498e8fc189f

**응답 시간**: 6.65s

**LLM 답변**:
```
259
```

**결과**: FAIL

---

## Test 16

**질의**: How many security alerts have been raised?

**예상 답변에 포함할 단어**: `6,286`

**Trace ID**: 1dbb19ec-e952-43dd-8abf-cab9344f7b9c

**응답 시간**: 5.21s

**LLM 답변**:
```
259
```

**결과**: FAIL

---

## Test 17

**질의**: How many health check events are there?

**예상 답변에 포함할 단어**: `6,267`

**Trace ID**: 3a677ca3-2a7a-42b3-a6ae-e064a6e8080b

**응답 시간**: 5.78s

**LLM 답변**:
```
31243
```

**결과**: FAIL

---

## Test 18

**질의**: How many status change events have occurred?

**예상 답변에 포함할 단어**: `6,225`

**Trace ID**: 18658084-4e8c-4cd5-b5a7-a77e0b189442

**응답 시간**: 7.03s

**LLM 답변**:
```
31243
```

**결과**: FAIL

---

## Test 19

**질의**: How many deployment events have been recorded?

**예상 답변에 포함할 단어**: `6,174`

**Trace ID**: 5b98b983-86bd-49fd-8871-ef8f3a3e8486

**응답 시간**: 8.79s

**LLM 답변**:
```
31243
```

**결과**: FAIL

---

## Test 20

**질의**: How many distinct CI names are there in the system?

**예상 답변에 포함할 단어**: `280`

**Trace ID**: 9e63345e-15c9-4515-8641-c568894ac626

**응답 시간**: 9.16s

**LLM 답변**:
```
7b397dde-20cd-4bce-b317-3e468d9468e5
```

**결과**: FAIL

---

