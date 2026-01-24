# Save Draft 오류 디버깅 가이드

## 📋 문제 상황
Admin > Screen 탭에서 컴포넌트를 선택하고 Properties에서 이름을 변경한 후 Save Draft를 누르면 404 오류가 발생합니다.

## 🔍 디버깅 단계

### 1단계: 브라우저 캐시 완전 삭제
```
- Chrome/Edge: Ctrl+Shift+Delete (Windows) 또는 Cmd+Shift+Delete (Mac)
- Firefox: Ctrl+Shift+Delete (Windows) 또는 Cmd+Shift+Delete (Mac)
- Safari: Preferences > Privacy > Manage Website Data
```

### 2단계: 브라우저 개발자 도구 열기
```
F12 또는 Ctrl+Shift+I (Windows)
Cmd+Option+I (Mac)
```

### 3단계: Network 탭에서 요청 모니터링
1. **Network 탭** 클릭
2. **Filter** 입력 필드에 "asset" 입력 (asset 관련 요청만 표시)
3. Save Draft 버튼 클릭

### 4단계: PUT 요청 확인
다음을 체크하세요:

**요청 정보:**
- URL: `http://localhost:8000/asset-registry/assets/{screen_id}`
- Method: **PUT**
- Status: **404** (또는 다른 상태)

**요청 헤더:**
```
Authorization: Bearer {token}
Content-Type: application/json
```

**요청 본문:**
```json
{
  "schema_json": { ... screen data ... }
}
```

**응답 본문:**
```json
{"detail":"asset not found"}
```

### 5단계: 콘솔 확인
**Console 탭**에서 다음을 찾으세요:

```
[API] Request failed: {
  endpoint: /asset-registry/assets/...,
  method: PUT,
  status: 404,
  statusText: Not Found,
  error: {...},
  rawResponse: "..."
}
```

**특히 주목:**
- `status` 코드
- `error` 객체의 내용
- `rawResponse` 메시지

### 6단계: 결과 보고

다음 정보를 제공해주세요:

1. **Network 탭의 PUT 요청:**
   - 전체 URL
   - 상태 코드
   - 응답 본문 (Response 탭에서 확인)

2. **Console 탭의 오류 메시지:**
   - 전체 에러 객체 출력
   - "[API]" 또는 "[EDITOR]" 태그가 있는 모든 로그

3. **API 서버 로그:**
   - `/tmp/api_server.log` 파일의 마지막 20줄

## 🛠️ 가능한 해결 방법

### 방법 1: 하드 새로고침
```
Ctrl+Shift+R (Windows)
Cmd+Shift+R (Mac)
```

### 방법 2: 새 탭에서 시도
```
1. 새 시크릿/개인 창 열기
2. 새 탭에서 http://localhost:3000 접속
3. 다시 로그인
4. 다시 시도
```

### 방법 3: API 서버 재시작
```bash
# API 서버 중지
fuser -k 8000/tcp

# API 서버 시작
cd /home/spa/tobit-spa-ai/apps/api
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 방법 4: 웹 서버 재시작
```bash
# 웹 서버 중지
fuser -k 3000/tcp

# 웹 서버 시작
cd /home/spa/tobit-spa-ai/apps/web
npm run dev
```

## 📊 예상되는 성공 흐름

1. **PUT 요청** → 404 (asset이 없음, 정상)
2. **POST 요청** → 200 (새 asset 생성)
3. **Console 메시지**: `[EDITOR] saveDraft completed successfully`

## ❓ 여전히 안 되면?

위의 디버깅 정보를 모두 수집한 후 다시 보고해주세요.
특히 Network 탭의 응답 내용이 중요합니다.
