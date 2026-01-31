#!/bin/bash

# Test API call to /ops/ci/ask endpoint
curl -X POST http://localhost:8000/ops/ci/ask \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: default" \
  -H "X-User-Id: test_user" \
  -d '{
    "question": "전체기간중 cpu 사용률이 가장 높은 ci를 찾아서 ci의 구성정보를 알려주고, 최근 작업이력을 알려줘"
  }' 2>&1 | jq -r '.data.trace_id // .trace_id // "NO_TRACE_ID"'
