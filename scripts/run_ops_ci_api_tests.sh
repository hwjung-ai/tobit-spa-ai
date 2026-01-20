#!/usr/bin/env bash
set -euo pipefail

# OPS CI API 테스트 실행 스크립트
# 기능:
#  1. 백엔드 서버 상태 확인 (또는 기동)
#  2. pytest 실행
#  3. 결과 리포트 생성

# 설정
BASE_URL="${OPS_BASE_URL:-http://localhost:8000}"
HEALTH_URL="${BASE_URL}/health"
MAX_HEALTH_RETRIES=10
HEALTH_RETRY_INTERVAL=2

echo "=========================================="
echo "OPS CI API Tests"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo "Health URL: $HEALTH_URL"
echo ""

# Step 1: 헬스체크 대기
echo "🏥 Waiting for backend to be healthy..."
retry_count=0
while [ $retry_count -lt $MAX_HEALTH_RETRIES ]; do
    if curl --fail --silent --show-error "$HEALTH_URL" > /dev/null 2>&1; then
        echo "✅ Backend is healthy"
        break
    fi
    retry_count=$((retry_count + 1))
    if [ $retry_count -lt $MAX_HEALTH_RETRIES ]; then
        echo "   Attempt $retry_count/$MAX_HEALTH_RETRIES - retrying in ${HEALTH_RETRY_INTERVAL}s..."
        sleep "$HEALTH_RETRY_INTERVAL"
    fi
done

if [ $retry_count -eq $MAX_HEALTH_RETRIES ]; then
    echo "❌ Backend health check failed after $MAX_HEALTH_RETRIES attempts"
    exit 1
fi

# Step 2: 아티팩트 디렉터리 생성
echo ""
echo "📁 Creating artifacts directory..."
mkdir -p artifacts/ops_ci_api_raw

# Step 3: pytest 실행
echo ""
echo "🧪 Running pytest..."
cd "$(dirname "$(readlink -f "$0")")/.."

# pytest 실행 (junit xml 포맷)
if python -m pytest \
    tests/ops_ci_api/test_ops_ci_ask_api.py \
    -v \
    --tb=short \
    --junit-xml=artifacts/junit.xml \
    --tb=short; then
    echo "✅ All tests passed"
else
    echo "⚠️  Some tests failed (see above)"
fi

echo ""
echo "=========================================="
echo "✅ Test execution complete"
echo "=========================================="
echo "Artifacts:"
echo "  - artifacts/junit.xml"
echo "  - artifacts/ops_ci_api_raw/*.json"
echo ""
