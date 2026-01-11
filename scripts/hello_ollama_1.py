import requests
import json

# 1. 설정: Ollama API 주소 및 모델
url = "http://115.21.12.41:11434/api/chat"
model_name = "qwen3coder-30b-cline:latest"  # 로컬에 설치된 모델 이름

# 2. 전송할 데이터 (JSON Payload)
payload = {
    "model": model_name,
    "messages": [
        {
            "role": "user",
            "content": "Hello! I am ready to code."
        }
    ],
    "stream": False  # 중요: False로 설정하면 답변이 완성될 때까지 기다렸다가 한 번에 받습니다.
}

# 3. HTTP POST 요청 보내기
try:
    print(f"📡 {url} 로 요청 보내는 중...")
    
    response = requests.post(url, json=payload)
    
    # 4. 응답 확인 및 출력
    if response.status_code == 200:
        result = response.json()
        answer = result['message']['content']
        print("\n[답변]:", answer)
    else:
        print("Error:", response.status_code, response.text)

except requests.exceptions.ConnectionError:
    print("연결 실패: Ollama가 실행 중인지 확인해주세요. (http://localhost:11434)")