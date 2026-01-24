# 긴급 디버깅 가이드 - Save Draft 404 오류

## 현 상황 분석

테스트 환경에서는 Save Draft가 **완벽하게 작동**합니다:
1. ✅ PUT 요청 → 404 (asset이 없어서 정상)
2. ✅ POST 요청 → 200 (새 asset 생성 성공)
3. ✅ `saveDraft completed successfully`

하지만 사용자 환경에서는 여전히 오류가 발생한다고 보고했습니다.

## 🔍 정확한 오류 정보 수집 방법

### 1단계: 브라우저 개발자 도구 열기
```
F12 또는 Ctrl+Shift+I
```

### 2단계: Console 탭 열기
```
콘솔 탭 클릭 → 모든 메시지 표시하기
```

### 3단계: Save Draft 실행 후 정보 수집

**정확히 다음 정보를 캡처해주세요:**

```
1. Console의 모든 [API] 메시지:
   - "[API] Request failed:" 메시지의 전체 내용
   - status 코드
   - error 객체의 내용

2. Console의 모든 [EDITOR] 메시지:
   - 전체 메시지 출력

3. Network 탭의 PUT/POST 요청:
   - PUT 요청의 Response 탭 내용
   - POST 요청의 Response 탭 내용 (있으면)
```

### 4단계: 다음 명령을 콘솔에 복사해서 실행

```javascript
// 모든 API 관련 메시지를 텍스트로 출력
const logs = console.log.toString();
console.log("=== API DEBUG INFO ===");
console.log("If you see [API] Request failed, copy everything below this line");
```

그 다음 **F12 개발자 도구의 Console 탭에서 우클릭 → Save as...**로 저장

## 📊 예상 시나리오

### 시나리오 1: POST도 404로 실패
```
[EDITOR] Asset not found, creating new asset with POST
[API] Fetching: /asset-registry/assets with method: POST
[API] Request failed: {
  endpoint: /asset-registry/assets,
  method: POST,
  status: 404,
  ...
}
```
**이 경우:** POST 엔드포인트 자체를 찾지 못함 → 라우터 설정 문제

### 시나리오 2: POST가 다른 오류 (400, 500 등)
```
[API] Request failed: {
  endpoint: /asset-registry/assets,
  method: POST,
  status: 400 또는 500,
  error: {...}
}
```
**이 경우:** 요청 데이터 또는 백엔드 처리 문제

### 시나리오 3: POST 요청이 완료되지 않음
```
[EDITOR] Asset not found, creating new asset with POST
[EDITOR] POST error: {message: "..."}
```
**이 경우:** 네트워크 또는 타임아웃 문제

## 🚨 빠른 해결 방법 (꼭 시도해보세요)

### 방법 1: 완전한 서버 재시작
```bash
# API 서버 중지
fuser -k 8000/tcp

# 웹 서버 중지
fuser -k 3000/tcp

# 잠깐 대기
sleep 3

# API 서버 시작
cd /home/spa/tobit-spa-ai/apps/api
python -m uvicorn main:app --host 127.0.0.1 --port 8000 &

# 웹 서버 시작
cd /home/spa/tobit-spa-ai/apps/web
npm run dev &
```

### 방법 2: 브라우저 완전 초기화
1. **모든 브라우저 탭 닫기**
2. **브라우저 캐시 삭제** (Ctrl+Shift+Delete)
3. **브라우저 재시작**
4. **http://localhost:3000에서 새로 로그인**

### 방법 3: 특정 스크린이 아닌 다른 스크린으로 시도
```
- 목록에서 다른 스크린 선택해보기
- 같은 오류가 나는지 확인
```

## 📋 최종 보고

위의 정보들을 수집한 후 다음과 함께 보고해주세요:

1. **정확한 오류 메시지 (콘솔 스크린샷 또는 텍스트)**
2. **Network 탭의 PUT/POST 요청 정보**
3. **API 서버 로그** (`tail -50 /tmp/api_server.log`)
4. **웹 서버 로그** (`tail -50 /tmp/web_server.log`)

이 정보가 있으면 정확한 원인을 파악할 수 있습니다!
