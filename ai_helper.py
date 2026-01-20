"""
LIMRA AI Helper Module
Groq + Qwen2.5-72B를 사용한 AI 기능
- PDF 요약
- 키워드 확장
- 리포트 생성
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from groq import Groq

# PDF 텍스트 추출
try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("[WARN] PyPDF2가 설치되지 않았습니다. pip install PyPDF2")


class LimraAIHelper:
    """Groq + Qwen2.5-72B를 사용한 AI 도우미"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Groq API 키 (없으면 환경변수 GROQ_API_KEY 사용)
        """
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Groq API 키가 필요합니다.\n"
                "1. https://console.groq.com/keys 에서 API 키 생성\n"
                "2. 환경변수 설정: set GROQ_API_KEY=your_api_key\n"
                "   또는 LimraAIHelper(api_key='your_api_key') 로 직접 전달"
            )

        # Groq 클라이언트 설정
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"  # Llama 3.3 70B

        print("[OK] Groq + Llama 3.3 70B 초기화 완료")

    def extract_pdf_text(self, pdf_path: str, max_pages: int = 20) -> str:
        """PDF에서 텍스트 추출

        Args:
            pdf_path: PDF 파일 경로
            max_pages: 최대 페이지 수

        Returns:
            추출된 텍스트
        """
        if not PDF_SUPPORT:
            return "[ERROR] PyPDF2가 설치되지 않았습니다."

        try:
            text_parts = []
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                total_pages = min(len(reader.pages), max_pages)

                for i in range(total_pages):
                    page = reader.pages[i]
                    text = page.extract_text()
                    if text:
                        text_parts.append(f"--- Page {i+1} ---\n{text}")

            return "\n\n".join(text_parts)

        except Exception as e:
            return f"[ERROR] PDF 읽기 실패: {e}"

    def summarize_pdf(self, pdf_path: str, language: str = "ko") -> Dict:
        """PDF 문서 요약

        Args:
            pdf_path: PDF 파일 경로
            language: 출력 언어 (ko: 한국어, en: 영어)

        Returns:
            요약 결과 딕셔너리
        """
        print(f"[AI] PDF 요약 중: {Path(pdf_path).name}")

        # 텍스트 추출
        text = self.extract_pdf_text(pdf_path)

        if text.startswith("[ERROR]"):
            return {"error": text, "summary": None}

        if not text.strip():
            return {"error": "PDF에서 텍스트를 추출할 수 없습니다.", "summary": None}

        # 텍스트가 너무 길면 자르기 (약 30000자)
        if len(text) > 30000:
            text = text[:30000] + "\n\n[... 이하 생략 ...]"

        # 요약 프롬프트
        lang_instruction = "한국어로" if language == "ko" else "in English"

        prompt = f"""다음은 보험/금융 산업 관련 연구 문서입니다. {lang_instruction} 요약해주세요.

문서 내용:
{text}

다음 형식으로 요약해주세요:
1. **제목**: 문서 제목
2. **핵심 주제**: 1-2문장으로 주제 설명
3. **주요 내용**: 3-5개의 핵심 포인트 (불릿 포인트)
4. **주요 통계/수치**: 중요한 데이터가 있다면 나열
5. **결론/시사점**: 문서의 결론이나 비즈니스 시사점

간결하고 명확하게 작성해주세요."""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
                temperature=0.3,
                max_tokens=2000,
            )

            summary = chat_completion.choices[0].message.content

            print("[OK] PDF 요약 완료")

            return {
                "file": Path(pdf_path).name,
                "summary": summary,
                "text_length": len(text),
                "error": None
            }

        except Exception as e:
            print(f"[ERROR] AI 요약 실패: {e}")
            return {"error": str(e), "summary": None}

    def expand_keywords(self, keyword: str, industry: str = "insurance", count: int = 10) -> Dict:
        """키워드 확장 - 관련 검색어 생성

        Args:
            keyword: 원본 키워드
            industry: 산업 분야 (insurance, finance, retirement 등)
            count: 생성할 관련 키워드 수

        Returns:
            확장된 키워드 목록
        """
        print(f"[AI] 키워드 확장 중: {keyword}")

        prompt = f"""당신은 보험 및 금융 산업 전문가입니다.

원본 키워드: "{keyword}"
산업 분야: {industry}

이 키워드와 관련된 검색어를 {count}개 생성해주세요.
LIMRA (Life Insurance and Market Research Association) 연구 자료를 검색할 때 유용한 키워드여야 합니다.

다음 카테고리로 분류해서 생성해주세요:
1. 동의어/유사어 (Synonyms)
2. 관련 개념 (Related Concepts)
3. 세부 주제 (Specific Topics)
4. 측정 지표 (Metrics/KPIs)

JSON 형식으로 응답해주세요:
{{
    "original": "{keyword}",
    "synonyms": ["키워드1", "키워드2"],
    "related_concepts": ["키워드3", "키워드4"],
    "specific_topics": ["키워드5", "키워드6"],
    "metrics": ["키워드7", "키워드8"],
    "search_suggestions": ["검색에 좋은 조합1", "검색에 좋은 조합2"]
}}

영어 키워드로 생성해주세요 (LIMRA는 영어 사이트입니다)."""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
                temperature=0.7,
                max_tokens=1500,
            )

            text = chat_completion.choices[0].message.content

            # JSON 추출 (마크다운 코드블록 제거)
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            result = json.loads(text.strip())

            # 모든 키워드를 하나의 리스트로
            all_keywords = [keyword]  # 원본 포함
            for key in ["synonyms", "related_concepts", "specific_topics", "metrics"]:
                if key in result:
                    all_keywords.extend(result[key])

            result["all_keywords"] = list(set(all_keywords))  # 중복 제거
            result["expanded_keywords"] = result["all_keywords"]  # 호환성을 위해 추가

            print(f"[OK] {len(result['all_keywords'])}개 키워드 생성 완료")

            return result

        except json.JSONDecodeError as e:
            print(f"[WARN] JSON 파싱 실패, 텍스트로 반환: {e}")
            return {
                "original": keyword,
                "all_keywords": [keyword],
                "raw_response": text if 'text' in dir() else str(e),
                "error": "JSON 파싱 실패"
            }

        except Exception as e:
            print(f"[ERROR] 키워드 확장 실패: {e}")
            return {"original": keyword, "all_keywords": [keyword], "error": str(e)}

    def generate_report(self, documents: List[Dict], keyword: str, language: str = "ko") -> Dict:
        """검색 결과 기반 종합 리포트 생성

        Args:
            documents: 검색된 문서 목록 (title, type, url, summary 등)
            keyword: 검색 키워드
            language: 출력 언어

        Returns:
            생성된 리포트
        """
        print(f"[AI] 종합 리포트 생성 중: {keyword}")

        # 문서 정보 정리
        doc_info = []
        for i, doc in enumerate(documents[:20], 1):  # 최대 20개
            info = f"{i}. [{doc.get('type', 'Unknown')}] {doc.get('title', 'No Title')}"
            if doc.get('summary'):
                info += f"\n   요약: {doc['summary'][:200]}..."
            if doc.get('year'):
                info += f"\n   연도: {doc['year']}"
            doc_info.append(info)

        docs_text = "\n\n".join(doc_info)

        lang_instruction = "한국어로" if language == "ko" else "in English"

        prompt = f"""당신은 보험 산업 리서치 전문가입니다.

검색 키워드: "{keyword}"
검색된 문서 수: {len(documents)}개

검색된 문서 목록:
{docs_text}

이 검색 결과를 바탕으로 {lang_instruction} 종합 분석 리포트를 작성해주세요.

리포트 구성:
## 1. 개요 (Executive Summary)
- 검색 주제에 대한 간략한 소개
- 검색 결과 요약

## 2. 주요 트렌드
- 문서들에서 발견되는 주요 트렌드 3-5개
- 각 트렌드에 대한 설명

## 3. 문서 분류
- 문서 유형별 분류 및 특징
- 주요 문서 하이라이트

## 4. 비즈니스 시사점
- 보험사/금융사에 대한 시사점
- 실무 적용 포인트

## 5. 추가 연구 제안
- 더 조사해볼 만한 관련 주제
- 권장 키워드

전문적이면서도 이해하기 쉽게 작성해주세요."""

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
                temperature=0.5,
                max_tokens=3000,
            )

            report = chat_completion.choices[0].message.content

            print("[OK] 리포트 생성 완료")

            return {
                "keyword": keyword,
                "document_count": len(documents),
                "report": report,
                "error": None
            }

        except Exception as e:
            print(f"[ERROR] 리포트 생성 실패: {e}")
            return {"keyword": keyword, "report": None, "error": str(e)}

    def summarize_multiple_pdfs(self, pdf_folder: str, language: str = "ko") -> List[Dict]:
        """폴더 내 모든 PDF 요약

        Args:
            pdf_folder: PDF 파일들이 있는 폴더
            language: 출력 언어

        Returns:
            각 PDF의 요약 목록
        """
        folder = Path(pdf_folder)
        pdf_files = list(folder.glob("*.pdf"))

        print(f"[AI] {len(pdf_files)}개 PDF 요약 시작...")

        summaries = []
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"\n[{i}/{len(pdf_files)}] {pdf_path.name}")
            summary = self.summarize_pdf(str(pdf_path), language)
            summaries.append(summary)

        return summaries

    def generate_comprehensive_report(self, keyword: str, summaries: List, language: str = "ko") -> Dict:
        """여러 PDF 요약을 기반으로 종합 리포트 생성 (web_app.py 호환성)"""
        # 요약을 문서 형식으로 변환
        documents = []
        for summary in summaries:
            if isinstance(summary, dict) and summary.get('summary'):
                documents.append({
                    'title': summary.get('file', 'Unknown'),
                    'type': 'PDF',
                    'summary': summary['summary'][:200]
                })

        # generate_report 호출
        return self.generate_report(documents, keyword, language)


# 테스트 코드
if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("LIMRA AI Helper - Groq + Qwen2.5 Test")
    print("=" * 60)

    # API 키 확인
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("\n[ERROR] GROQ_API_KEY 환경변수가 설정되지 않았습니다.")
        print("설정 방법:")
        print("  Windows: set GROQ_API_KEY=your_api_key")
        print("  또는 직접 전달: LimraAIHelper(api_key='your_key')")
        sys.exit(1)

    try:
        # AI 헬퍼 초기화
        ai = LimraAIHelper()

        # 1. 키워드 확장 테스트
        print("\n" + "-" * 40)
        print("[TEST] 키워드 확장")
        print("-" * 40)
        result = ai.expand_keywords("Retention", industry="insurance")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 2. PDF 요약 테스트 (파일이 있는 경우)
        test_folder = Path("./limra_downloads")
        pdf_files = list(test_folder.glob("*.pdf"))

        if pdf_files:
            print("\n" + "-" * 40)
            print("[TEST] PDF 요약")
            print("-" * 40)
            summary = ai.summarize_pdf(str(pdf_files[0]))
            print(summary.get("summary", summary.get("error")))

        print("\n[OK] 테스트 완료!")

    except Exception as e:
        print(f"\n[ERROR] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
