# 📊 20개 테스트 케이스 실행 결과

**실행일시**: 2026-01-31 15:54:57
**API**: /ops/ci/ask
**결과**: ❌ 0/20 (통과율: 0.0%)

---

## Test 1

**질의**: What is the current system status? Tell me the total number of CIs.

**예상 답변에 포함할 단어**: `280`

**Trace ID**: b5ea83a4-3590-41f5-847a-bf1970c6b6c5

**응답 시간**: 10.71s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 2

**질의**: What is the most common CI type in the system?

**예상 답변에 포함할 단어**: `SW`

**Trace ID**: 3cd5bad4-548e-4b86-80ad-6c7c1684a3d2

**응답 시간**: 0.65s

**LLM 답변**:
```
Found 10 results
```

**결과**: FAIL

---

## Test 3

**질의**: How many events are recorded in the system?

**예상 답변에 포함할 단어**: `31,243`

**Trace ID**: 3b8a9d99-8ce3-429b-b8a3-248e34c55b79

**응답 시간**: 5.92s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 4

**질의**: What is the most common event type?

**예상 답변에 포함할 단어**: `threshold_alarm`

**Trace ID**: 5654ab17-a462-42f4-8416-05358fa03858

**응답 시간**: 6.29s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 5

**질의**: How many events occurred in the last 24 hours?

**예상 답변에 포함할 단어**: `0`

**Trace ID**: 9cf980b0-44d0-4f71-b3f4-d1cac7819688

**응답 시간**: 5.61s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 6

**질의**: How many metrics are defined in the system?

**예상 답변에 포함할 단어**: `120`

**Trace ID**: 5aff6975-d06a-4172-97fa-901e12fb9e10

**응답 시간**: 6.44s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 7

**질의**: How many metric data points are recorded?

**예상 답변에 포함할 단어**: `10,800,000`

**Trace ID**: 737f73e1-7188-4169-83bf-bf43ea56f51b

**응답 시간**: 7.34s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 8

**질의**: How many CIs are currently in active status?

**예상 답변에 포함할 단어**: `259`

**Trace ID**: 24f06581-ff8a-4472-9c0d-d7aecd82b6ef

**응답 시간**: 5.11s

**LLM 답변**:
```
Found 10 results
```

**결과**: FAIL

---

## Test 9

**질의**: How many software and hardware CIs do we have?

**예상 답변에 포함할 단어**: `272`

**Trace ID**: 07c9f674-5e5b-4a0d-8a2f-32a5744970ed

**응답 시간**: 10.21s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 10

**질의**: How many audit log entries are there?

**예상 답변에 포함할 단어**: `667`

**Trace ID**: ed4f823e-88fb-43d3-8775-14339d61f20d

**응답 시간**: 7.18s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 11

**질의**: How many system-type CIs exist?

**예상 답변에 포함할 단어**: `8`

**Trace ID**: 9b64358f-7bbe-4af5-97ad-c8d4099a85c0

**응답 시간**: 0.62s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 12

**질의**: How many events occurred today?

**예상 답변에 포함할 단어**: `0`

**Trace ID**: 30c631bf-eb07-4504-ab5b-8fed8a3dfd83

**응답 시간**: 6.93s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 13

**질의**: How many metric values were recorded today?

**예상 답변에 포함할 단어**: `360,000`

**Trace ID**: f1ff429a-fae2-48d6-8f23-50cebf7c7461

**응답 시간**: 4.75s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 14

**질의**: What was the most recent event type?

**예상 답변에 포함할 단어**: `threshold_alarm`

**Trace ID**: 9f831d58-1454-4b77-afcf-4b669a5bc6ee

**응답 시간**: 0.49s

**LLM 답변**:
```
Error during execution: 'str' object has no attribute 'value'
```

**결과**: FAIL

---

## Test 15

**질의**: How many threshold alarms have occurred?

**예상 답변에 포함할 단어**: `6,291`

**Trace ID**: 8bb3e8d5-d451-4e6c-828a-d4f2184c379d

**응답 시간**: 5.63s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 16

**질의**: How many security alerts have been raised?

**예상 답변에 포함할 단어**: `6,286`

**Trace ID**: 7db70e1d-c134-43c2-9407-cdad6d659137

**응답 시간**: 5.78s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 17

**질의**: How many health check events are there?

**예상 답변에 포함할 단어**: `6,267`

**Trace ID**: 1e0b0035-d0f9-4b15-8c74-83923c731252

**응답 시간**: 6.87s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 18

**질의**: How many status change events have occurred?

**예상 답변에 포함할 단어**: `6,225`

**Trace ID**: 5605ecf0-111c-416c-8caa-3329fd67b824

**응답 시간**: 7.84s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 19

**질의**: How many deployment events have been recorded?

**예상 답변에 포함할 단어**: `6,174`

**Trace ID**: 3665dcc3-7701-4e6d-83a9-15bddf766c9a

**응답 시간**: 4.42s

**LLM 답변**:
```
Found 1 results
```

**결과**: FAIL

---

## Test 20

**질의**: How many distinct CI names are there in the system?

**예상 답변에 포함할 단어**: `280`

**Trace ID**: 5c3034a1-40f1-43a6-85cd-3eaf191b5b41

**응답 시간**: 8.2s

**LLM 답변**:
```
Found 10 results
```

**결과**: FAIL

---

