"""
Agent 키워드로 LIMRA Research 검색 및 다운로드 실행 스크립트
"""

import asyncio
import sys
import io

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from limra_search_agent import LimraSearchAgent


async def manual_login_and_search():
    """수동 로그인 후 검색 진행"""
    print("=" * 60)
    print("LIMRA Research 검색 에이전트")
    print("키워드: Agent")
    print("=" * 60)
    print("\n[!] CAPTCHA가 나타나면 직접 체크박스를 클릭해주세요!")
    print("[!] 로그인 완료 후 자동으로 검색이 진행됩니다.\n")

    # 에이전트 생성
    agent = LimraSearchAgent(
        email="plopa1535@kyobo.com",
        password="Kyobo1234!@#$",
        download_folder="./limra_downloads",
        headless=False  # 브라우저 표시
    )

    try:
        # 1. 브라우저 초기화
        print("\n[1/4] 브라우저 초기화...")
        await agent.initialize()

        # 2. 로그인
        print("\n[2/4] 로그인 중...")
        login_success = await agent.login()

        if not login_success:
            print("[ERROR] 로그인 실패!")
            return

        print("[OK] 로그인 성공!")

        # 3. Agent 키워드로 검색
        print("\n[3/4] 'Agent' 키워드로 Research 검색 중...")
        results = await agent.browse_research_with_filter(
            keywords=["Agent"],
            auto_download=False
        )

        print(f"\n[결과] {len(results)}개 문서 발견")

        if results:
            # 상위 5개 출력
            print("\n발견된 문서 (상위 5개):")
            for i, doc in enumerate(results[:5], 1):
                title = doc.get('title', 'N/A')[:50]
                print(f"  {i}. {title}...")

            # 4. 다운로드
            print(f"\n[4/4] {len(results)}개 문서 다운로드 중...")
            agent.search_results = results
            downloaded = await agent.download_all_results()

            print(f"\n[완료] {len(downloaded) if downloaded else 0}개 파일 다운로드 완료!")
        else:
            print("[INFO] 검색 결과가 없습니다.")

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 브라우저 종료
        print("\n[정리] 브라우저 종료 중...")
        await agent.close()
        print("[완료] 종료됨")


async def main():
    """메인 함수 - 저장된 세션으로 시도 후 없으면 수동 로그인"""
    await manual_login_and_search()


if __name__ == "__main__":
    asyncio.run(main())
