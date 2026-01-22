"""
웹앱 검색 API 직접 테스트
web_app.py의 /api/search 엔드포인트 로직 시뮬레이션
"""

import asyncio
import sys
import io
import re

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from limra_search_agent import LimraSearchAgent


def extract_year_from_doc(doc: dict) -> int:
    """문서에서 연도 추출 (URL, 제목, 설명에서)"""
    if doc.get('year'):
        return doc['year']

    url = doc.get('url', '')
    url_year_match = re.search(r'/(\d{4})/', url)
    if url_year_match:
        year = int(url_year_match.group(1))
        if 2000 <= year <= 2030:
            return year

    title = doc.get('title', '')
    title_year_match = re.search(r'\b(20\d{2})\b', title)
    if title_year_match:
        return int(title_year_match.group(1))

    desc = doc.get('description', '')
    desc_year_match = re.search(r'\b(20\d{2})\b', desc)
    if desc_year_match:
        return int(desc_year_match.group(1))

    return None


def filter_docs_by_year(docs: list, start_year: int = None, end_year: int = None) -> list:
    """문서 목록을 연도로 필터링"""
    if not start_year and not end_year:
        return docs

    filtered = []
    for doc in docs:
        year = extract_year_from_doc(doc)
        doc['year'] = year

        if year is None:
            filtered.append(doc)
            continue

        if start_year and year < start_year:
            continue
        if end_year and year > end_year:
            continue

        filtered.append(doc)

    return filtered


async def simulate_webapp_search(keywords, start_year, end_year):
    """웹앱 검색 로직 시뮬레이션"""
    print("=" * 60)
    print("웹앱 검색 API 시뮬레이션")
    print(f"키워드: {keywords}")
    print(f"연도: {start_year} ~ {end_year}")
    print("=" * 60)

    agent = LimraSearchAgent(
        email="plopa1535@kyobo.com",
        password="Kyobo1234!@#$",
        download_folder="./limra_downloads",
        headless=False
    )

    try:
        print("\n[1] 브라우저 초기화...")
        await agent.initialize()

        print("\n[2] 로그인 중...")
        login_success = await agent.login()
        if not login_success:
            print("[ERROR] 로그인 실패!")
            return

        print("[OK] 로그인 성공!")

        # 웹앱과 동일한 로직
        all_results = []
        seen_urls = set()

        # 1단계: LIMRA 검색 API 사용
        print("\n" + "=" * 40)
        print("[STEP 1] LIMRA 검색 API (search_documents)")
        print("=" * 40)

        for kw in keywords:
            search_results = await agent.search_documents(query=kw, max_results=50)
            print(f"[SEARCH] '{kw}' 원본 결과: {len(search_results)}개")

            # 연도 필터 적용
            if start_year or end_year:
                search_results = filter_docs_by_year(search_results, start_year, end_year)
                print(f"[SEARCH] 연도 필터({start_year}-{end_year}) 후: {len(search_results)}개")

            for doc in search_results:
                url = doc.get('url', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(doc)

        print(f"\n[STEP 1 결과] {len(all_results)}개 문서")

        # 2단계: Research 섹션 탐색
        print("\n" + "=" * 40)
        print("[STEP 2] Research 섹션 탐색 (browse_research_with_filter)")
        print("=" * 40)

        browse_results = await agent.browse_research_with_filter(
            keywords=keywords,
            start_year=start_year,
            end_year=end_year,
            auto_download=False
        )

        print(f"[BROWSE] 결과: {len(browse_results)}개")

        # 중복 제거하며 병합
        for doc in browse_results:
            url = doc.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(doc)

        # 최종 결과
        print("\n" + "=" * 60)
        print("[최종 결과]")
        print("=" * 60)
        print(f"총 문서 수: {len(all_results)}개")

        if all_results:
            print("\n[문서 목록]")
            for i, doc in enumerate(all_results[:15], 1):
                title = doc.get('title', 'N/A')[:50]
                year = doc.get('year', 'N/A')
                print(f"  {i}. [{year}] {title}...")

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[정리] 브라우저 종료 중...")
        await agent.close()
        print("[완료]")


if __name__ == "__main__":
    # Retention, 2024-2025 테스트
    asyncio.run(simulate_webapp_search(
        keywords=["Retention"],
        start_year=2024,
        end_year=2025
    ))
