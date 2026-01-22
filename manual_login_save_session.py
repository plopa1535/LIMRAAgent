"""
LIMRA 수동 로그인 및 세션 저장
- 브라우저를 열고 수동으로 로그인
- 로그인 완료 후 세션을 저장
"""

from playwright.sync_api import sync_playwright
import json
import os
import sys
import io

# Windows 콘솔 인코딩
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class LIMRASessionManager:
    def __init__(self):
        self.session_file = './limra_downloads/limra_session.json'
        self.base_url = 'https://www.limra.com'

        # 폴더 생성
        os.makedirs('./limra_downloads', exist_ok=True)

    def manual_login_once(self):
        """최초 1회만 수동 로그인하여 세션 저장"""
        print("=" * 60)
        print("LIMRA 수동 로그인 및 세션 저장")
        print("=" * 60)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()

            # 로그인 페이지로 이동
            print("\n[1] 로그인 페이지로 이동 중...")
            page.goto(f'{self.base_url}/login')

            print("\n" + "!" * 60)
            print("브라우저가 열렸습니다!")
            print("")
            print("  1. 이메일을 입력하세요")
            print("  2. CAPTCHA 체크박스를 클릭하세요")
            print("  3. 'Next' 버튼을 클릭하세요")
            print("  4. 비밀번호를 입력하고 로그인하세요")
            print("")
            print("로그인이 완료될 때까지 대기합니다 (최대 3분)...")
            print("!" * 60 + "\n")

            # 로그인 완료 감지 (최대 3분 대기)
            max_wait = 180  # 3분
            for i in range(max_wait):
                page.wait_for_timeout(1000)  # 1초 대기

                current_url = page.url
                content = page.content().lower()

                # 로그인 성공 판별
                if 'limra.com' in current_url and 'login' not in current_url.lower():
                    print(f"\n[OK] 로그인 성공 감지! URL: {current_url[:50]}...")
                    break

                # 로그아웃 버튼이 있으면 로그인 성공
                if 'logout' in content or 'sign out' in content:
                    print(f"\n[OK] 로그인 성공 감지! (로그아웃 버튼 발견)")
                    break

                if i % 10 == 0 and i > 0:
                    print(f"  ... {i}초 경과, 로그인을 완료해주세요")
            else:
                print("\n[WARN] 3분 타임아웃. 현재 상태로 세션을 저장합니다.")

            # 로그인 완료 확인
            print("[2] 로그인 상태 확인 중...")
            current_url = page.url
            print(f"    현재 URL: {current_url}")

            # 세션 저장
            print("\n[3] 세션 저장 중...")
            storage_state = context.storage_state()

            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(storage_state, f, indent=2)

            print(f"    세션 파일: {self.session_file}")
            print("\n[OK] 세션이 저장되었습니다!")

            browser.close()

        print("\n이제 run_search_agent.py를 실행하면 저장된 세션으로 자동 로그인됩니다.")


def main():
    manager = LIMRASessionManager()
    manager.manual_login_once()


if __name__ == "__main__":
    main()
