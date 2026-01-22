"""
LIMRA 자동 로그인 및 Agent 검색/다운로드
- 저장된 세션 사용 시도
- 세션 없거나 만료시 수동 로그인 대기
- 기존 LimraSearchAgent의 검색 기능 활용
- Agent 키워드로 Research 검색
- 결과 문서 다운로드
"""

import asyncio
import sys
import io
import json
from pathlib import Path

# Windows 콘솔 인코딩
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from limra_search_agent import LimraSearchAgent


async def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("LIMRA Auto Agent - Agent 키워드 검색 및 다운로드")
    print("=" * 60)
    print("\n[!] CAPTCHA가 나타나면 직접 체크박스를 클릭해주세요!")
    print("[!] 로그인 완료 후 자동으로 검색이 진행됩니다.\n")

    # 에이전트 생성 (기존 LimraSearchAgent 사용)
    agent = LimraSearchAgent(
        email="plopa1535@kyobo.com",
        password="Kyobo1234!@#$",
        download_folder="./limra_downloads",
        headless=False  # 브라우저 표시 (CAPTCHA 대응)
    )

    try:
        # 1. 브라우저 초기화
        print("[1/5] 브라우저 초기화...")
        await agent.initialize()

        # 2. 로그인 (세션 자동 로드 시도)
        print("\n[2/5] 로그인 시도...")
        login_success = await agent.login()

        if not login_success:
            print("\n[ERROR] 로그인 실패!")
            print("브라우저에서 수동으로 로그인해주세요.")
            print("CAPTCHA 체크박스를 클릭하고 로그인을 완료하세요.")
            print("\n로그인 완료 대기 중... (최대 3분)")

            # 수동 로그인 대기
            for i in range(180):
                await asyncio.sleep(1)

                # 로그인 성공 여부 확인
                content = await agent.page.content()
                content_lower = content.lower()
                current_url = agent.page.url

                if 'logout' in content_lower or 'sign out' in content_lower:
                    print(f"\n[OK] 로그인 성공 감지!")
                    agent.is_logged_in = True
                    # 세션 저장
                    await agent.save_session()
                    break

                if i % 15 == 0 and i > 0:
                    print(f"  ... {i}초 경과")
            else:
                print("\n[ERROR] 로그인 타임아웃")
                return

        print("[OK] 로그인 성공!")

        # 3. Agent 키워드로 검색
        print("\n[3/5] 'Agent' 키워드로 검색 중...")

        # 방법 1: search_documents 사용
        search_results = await agent.search_documents(query="Agent", max_results=30)

        # 방법 2: browse_research_with_filter 사용 (더 많은 결과)
        if len(search_results) < 5:
            print("\n[3/5] Research 섹션 추가 탐색...")
            browse_results = await agent.browse_research_with_filter(
                keywords=["Agent", "agent", "Insurance Agent", "Distribution"],
                auto_download=False
            )

            # 결과 병합 (중복 제거)
            seen_urls = {r['url'] for r in search_results}
            for doc in browse_results:
                if doc.get('url') and doc['url'] not in seen_urls:
                    search_results.append(doc)
                    seen_urls.add(doc['url'])

        print(f"\n[결과] 총 {len(search_results)}개 문서 발견")

        if search_results:
            # 상위 10개 출력
            print("\n발견된 문서:")
            for i, doc in enumerate(search_results[:10], 1):
                title = doc.get('title', 'N/A')[:60]
                print(f"  {i}. {title}...")

            # 4. 다운로드
            print(f"\n[4/5] {min(len(search_results), 20)}개 문서 다운로드 중...")
            agent.search_results = search_results[:20]  # 최대 20개
            downloaded = await agent.download_all_results()

            print(f"\n[5/5] 완료!")
            print(f"  - 발견: {len(search_results)}개")
            print(f"  - 다운로드: {len(downloaded) if downloaded else 0}개")
            print(f"  - 저장 위치: {agent.download_folder}")

        else:
            print("\n[INFO] 검색 결과가 없습니다.")
            print("가능한 원인:")
            print("  1. 로그인이 제대로 되지 않았을 수 있습니다")
            print("  2. LIMRA 사이트 구조가 변경되었을 수 있습니다")
            print("  3. 'Agent' 키워드로 검색된 문서가 없을 수 있습니다")

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[정리] 브라우저 종료 중...")
        await agent.close()
        print("[완료] 종료됨")


if __name__ == "__main__":
    asyncio.run(main())
