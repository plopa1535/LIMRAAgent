"""
LIMRA 간편 수동 로그인 스크립트
최초 1회만 실행하여 세션을 저장합니다.
"""

import asyncio
from playwright.async_api import async_playwright
import json
from pathlib import Path

async def manual_login_once():
    """최초 1회만 수동 로그인하여 세션 저장"""

    SESSION_FILE = Path('./limra_downloads/limra_session.json')
    LOGIN_URL = 'https://www.limra.com/en/log-in/'

    print("=" * 60)
    print("LIMRA 간편 수동 로그인")
    print("=" * 60)
    print("\n이 스크립트는 최초 1회만 실행하면 됩니다.")
    print("로그인 완료 후 세션이 저장되어, 다음번부터는 자동 로그인됩니다.\n")

    async with async_playwright() as p:
        # 브라우저 실행 (사용자가 볼 수 있도록 headless=False)
        print("[1/4] 브라우저를 실행합니다...")
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # 로그인 페이지로 이동
        print(f"[2/4] 로그인 페이지로 이동: {LOGIN_URL}")
        await page.goto(LOGIN_URL)

        print("\n" + "=" * 60)
        print("[LOGIN] 브라우저가 열렸습니다!")
        print("=" * 60)
        print("\n다음 작업을 수행해주세요:")
        print("  1. 이메일과 비밀번호 입력")
        print("  2. CAPTCHA 해결 (reCAPTCHA 체크)")
        print("  3. 로그인 버튼 클릭")
        print("  4. 메인 페이지가 완전히 로드될 때까지 대기")
        print("\n[WAIT] 5분(300초) 동안 대기합니다...")
        print("       충분한 시간을 드리니 천천히 로그인해주세요.")
        print("=" * 60 + "\n")

        # 사용자가 수동으로 로그인할 시간 제공 (5분)
        await page.wait_for_timeout(300000)

        # 로그인 확인
        current_url = page.url
        print(f"\n[3/4] 현재 URL: {current_url}")

        # 로그인 성공 여부 확인 (로그인 페이지가 아니면 성공)
        if 'login' not in current_url.lower() and 'log-in' not in current_url.lower():
            print("[OK] 로그인이 완료되었습니다!")
        else:
            print("\n[WARN] 아직 로그인 페이지에 있습니다.")
            print("       그래도 세션을 저장합니다. 로그인이 완료되었다면 괜찮습니다.")

        # 세션 상태 저장
        print("[4/4] 세션을 저장하는 중...")
        storage_state = await context.storage_state()

        # 저장 경로 확인
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(storage_state, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] 세션이 저장되었습니다!")
        print(f"     파일: {SESSION_FILE.absolute()}")
        print("\n이제 웹 UI에서 CAPTCHA 없이 자동 로그인됩니다!\n")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(manual_login_once())
