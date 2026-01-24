import os
import sys

# apps/api 경로를 path에 추가하여 모듈 import 가능하게 함
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path

from dotenv import load_dotenv
from redis import Redis
from rq import Queue, Worker

# .env 파일 로드
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[*] Loaded .env from {env_path}")
else:
    print(f"[!] Warning: .env not found at {env_path}")

REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    print("[!] Error: REDIS_URL is not set in .env", file=sys.stderr)
    sys.exit(1)


def run():
    print("[*] Starting RQ Worker for queues: documents")
    print(f"[*] Redis URL: {REDIS_URL}")

    try:
        # 워커 클래스 임포트 경로 문제 해결을 위해 sys.path 확인
        # 필요하다면 Worker 실행 시 import 가능한지 확인
        redis_conn = Redis.from_url(REDIS_URL)
        # 듣고 싶은 큐 이름들 - explicit connection passing
        qs = [Queue("documents", connection=redis_conn)]
        w = Worker(qs, connection=redis_conn)
        w.work()
    except Exception as e:
        print(f"[!] Error starting worker: {e}", file=sys.stderr)


if __name__ == "__main__":
    run()
