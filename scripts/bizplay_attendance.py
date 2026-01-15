import sys
import time
from playwright.sync_api import sync_playwright
from datetime import datetime

# 기존 print 함수를 덮어씌워 자동으로 시간 로그를 남기도록 설정
_original_print = print

def print(*args, **kwargs):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    _original_print(timestamp, *args, **kwargs)

def run(mode, is_simulation):
    with sync_playwright() as p:
        # 브라우저 실행 (headless=False로 하면 실제 브라우저가 뜨는 것을 볼 수 있습니다)
        browser = p.chromium.launch(headless=False) 
        context = browser.new_context()
        page = context.new_page()

        try:
            print("비즈플레이 로그인 페이지 접속 중...")
            page.goto("https://www.bizplay.co.kr/login_0001_01.act")

            # 로그인 정보 입력
            page.fill("#USER_ID", "likesea7")
            page.fill("#PWD", "hi0910!12")
            
            print("로그인 시도 중...")
            page.click("#btnLogin")
            
            # 로그인 후 메인 대시보드 대기
            page.wait_for_load_state("networkidle")
            
            # 'MY인사' 앱 클릭 (새 탭으로 열림)
            print("'MY인사' 앱 진입 중...")
            with context.expect_page() as new_page_info:
                # 6번째 app_img 아이콘이 MY인사임 (인덱스 5)
                page.locator(".app_img").nth(5).click()
            
            hr_page = new_page_info.value
            hr_page.wait_for_load_state("networkidle")
            
            # '출퇴근시간관리' 메뉴 클릭
            print("'출퇴근시간관리' 메뉴로 이동 중...")
            hr_page.get_by_role("link", name="출퇴근시간관리").click()
            
            # iframe 내의 버튼을 찾기 위해 iframe_locator 사용
            hr_page.wait_for_timeout(3000)
            iframe = hr_page.frame_locator("#ifr_content")
            
            target_btn_id = "#btnWorkIn" if mode == "in" else "#btnWorkOut"
            mode_name = "출근" if mode == "in" else "퇴근"
            
            print(f"{mode_name} 체크 시도 중...")
            btn = iframe.locator(target_btn_id)
            
            if btn.is_visible():
                btn.click()
                print(f"{mode_name} 버튼을 클릭했습니다. 팝업 대기 중...")
                
                # 팝업이 뜰 때까지 충분히 대기 (3초)
                hr_page.wait_for_timeout(3000)
                
                # 팝업이 뜰 때까지 충분히 대기 (3초)
                hr_page.wait_for_timeout(3000)
                
                print("팝업 iframe(#dialog_iframe) 탐색 중...")
                
                target_frame = None
                
                # 1. 메인 페이지(hr_page) 바로 아래에 dialog_iframe이 있는지 확인
                if hr_page.locator("#dialog_iframe").count() > 0:
                    print("메인 페이지에서 팝업(#dialog_iframe) 발견.")
                    target_frame = hr_page.frame_locator("#dialog_iframe")
                
                # 2. 없다면 #ifr_content 안에 dialog_iframe이 있는지 확인
                elif iframe.locator("#dialog_iframe").count() > 0:
                    print("#ifr_content 내부에서 팝업(#dialog_iframe) 발견.")
                    target_frame = iframe.frame_locator("#dialog_iframe")
                
                if target_frame:
                    if is_simulation:
                        print("시뮬레이션 모드: '아니오' 버튼(#cancelBtn) 클릭...")
                        # 스크린샷: <span id="cancelBtn"><a>아니오</a></span>
                        # 클릭 가능한 요소가 a 태그일 수도 있고 span일 수도 있으니 안전하게 내부 텍스트나 span을 타겟팅
                        btn = target_frame.locator("#cancelBtn")
                        if btn.is_visible():
                            btn.click()
                            print("시뮬레이션 완료 ('아니오' 클릭 성공).")
                        else:
                            print("오류: #cancelBtn이 보이지 않습니다.")
                    else:
                        print("실제 모드: '예' 버튼(.confirmBtn) 클릭...")
                        # Strict mode 오류 방지: .confirmBtn 클래스가 여러 개일 수 있으므로 "예" 텍스트로 필터링
                        btn = target_frame.locator(".confirmBtn").filter(has_text="예")
                        if btn.count() > 0 and btn.is_visible():
                            btn.click()
                            print(f"{mode_name} 체크 완료 ('예' 클릭 성공).")
                        else:
                            print("오류: .confirmBtn('예')이 보이지 않습니다.")
                else:
                    print("오류: 팝업 iframe(#dialog_iframe)을 찾을 수 없습니다.")
            else:
                print(f"{mode_name} 버튼이 화면에 보이지 않습니다. (이미 체크되었거나 다른 이유일 수 있습니다)")
            
            # 결과 확인을 위해 잠시 대기
            hr_page.wait_for_timeout(3000)
            
        except Exception as e:
            print(f"오류가 발생했습니다: {e}")
        finally:
            print("브라우저를 종료합니다.")
            browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python bizplay_attendance.py [in|out] [--sim]")
        sys.exit(1)
    
    check_mode = sys.argv[1].lower()
    if check_mode not in ["in", "out"]:
        print("오류: 'in'(출근) 또는 'out'(퇴근)을 입력하세요.")
        sys.exit(1)
        
    # --sim 또는 -sim 모두 허용
    simulation = "--sim" in sys.argv or "-sim" in sys.argv
    run(check_mode, simulation)
