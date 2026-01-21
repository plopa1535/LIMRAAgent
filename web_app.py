"""
LIMRA 문서 검색 에이전트 - 웹 인터페이스
Flask 기반 웹 UI + 멀티스레드 서브에이전트 시스템
"""

import asyncio
import nest_asyncio
nest_asyncio.apply()  # 중첩 이벤트 루프 허용
import json
import os
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, render_template, request, jsonify, send_from_directory
from limra_search_agent import LimraSearchAgent
from sub_agents import AgentManager, SharedState

# AI 기능 임포트 (선택적)
try:
    from ai_helper import LimraAIHelper
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("[WARN] AI 기능을 사용할 수 없습니다. ai_helper.py를 확인하세요.")

app = Flask(__name__, template_folder='templates', static_folder='static')

# 비동기 작업 실행을 위한 ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=3)

# 전역 에이전트 및 상태
agent = None
agent_loop = None  # 에이전트 전용 이벤트 루프
ai_helper = None  # AI 도우미

# 서브에이전트 매니저
agent_manager: AgentManager = None

# 기존 호환성을 위한 agent_status (agent_manager와 동기화됨)
agent_status = {
    'logged_in': False,
    'message': '',
    'progress': '',
    'results': [],
    'is_running': False,
    'ai_enabled': False
}

# 설정
DOWNLOAD_FOLDER = "./limra_downloads"
Path(DOWNLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

# AI 자동 초기화
def auto_init_ai():
    """환경 변수에 API 키가 있으면 AI 자동 초기화"""
    global ai_helper, agent_status

    if not AI_AVAILABLE:
        return

    # 환경 변수에서 API 키 로드
    api_key = os.environ.get('GROQ_API_KEY')
    if api_key:
        try:
            ai_helper = LimraAIHelper(api_key=api_key)
            agent_status['ai_enabled'] = True
            print("[AI] AI 기능 자동 활성화됨 (Groq + Qwen 32B)")
            print("[AI] - AI 키워드 확장")
            print("[AI] - PDF 자동 요약")
            print("[AI] - 종합 리포트 생성")
        except Exception as e:
            print(f"[AI] AI 자동 초기화 실패: {str(e)}")
            print("[AI] 수동으로 API 키를 입력할 수 있습니다.")
    else:
        print("[AI] GROQ_API_KEY 환경 변수가 없습니다.")
        print("[AI] AI 기능을 사용하려면 웹 UI에서 API 키를 입력하세요.")
        print("[AI] https://console.groq.com/keys")

auto_init_ai()


def get_or_create_loop():
    """에이전트 전용 이벤트 루프 가져오기 또는 생성"""
    global agent_loop
    if agent_loop is None or agent_loop.is_closed():
        agent_loop = asyncio.new_event_loop()
    return agent_loop


def run_async(coro):
    """비동기 함수를 동기적으로 실행 - 동일한 루프 재사용 (Playwright 호환)"""
    global agent_loop
    try:
        # 에이전트 전용 루프 사용 (Playwright 객체 유지를 위해)
        if agent_loop is None or agent_loop.is_closed():
            agent_loop = asyncio.new_event_loop()
            print(f"[ASYNC] 새 이벤트 루프 생성", flush=True)

        asyncio.set_event_loop(agent_loop)
        # nest_asyncio가 적용되어 있으므로 run_until_complete 호출 가능
        return agent_loop.run_until_complete(coro)
    except Exception as e:
        print(f"[ASYNC ERROR] {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()
        raise


@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')


@app.route('/api/login', methods=['POST'])
def api_login():
    """로그인 API"""
    global agent, agent_status, agent_manager

    print("[API] /api/login 호출됨", flush=True)

    data = request.json or {}
    email = data.get('email', 'plopa1535@kyobo.com')
    password = data.get('password', 'Kyobo1234!@#$')

    print(f"[API] 로그인 시작: {email}", flush=True)

    def do_login_sync():
        global agent, agent_status, agent_manager
        print("[LOGIN THREAD] do_login_sync 시작", flush=True)
        agent_status['is_running'] = True
        agent_status['message'] = '로그인 중...'

        # 서브에이전트 상태 업데이트
        if agent_manager:
            agent_manager.update_state(is_running=True, message='로그인 중...', browser_status='opening')

        import sys

        print("\n" + "="*60, flush=True)
        print("[WEB] 로그인 프로세스 시작", flush=True)
        print("="*60, flush=True)

        try:
            async def do_login():
                global agent
                print("[WEB] LimraSearchAgent 생성 중...", flush=True)
                agent = LimraSearchAgent(
                    email=email,
                    password=password,
                    download_folder=DOWNLOAD_FOLDER,
                    headless=False  # 브라우저 표시 (CAPTCHA 대응)
                )
                print("[WEB] 브라우저 초기화 중...", flush=True)
                await agent.initialize()

                # 서브에이전트에 브라우저 참조 설정
                if agent_manager and agent.browser and agent.context and agent.page:
                    agent_manager.set_browser_refs(agent.browser, agent.context, agent.page)
                    print("[WEB] 서브에이전트에 브라우저 참조 설정 완료", flush=True)

                print("[WEB] 로그인 실행 중...", flush=True)
                success = await agent.login()
                print(f"[WEB] 로그인 결과: {success}", flush=True)
                return success

            success = run_async(do_login())

            if success:
                agent_status['logged_in'] = True
                agent_status['message'] = '로그인 성공!'
                if agent_manager:
                    agent_manager.update_state(logged_in=True, message='로그인 성공!', browser_status='ready')
                print("[WEB] 로그인 성공! 상태 업데이트 완료", flush=True)
            else:
                agent_status['message'] = '로그인 실패'
                if agent_manager:
                    agent_manager.update_state(message='로그인 실패', browser_status='error')
                print("[WEB] 로그인 실패", flush=True)

            return success

        except Exception as e:
            agent_status['message'] = f'오류: {str(e)}'
            if agent_manager:
                agent_manager.update_state(message=f'오류: {str(e)}', browser_status='error')
                agent_manager.shared_state.add_error(f'Login error: {str(e)}')
            print(f"[WEB ERROR] {type(e).__name__}: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()
            return False

        finally:
            agent_status['is_running'] = False
            if agent_manager:
                agent_manager.update_state(is_running=False)
            print("[WEB] 로그인 프로세스 종료\n", flush=True)

    # 백그라운드 스레드에서 로그인 실행
    executor.submit(do_login_sync)

    # 즉시 응답 반환 (로그인은 백그라운드에서 진행)
    return jsonify({
        'success': True,
        'message': '로그인 진행 중... 상태를 확인하세요.',
        'status': 'processing'
    })


@app.route('/api/ai-smart-search', methods=['POST'])
def api_ai_smart_search():
    """AI 스마트 검색 API - 키워드로 LIMRA 사이트 검색 및 AI 분석"""
    global agent, agent_status, ai_helper

    if not agent or not agent_status['logged_in']:
        return jsonify({'success': False, 'message': '먼저 로그인하세요.'})

    if not ai_helper:
        return jsonify({'success': False, 'message': 'AI 기능이 활성화되지 않았습니다.'})

    data = request.json
    keyword = data.get('keyword', '').strip()
    max_pages = data.get('max_pages', 20)

    if not keyword:
        return jsonify({'success': False, 'message': '검색 키워드를 입력하세요.'})

    def do_ai_search_sync():
        global agent_status
        agent_status['is_running'] = True
        agent_status['message'] = f'AI 스마트 검색 중: {keyword}'

        try:
            async def do_ai_search():
                results = await agent.ai_smart_search(
                    keyword=keyword,
                    ai_helper=ai_helper,
                    max_pages=max_pages
                )
                return results

            results = run_async(do_ai_search())

            if results:
                agent_status['message'] = f'AI 보고서 생성 완료'
                return results
            else:
                agent_status['message'] = '검색 결과 없음'
                return []

        except Exception as e:
            agent_status['message'] = f'오류: {str(e)}'
            print(f"[ERROR] AI 스마트 검색 실패: {e}")
            import traceback
            traceback.print_exc()
            return None

        finally:
            agent_status['is_running'] = False

    # 백그라운드 스레드에서 AI 검색 실행
    executor.submit(do_ai_search_sync)

    # 즉시 응답 반환
    return jsonify({
        'success': True,
        'message': f'AI가 "{keyword}"에 대한 콘텐츠를 검색하고 분석 중입니다...',
        'status': 'processing'
    })


@app.route('/api/search', methods=['POST'])
def api_search():
    """필터링 검색 API"""
    global agent, agent_status

    if not agent or not agent_status['logged_in']:
        return jsonify({'success': False, 'message': '먼저 로그인하세요.'})

    data = request.json
    keywords = data.get('keywords', [])
    start_year = data.get('start_year')
    end_year = data.get('end_year')
    auto_download = data.get('auto_download', False)

    # 문자열을 리스트로 변환
    if isinstance(keywords, str):
        keywords = [k.strip() for k in keywords.split(',') if k.strip()]

    # 연도를 정수로 변환
    if start_year:
        start_year = int(start_year)
    if end_year:
        end_year = int(end_year)

    def do_search_sync():
        global agent_status
        agent_status['is_running'] = True
        agent_status['message'] = '검색 중...'
        agent_status['results'] = []

        try:
            async def do_search():
                all_results = []
                seen_urls = set()

                # 1단계: LIMRA 검색 API 사용 (키워드가 있는 경우)
                if keywords:
                    agent_status['message'] = f'LIMRA 검색 중: {", ".join(keywords)}...'
                    print(f"\n[SEARCH] LIMRA 검색 API 사용: {keywords}", flush=True)

                    for kw in keywords:
                        try:
                            search_results = await agent.search_documents(query=kw, max_results=50)
                            print(f"[SEARCH] '{kw}' 검색 결과: {len(search_results)}개", flush=True)

                            for doc in search_results:
                                url = doc.get('url', '')
                                if url and url not in seen_urls:
                                    seen_urls.add(url)
                                    all_results.append(doc)
                        except Exception as e:
                            print(f"[SEARCH] 검색 오류: {e}", flush=True)

                # 2단계: Research 섹션 탐색 (추가 문서 수집)
                agent_status['message'] = 'Research 섹션 탐색 중...'
                print(f"\n[SEARCH] Research 섹션 탐색 시작", flush=True)

                browse_results = await agent.browse_research_with_filter(
                    keywords=keywords if keywords else None,
                    start_year=start_year,
                    end_year=end_year,
                    auto_download=False  # 다운로드는 별도로 처리
                )

                # 중복 제거하며 병합
                for doc in browse_results:
                    url = doc.get('url', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(doc)

                print(f"[SEARCH] 총 {len(all_results)}개 문서 발견 (중복 제거)", flush=True)

                # 자동 다운로드 처리
                if auto_download and all_results:
                    agent_status['message'] = f'{len(all_results)}개 문서 다운로드 중...'
                    agent.search_results = all_results
                    await agent.download_all_results()

                return all_results

            results = run_async(do_search())

            agent_status['results'] = results
            agent_status['message'] = f'{len(results)}개 문서 발견'
            return results

        except Exception as e:
            import traceback
            print(f"[SEARCH ERROR] {type(e).__name__}: {str(e)}", flush=True)
            traceback.print_exc()
            agent_status['message'] = f'오류: {str(e)}'
            return None

        finally:
            agent_status['is_running'] = False

    # 백그라운드 스레드에서 검색 실행
    executor.submit(do_search_sync)

    # 즉시 응답 반환
    return jsonify({
        'success': True,
        'message': '검색 진행 중... 상태를 확인하세요.',
        'status': 'processing'
    })


@app.route('/api/download', methods=['POST'])
def api_download():
    """문서 다운로드 API"""
    global agent, agent_status

    if not agent or not agent_status['logged_in']:
        return jsonify({'success': False, 'message': '먼저 로그인하세요.'})

    data = request.json
    documents = data.get('documents', [])

    if not documents:
        documents = agent_status['results']

    if not documents:
        return jsonify({'success': False, 'message': '다운로드할 문서가 없습니다.'})

    def do_download_sync():
        global agent_status, agent_manager
        agent_status['is_running'] = True
        agent_status['message'] = f'{len(documents)}개 문서 다운로드 중...'

        print(f"\n[DOWNLOAD] 다운로드 시작: {len(documents)}개 문서", flush=True)

        if agent_manager:
            agent_manager.update_state(is_running=True, message=f'{len(documents)}개 문서 다운로드 중...')

        try:
            async def do_download():
                print(f"[DOWNLOAD] search_results 설정: {len(documents)}개", flush=True)
                agent.search_results = documents
                print("[DOWNLOAD] download_all_results 호출...", flush=True)
                downloaded = await agent.download_all_results()
                print(f"[DOWNLOAD] 다운로드 완료: {len(downloaded) if downloaded else 0}개", flush=True)
                return downloaded

            downloaded = run_async(do_download())

            msg = f'{len(downloaded) if downloaded else 0}개 파일 다운로드 완료'
            agent_status['message'] = msg
            if agent_manager:
                agent_manager.update_state(message=msg)
            print(f"[DOWNLOAD] {msg}", flush=True)
            return downloaded

        except Exception as e:
            import traceback
            error_msg = f'다운로드 오류: {str(e)}'
            agent_status['message'] = error_msg
            if agent_manager:
                agent_manager.update_state(message=error_msg)
                agent_manager.shared_state.add_error(f'Download error: {str(e)}')
            print(f"[DOWNLOAD ERROR] {error_msg}", flush=True)
            traceback.print_exc()
            return None

        finally:
            agent_status['is_running'] = False
            if agent_manager:
                agent_manager.update_state(is_running=False)
            print("[DOWNLOAD] 다운로드 프로세스 종료\n", flush=True)

    # 백그라운드 스레드에서 다운로드 실행
    executor.submit(do_download_sync)

    # 즉시 응답 반환
    return jsonify({
        'success': True,
        'message': '다운로드 진행 중... 상태를 확인하세요.',
        'status': 'processing'
    })


@app.route('/api/status')
def api_status():
    """상태 확인 API"""
    global agent_manager

    # 서브에이전트 매니저가 있으면 통합 상태 반환
    if agent_manager:
        status = agent_manager.get_status()
        # 기존 agent_status와 병합 (results는 기존 것 유지)
        status['results'] = agent_status.get('results', [])
        status['ai_enabled'] = agent_status.get('ai_enabled', False)
        return jsonify(status)

    return jsonify(agent_status)


@app.route('/api/logout', methods=['POST'])
def api_logout():
    """로그아웃 API"""
    global agent, agent_status, agent_loop, agent_manager

    try:
        if agent:
            run_async(agent.close())

        agent = None
        agent_status['logged_in'] = False
        agent_status['message'] = '로그아웃됨'
        agent_status['results'] = []

        # 서브에이전트 브라우저 참조 클리어
        if agent_manager:
            agent_manager.clear_browser_refs()
            agent_manager.update_state(logged_in=False, message='로그아웃됨', browser_status='closed')

        # 이벤트 루프 정리
        if agent_loop and not agent_loop.is_closed():
            agent_loop.close()
            agent_loop = None

        return jsonify({'success': True, 'message': '로그아웃되었습니다.'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/downloads/<path:filename>')
def download_file(filename):
    """다운로드 파일 제공"""
    return send_from_directory(DOWNLOAD_FOLDER, filename)


@app.route('/api/agents')
def api_agents():
    """서브에이전트 상태 확인 API"""
    global agent_manager

    if not agent_manager:
        return jsonify({'error': 'Agent manager not initialized'})

    agents_info = {
        'manager': 'running',
        'agents': {
            'BrowserController': {
                'running': agent_manager.browser_agent._running,
                'interval': agent_manager.browser_agent.get_interval(),
                'browser_status': agent_manager.shared_state.get('browser_status'),
                'has_page': agent_manager.browser_agent.page is not None,
                'last_check': str(agent_manager.browser_agent.last_check) if agent_manager.browser_agent.last_check else None
            },
            'SessionManager': {
                'running': agent_manager.session_agent._running,
                'interval': agent_manager.session_agent.get_interval(),
                'has_context': agent_manager.session_agent.context is not None,
                'last_check': str(agent_manager.session_agent.last_session_check) if agent_manager.session_agent.last_session_check else None
            },
            'DownloadManager': {
                'running': agent_manager.download_agent._running,
                'interval': agent_manager.download_agent.get_interval(),
                'queue_size': len(agent_manager.shared_state.get('download_queue', [])),
                'download_folder': str(agent_manager.download_agent.download_folder)
            },
            'UISync': {
                'running': agent_manager.ui_agent._running,
                'interval': agent_manager.ui_agent.get_interval(),
                'callbacks_count': len(agent_manager.ui_agent._callbacks)
            }
        },
        'shared_state': agent_manager.shared_state.get_all(),
        'errors': agent_manager.shared_state.get('errors', [])[-10:]  # 최근 10개 에러
    }

    return jsonify(agents_info)


@app.route('/api/files')
def list_files():
    """다운로드된 파일 목록"""
    files = []
    download_path = Path(DOWNLOAD_FOLDER)

    for f in download_path.glob('*'):
        if f.is_file():
            files.append({
                'name': f.name,
                'size': f.stat().st_size,
                'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })

    files.sort(key=lambda x: x['modified'], reverse=True)
    return jsonify(files)


@app.route('/api/files/delete', methods=['POST'])
def delete_file():
    """파일 삭제"""
    data = request.json
    filename = data.get('filename', '')

    if not filename:
        return jsonify({'success': False, 'message': '파일명이 필요합니다.'})

    file_path = Path(DOWNLOAD_FOLDER) / filename

    # 경로 탐색 공격 방지
    if not file_path.resolve().parent == Path(DOWNLOAD_FOLDER).resolve():
        return jsonify({'success': False, 'message': '잘못된 파일 경로입니다.'})

    if not file_path.exists():
        return jsonify({'success': False, 'message': '파일을 찾을 수 없습니다.'})

    try:
        file_path.unlink()
        return jsonify({'success': True, 'message': f'{filename} 삭제 완료'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'삭제 실패: {str(e)}'})


@app.route('/api/files/delete-all', methods=['POST'])
def delete_all_files():
    """모든 다운로드 파일 삭제 (로그 파일 제외)"""
    download_path = Path(DOWNLOAD_FOLDER)
    deleted_count = 0
    errors = []

    try:
        for f in download_path.glob('*'):
            if f.is_file():
                # 로그 파일과 세션 파일은 제외
                if f.suffix in ['.log', '.json'] or 'debug' in f.name.lower() or 'session' in f.name.lower():
                    continue

                try:
                    f.unlink()
                    deleted_count += 1
                except Exception as e:
                    errors.append(f'{f.name}: {str(e)}')

        if errors:
            return jsonify({
                'success': True,
                'message': f'{deleted_count}개 파일 삭제 완료 ({len(errors)}개 오류)',
                'errors': errors
            })
        else:
            return jsonify({
                'success': True,
                'message': f'{deleted_count}개 파일 삭제 완료'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': f'삭제 실패: {str(e)}'})


# ============= AI 기능 API =============

@app.route('/api/ai/init', methods=['POST'])
def api_ai_init():
    """AI 초기화"""
    global ai_helper, agent_status

    if not AI_AVAILABLE:
        return jsonify({
            'success': False,
            'message': 'AI 기능을 사용할 수 없습니다. ai_helper.py와 필요한 패키지를 확인하세요.'
        })

    data = request.json
    api_key = data.get('api_key') or os.environ.get('GOOGLE_API_KEY')

    if not api_key:
        return jsonify({
            'success': False,
            'message': 'Google API 키가 필요합니다. https://aistudio.google.com/app/apikey'
        })

    try:
        ai_helper = LimraAIHelper(api_key=api_key)
        agent_status['ai_enabled'] = True
        return jsonify({
            'success': True,
            'message': 'AI 기능이 활성화되었습니다 (Gemini 2.0 Flash)'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'AI 초기화 실패: {str(e)}'
        })


@app.route('/api/ai/expand-keywords', methods=['POST'])
def api_ai_expand_keywords():
    """AI 키워드 확장"""
    global ai_helper

    if not ai_helper:
        return jsonify({
            'success': False,
            'message': '먼저 AI를 초기화하세요.'
        })

    data = request.json
    keyword = data.get('keyword', '')
    industry = data.get('industry', 'insurance')
    count = data.get('count', 10)

    if not keyword:
        return jsonify({
            'success': False,
            'message': '키워드를 입력하세요.'
        })

    def expand_keywords_sync():
        try:
            result = ai_helper.expand_keywords(keyword, industry=industry, count=count)
            return result
        except Exception as e:
            return {'error': str(e)}

    # 백그라운드 실행
    future = executor.submit(expand_keywords_sync)
    result = future.result(timeout=30)  # 30초 타임아웃

    if 'error' in result:
        return jsonify({
            'success': False,
            'message': result['error']
        })

    return jsonify({
        'success': True,
        'original_keyword': keyword,
        'all_keywords': result.get('all_keywords', []),
        'synonyms': result.get('synonyms', []),
        'related_concepts': result.get('related_concepts', []),
        'specific_topics': result.get('specific_topics', []),
        'metrics': result.get('metrics', []),
        'search_suggestions': result.get('search_suggestions', [])
    })


@app.route('/api/ai/summarize-pdf', methods=['POST'])
def api_ai_summarize_pdf():
    """PDF 요약"""
    global ai_helper

    if not ai_helper:
        return jsonify({
            'success': False,
            'message': '먼저 AI를 초기화하세요.'
        })

    data = request.json
    filename = data.get('filename', '')
    language = data.get('language', 'ko')

    if not filename:
        return jsonify({
            'success': False,
            'message': '파일명을 입력하세요.'
        })

    pdf_path = Path(DOWNLOAD_FOLDER) / filename

    if not pdf_path.exists():
        return jsonify({
            'success': False,
            'message': f'파일을 찾을 수 없습니다: {filename}'
        })

    def summarize_pdf_sync():
        try:
            result = ai_helper.summarize_pdf(str(pdf_path), language=language)
            return result
        except Exception as e:
            return {'error': str(e)}

    # 백그라운드 실행
    agent_status['message'] = f'PDF 요약 중: {filename}'
    future = executor.submit(summarize_pdf_sync)
    result = future.result(timeout=120)  # 2분 타임아웃

    if 'error' in result:
        return jsonify({
            'success': False,
            'message': result['error']
        })

    return jsonify({
        'success': True,
        'filename': filename,
        'summary': result.get('summary', {})
    })


@app.route('/api/ai/generate-report', methods=['POST'])
def api_ai_generate_report():
    """종합 리포트 생성"""
    global ai_helper, agent_status

    if not ai_helper:
        return jsonify({
            'success': False,
            'message': '먼저 AI를 초기화하세요.'
        })

    data = request.json
    keyword = data.get('keyword', '')
    summaries = data.get('summaries', [])
    language = data.get('language', 'ko')

    if not keyword:
        return jsonify({
            'success': False,
            'message': '키워드를 입력하세요.'
        })

    def generate_report_sync():
        try:
            result = ai_helper.generate_comprehensive_report(
                keyword=keyword,
                summaries=summaries,
                language=language
            )
            return result
        except Exception as e:
            return {'error': str(e)}

    # 백그라운드 실행
    agent_status['message'] = '종합 리포트 생성 중...'
    future = executor.submit(generate_report_sync)
    result = future.result(timeout=120)  # 2분 타임아웃

    if 'error' in result:
        return jsonify({
            'success': False,
            'message': result['error']
        })

    return jsonify({
        'success': True,
        'keyword': keyword,
        'report': result.get('report', '')
    })


def init_agent_manager():
    """서브에이전트 매니저 초기화"""
    global agent_manager
    agent_manager = AgentManager(DOWNLOAD_FOLDER)
    # 참고: 서브에이전트는 Playwright와 이벤트 루프 충돌을 피하기 위해 시작하지 않음
    # 상태 관리는 agent_manager.shared_state를 통해 수동으로 처리
    print("[SYSTEM] Sub-agents manager initialized")

    # 상태 변경 리스너 추가 (agent_status 동기화)
    def sync_status(key, value):
        global agent_status
        if key in agent_status:
            agent_status[key] = value

    agent_manager.shared_state.add_listener(sync_status)


def shutdown_agent_manager():
    """서브에이전트 매니저 종료"""
    global agent_manager
    if agent_manager:
        agent_manager.stop_all()
        print("[SYSTEM] Sub-agents stopped")


if __name__ == '__main__':
    print("=" * 50)
    print("LIMRA 문서 검색 에이전트 - 웹 UI")
    print("=" * 50)

    # 서브에이전트 매니저 초기화
    init_agent_manager()

    print("\n브라우저에서 http://localhost:5000 접속하세요\n")

    try:
        # debug=False로 설정하여 watchdog 재시작 방지 (다운로드 안정성 향상)
        app.run(debug=False, port=5000, threaded=True)
    finally:
        shutdown_agent_manager()
