"""
LIMRA 수동 로그인 스크립트
최초 1회만 실행하여 세션을 저장합니다.
"""

import asyncio
from limra_search_agent import LimraSearchAgent

async def main():
    print("=" * 60)
    print("LIMRA 수동 로그인 도구")
    print("=" * 60)
    print("\n이 스크립트는 최초 1회만 실행하면 됩니다.")
    print("로그인 완료 후 세션이 저장되어, 다음번부터는 자동 로그인됩니다.\n")

    # 에이전트 초기화
    agent = LimraSearchAgent(
        email="plopa1535@kyobo.com",
        password="Kyobo1234!@#$",
        download_folder="./limra_downloads",
        headless=False  # 브라우저 표시
    )

    # 브라우저 초기화
    await agent.initialize()

    # 수동 로그인 모드 실행
    success = await agent.manual_login_once()

    if success:
        print("\n✅ 성공! 이제 웹 UI에서 CAPTCHA 없이 자동 로그인됩니다.")
    else:
        print("\n❌ 로그인에 실패했습니다. 다시 시도해주세요.")

    # 브라우저 종료
    await agent.close()

if __name__ == "__main__":
    asyncio.run(main())
