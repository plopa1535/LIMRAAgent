"""
Retention 키워드 검색 테스트
2024-2025 기간 필터링
"""

import asyncio
import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from limra_search_agent import LimraSearchAgent


async def main():
    print("=" * 60)
    print("Retention 키워드 검색 테스트 (2024-2025)")
    print("=" * 60)

    agent = LimraSearchAgent(
        email="plopa1535@kyobo.com",
        password="Kyobo1234!@#$",
        download_folder="./limra_downloads",
        headless=False
    )

    try:
        await agent.initialize()

        # 로그인
        print("\n[1] 로그인...")
        login_success = await agent.login()
        if not login_success:
            print("[ERROR] 로그인 실패")
            return

        print("[OK] 로그인 성공")

        # 방법 1: search_documents로 검색
        print("\n[2] search_documents로 'Retention' 검색...")
        results1 = await agent.search_documents(query="Retention", max_results=30)
        print(f"    결과: {len(results1)}개")

        if results1:
            print("\n    발견된 문서:")
            for i, doc in enumerate(results1[:5], 1):
                print(f"      {i}. {doc.get('title', 'N/A')[:50]}")

        # 방법 2: browse_research_with_filter로 검색 (연도 필터 포함)
        print("\n[3] browse_research_with_filter로 검색 (2024-2025)...")
        results2 = await agent.browse_research_with_filter(
            keywords=["Retention"],
            start_year=2024,
            end_year=2025,
            auto_download=False
        )
        print(f"    결과: {len(results2)}개")

        # 방법 3: 연도 필터 없이 키워드만
        print("\n[4] browse_research_with_filter (연도 필터 없이)...")
        results3 = await agent.browse_research_with_filter(
            keywords=["Retention"],
            auto_download=False
        )
        print(f"    결과: {len(results3)}개")

        # 총 결과
        print("\n" + "=" * 60)
        print("결과 요약:")
        print(f"  - search_documents: {len(results1)}개")
        print(f"  - browse (2024-2025): {len(results2)}개")
        print(f"  - browse (연도 필터 없음): {len(results3)}개")
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

    finally:
        await agent.close()
        print("\n[완료]")


if __name__ == "__main__":
    asyncio.run(main())
