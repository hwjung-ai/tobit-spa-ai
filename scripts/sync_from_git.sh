#!/bin/bash
#
# sync_from_git.sh - Git에서 수정된 파일을 받아서 서버로 복사
# 사용법: ./scripts/sync_from_git.sh [서버주소] [서버_유저명] [원격_경로]
# 예시: ./scripts/sync_from_git.sh 115.21.12.151 /home/spa/deploy
#

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 파라미터 처리
SERVER_HOST="${1:-}"
SERVER_USER="${2:-}"
SERVER_PATH="${3:-}"

if [ -z "$SERVER_HOST" ] || [ -z "$SERVER_USER" ] || [ -z "$SERVER_PATH" ]; then
    echo -e "${RED}사용법: $0 <서버주소> <서버유저> <원격경로>${NC}"
    echo -e "${YELLOW}예시: $0 115.21.12.151 spa /home/spa/deploy${NC}"
    echo ""
    echo "로컬 테스트 모드로 실행합니다 (dry-run)..."
    DRY_RUN=true
    SERVER_HOST=""
    SERVER_USER=""
    SERVER_PATH="./test_deploy"
else
    DRY_RUN=false
    echo -e "${GREEN}서버: $SERVER_USER@$SERVER_HOST:$SERVER_PATH${NC}"
fi

# 프로젝트 루트 디렉토리
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${BLUE}=== Git 변경사항 동기 스크립트 ===${NC}"
echo -e "${BLUE}프로젝트 루트: $PROJECT_ROOT${NC}"
echo ""

# 1. git에서 최신 변경사항 가져오기
echo -e "${YELLOW}[1/4] Git 변경사항 확인 중...${NC}"
git fetch origin || {
    echo -e "${RED}Git fetch 실패${NC}"
    exit 1
}

# 현재 브랜치 확인
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo -e "${BLUE}현재 브랜치: $CURRENT_BRANCH${NC}"

# 마지막 동기 이후 수정된 파일 목록 가져오기
# origin/$CURRENT_BRANCH와 비교하여 변경된 파일 목록
CHANGED_FILES=$(git diff --name-only origin/$CURRENT_BRANCH HEAD 2>/dev/null || git diff --name-only main~10 HEAD 2>/dev/null || echo "")

if [ -z "$CHANGED_FILES" ]; then
    echo -e "${YELLOW}변경된 파일이 없습니다.${NC}"
    exit 0
fi

# 파일 목록을 배열로 변환
FILE_ARRAY=()
while IFS= read -r file; do
    [ -n "$file" ] && FILE_ARRAY+=("$file")
done <<< "$CHANGED_FILES"

echo -e "${GREEN}총 ${#FILE_ARRAY[@]}개의 파일이 변경됨${NC}"

# 2. 대상 파일 필터링 (배포할 파일만)
echo ""
echo -e "${YELLOW}[2/4] 배포 대상 파일 필터링 중...${NC}"

DEPLOY_FILES=()
EXCLUDED_PATTERNS=(
    "node_modules/"
    ".next/"
    "__pycache__/"
    ".pytest_cache/"
    "*.pyc"
    ".env"
    "*.log"
    "tests-e2e/"
    "playwright-report/"
    "test-results/"
    ".venv/"
    "*.md"
    ".git/"
)

for file in "${FILE_ARRAY[@]}"; do
    # 제외 패턴 체크
    skip=false
    for pattern in "${EXCLUDED_PATTERNS[@]}"; do
        if [[ "$file" == *"$pattern"* ]] || [[ "$file" == "$pattern" ]]; then
            skip=true
            break
        fi
    done

    # 실제 파일 존재 확인
    if [ "$skip" = false ] && [ -f "$PROJECT_ROOT/$file" ]; then
        DEPLOY_FILES+=("$file")
    fi
done

echo -e "${GREEN}배포할 파일: ${#DEPLOY_FILES[@]}개${NC}"

if [ ${#DEPLOY_FILES[@]} -eq 0 ]; then
    echo -e "${YELLOW}배포할 파일이 없습니다.${NC}"
    exit 0
fi

# 3. 파일 목록 표시
echo ""
echo -e "${YELLOW}[3/4] 변경된 파일 목록:${NC}"
for file in "${DEPLOY_FILES[@]}"; do
    echo "  - $file"
done

# 4. 서버로 복사
echo ""
echo -e "${YELLOW}[4/4] 서버로 파일 복사...${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}[DRY-RUN] 실제로는 복사하지 않습니다.${NC}"
    for file in "${DEPLOY_FILES[@]}"; do
        echo "  Would copy: $file → $SERVER_PATH/$file"
    done
else
    # 임시 디렉토리에 파일 구조 복사
    TEMP_DIR=$(mktemp -d)
    echo -e "${BLUE}임시 디렉토리: $TEMP_DIR${NC}"

    for file in "${DEPLOY_FILES[@]}"; do
        src_file="$PROJECT_ROOT/$file"
        dst_file="$TEMP_DIR/$file"
        dst_dir=$(dirname "$dst_file")

        mkdir -p "$dst_dir"
        cp "$src_file" "$dst_file"
        echo -e "${GREEN}✓ $file${NC}"
    done

    # rsync로 서버에 전송
    echo ""
    echo -e "${BLUE}서버로 전송 중...${NC}"

    rsync -avz --delete \
        -e "ssh -o StrictHostKeyChecking=no" \
        "$TEMP_DIR/" \
        "$SERVER_USER@$SERVER_HOST:$SERVER_PATH/" || {
        echo -e "${RED}Rsync 전송 실패${NC}"
        rm -rf "$TEMP_DIR"
        exit 1
    }

    # 임시 디렉토리 정리
    rm -rf "$TEMP_DIR"

    echo ""
    echo -e "${GREEN}=== 동기 완료 ===${NC}"
    echo -e "${YELLOW}서버에서 재시작이 필요할 수 있습니다:${NC}"
    echo -e "${BLUE}  ssh $SERVER_USER@$SERVER_HOST 'cd $SERVER_PATH && npm run dev'${NC}"
fi

exit 0
