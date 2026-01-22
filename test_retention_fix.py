"""
Retention 검색 수정 확인 테스트
web_app.py의 연도 필터 적용 테스트
"""

import asyncio
import sys
import io

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from limra_search_agent import LimraSearchAgent

# web_app.py에서 추가한 함수들 복사
import re

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


async def test_retention_search():
    """Retention 검색 테스트"""
    print("=" * 60)
    print("Retention 검색 수정 테스트")
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

        # 테스트 1: search_documents 원본 결과
        print("\n" + "=" * 40)
        print("[TEST 1] search_documents('Retention') 원본")
        print("=" * 40)
        raw_results = await agent.search_documents(query="Retention", max_results=20)
        print(f"원본 결과: {len(raw_results)}개")

        # 테스트 2: 연도 필터 적용 (2024-2025)
        print("\n" + "=" * 40)
        print("[TEST 2] 연도 필터 적용 (2024-2025)")
        print("=" * 40)
        filtered_results = filter_docs_by_year(raw_results.copy(), start_year=2024, end_year=2025)
        print(f"필터 후 결과: {len(filtered_results)}개")

        print("\n[필터링된 문서 목록]")
        for i, doc in enumerate(filtered_results, 1):
            title = doc.get('title', 'N/A')[:50]
            year = doc.get('year', 'N/A')
            print(f"  {i}. [{year}] {title}...")

        # 테스트 3: 제외된 문서 확인
        print("\n[제외된 문서 목록]")
        excluded = [d for d in raw_results if d not in filtered_results]
        for i, doc in enumerate(excluded, 1):
            title = doc.get('title', 'N/A')[:50]
            year = extract_year_from_doc(doc)
            print(f"  {i}. [{year}] {title}...")

        print("\n" + "=" * 60)
        print("[결론]")
        print(f"  - 원본 검색 결과: {len(raw_results)}개")
        print(f"  - 2024-2025 필터 후: {len(filtered_results)}개")
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n[정리] 브라우저 종료 중...")
        await agent.close()
        print("[완료]")


if __name__ == "__main__":
    asyncio.run(test_retention_search())
