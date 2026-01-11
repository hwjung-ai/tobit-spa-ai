import schedule
import time
import subprocess
import sys
from datetime import datetime

# 실행할 스크립트 경로 (절대 경로로 지정)
SCRIPT_PATH = r"d:\tobit-spa-ai\scripts\bizplay_attendance.py"

def run_attendance(mode):
    """
    bizplay_attendance.py를 실행하는 함수
    mode: 'in' (출근) 또는 'out' (퇴근)
    """
    now = datetime.now()
    weekdays_kr = ["월", "화", "수", "목", "금", "토", "일"]
    day_str = weekdays_kr[now.weekday()]
    date_str = now.strftime("%Y-%m-%d")
    
    # 월(0) ~ 금(4) 인지 확인
    if now.weekday() > 4:
        print(f"[{date_str}({day_str})] 주말입니다. 작업을 건너뜁니다.")
        return

    mode_kor = "출근" if mode == "in" else "퇴근"
    print(f"[{date_str}({day_str})] {mode_kor} 체크 작업을 시작합니다...")
    try:
        # 현재 실행중인 파이썬 인터프리터를 사용하여 스크립트 실행
        # --sim 옵션을 제거하여 '실제'로 수행되도록 합니다.
        # 테스트를 원하시면 아래 리스트에 "--sim"을 추가하세요.
        cmd = [sys.executable, SCRIPT_PATH, mode]
        
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        print("="*30)
        print("실행 결과:")
        print(result.stdout)
        if result.stderr:
            print("오류 내용:")
            print(result.stderr)
        print("="*30)
        
    except Exception as e:
        print(f"작업 실행 중 오류 발생: {e}")

def job_in():
    run_attendance("in")

def job_out():
    run_attendance("out")

# 스케줄 설정
# 월요일부터 금요일까지 매일 지정된 시간에 실행
# 주말 체크 로직은 run_attendance 함수 내부에 있습니다.
TARGET_TIME_IN = "08:50"
TARGET_TIME_OUT = "18:10"

print(f"=== 비즈플레이 자동 출퇴근 스케줄러 시작 ===")
print(f"출근 설정 시간: {TARGET_TIME_IN}")
print(f"퇴근 설정 시간: {TARGET_TIME_OUT}")
print(f"대상 스크립트: {SCRIPT_PATH}")
print("Ctrl+C를 누르면 종료됩니다.")

schedule.every().day.at(TARGET_TIME_IN).do(job_in)
schedule.every().day.at(TARGET_TIME_OUT).do(job_out)

while True:
    # 10초마다 스케줄 확인
    schedule.run_pending()
    time.sleep(10)
