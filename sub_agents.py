"""
LIMRA Search Agent - Sub Agents System
멀티스레드/비동기 기반 서브에이전트 시스템

각 에이전트는 독립적으로 실행되며 shared_state를 통해 상태를 공유합니다.
"""

import asyncio
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import json


class SharedState:
    """에이전트 간 공유 상태 관리 (Thread-safe)"""

    def __init__(self):
        self._lock = threading.RLock()
        self._state = {
            'logged_in': False,
            'is_running': False,
            'message': '',
            'progress': '',
            'results': [],
            'ai_enabled': False,
            'browser_status': 'closed',  # closed, opening, ready, error
            'download_queue': [],
            'download_progress': {'current': 0, 'total': 0, 'current_file': ''},
            'errors': [],
            'last_activity': None,
        }
        self._listeners: list[Callable] = []

    def get(self, key: str, default=None):
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value: Any):
        with self._lock:
            old_value = self._state.get(key)
            self._state[key] = value
            if old_value != value:
                self._notify_listeners(key, value)

    def update(self, updates: Dict[str, Any]):
        with self._lock:
            for key, value in updates.items():
                old_value = self._state.get(key)
                self._state[key] = value
                if old_value != value:
                    self._notify_listeners(key, value)

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return self._state.copy()

    def add_listener(self, callback: Callable):
        """상태 변경 리스너 추가"""
        self._listeners.append(callback)

    def _notify_listeners(self, key: str, value: Any):
        """리스너들에게 상태 변경 알림"""
        for listener in self._listeners:
            try:
                listener(key, value)
            except Exception as e:
                print(f"[SharedState] Listener error: {e}")

    def add_error(self, error_msg: str):
        """에러 추가"""
        with self._lock:
            errors = self._state.get('errors', [])
            errors.append({
                'time': datetime.now().isoformat(),
                'message': error_msg
            })
            # 최근 100개만 유지
            self._state['errors'] = errors[-100:]

    def clear_errors(self):
        """에러 목록 클리어"""
        with self._lock:
            self._state['errors'] = []


class SubAgent(ABC):
    """서브에이전트 기본 클래스"""

    def __init__(self, name: str, shared_state: SharedState):
        self.name = name
        self.shared_state = shared_state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self):
        """에이전트 시작 (백그라운드 스레드)"""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[{self.name}] Started")

    def stop(self):
        """에이전트 중지"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print(f"[{self.name}] Stopped")

    def _run_loop(self):
        """이벤트 루프 실행"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main_loop())
        except Exception as e:
            print(f"[{self.name}] Error: {e}")
        finally:
            self._loop.close()

    async def _main_loop(self):
        """메인 루프"""
        while self._running:
            try:
                await self.run()
            except Exception as e:
                print(f"[{self.name}] Run error: {e}")
                self.shared_state.add_error(f"{self.name}: {str(e)}")
            await asyncio.sleep(self.get_interval())

    @abstractmethod
    async def run(self):
        """에이전트 메인 로직 (서브클래스에서 구현)"""
        pass

    def get_interval(self) -> float:
        """실행 간격 (초)"""
        return 1.0

    def log(self, message: str):
        """로그 출력"""
        print(f"[{self.name}] {message}")


class BrowserControllerAgent(SubAgent):
    """브라우저 제어 및 모니터링 에이전트"""

    def __init__(self, shared_state: SharedState):
        super().__init__("BrowserController", shared_state)
        self.page = None
        self.context = None
        self.browser = None
        self.last_check = None

    def set_browser_refs(self, browser, context, page):
        """브라우저 참조 설정"""
        self.browser = browser
        self.context = context
        self.page = page
        self.shared_state.set('browser_status', 'ready')

    def clear_browser_refs(self):
        """브라우저 참조 클리어"""
        self.browser = None
        self.context = None
        self.page = None
        self.shared_state.set('browser_status', 'closed')

    async def run(self):
        """브라우저 상태 모니터링"""
        if not self.page:
            return

        try:
            # 페이지 응답 확인
            await asyncio.wait_for(
                self._check_page_alive(),
                timeout=5.0
            )
            self.shared_state.set('browser_status', 'ready')
            self.last_check = datetime.now()

        except asyncio.TimeoutError:
            self.log("Page not responding")
            self.shared_state.set('browser_status', 'error')
            self.shared_state.add_error("Browser page not responding")

        except Exception as e:
            self.log(f"Browser check error: {e}")
            self.shared_state.set('browser_status', 'error')

    async def _check_page_alive(self):
        """페이지 생존 확인"""
        if self.page and not self.page.is_closed():
            # 간단한 JavaScript 실행으로 응답 확인
            await self.page.evaluate("() => true")
            return True
        return False

    async def take_screenshot(self, path: str) -> bool:
        """스크린샷 캡처"""
        if not self.page or self.page.is_closed():
            return False

        try:
            await self.page.screenshot(path=path)
            self.log(f"Screenshot saved: {path}")
            return True
        except Exception as e:
            self.log(f"Screenshot error: {e}")
            return False

    def get_interval(self) -> float:
        return 3.0  # 3초마다 체크


class SessionManagerAgent(SubAgent):
    """세션 관리 에이전트"""

    def __init__(self, shared_state: SharedState, session_file: str = "./limra_downloads/limra_session.json"):
        super().__init__("SessionManager", shared_state)
        self.session_file = Path(session_file)
        self.context = None
        self.page = None
        self.last_session_check = None

    def set_context(self, context, page):
        """컨텍스트 설정"""
        self.context = context
        self.page = page

    async def run(self):
        """세션 상태 체크"""
        if not self.page or not self.context:
            return

        try:
            # 로그인 상태 확인
            is_logged_in = await self._check_login_status()

            current_status = self.shared_state.get('logged_in')
            if is_logged_in != current_status:
                self.shared_state.set('logged_in', is_logged_in)
                self.log(f"Login status changed: {is_logged_in}")

                if is_logged_in:
                    # 세션 저장
                    await self._save_session()

            self.last_session_check = datetime.now()

        except Exception as e:
            self.log(f"Session check error: {e}")

    async def _check_login_status(self) -> bool:
        """로그인 상태 확인"""
        if not self.page or self.page.is_closed():
            return False

        try:
            content = await self.page.content()
            content_lower = content.lower()

            # 로그아웃 버튼이 있으면 로그인 상태
            logout_indicators = ['logout', 'log out', 'sign out', 'signout']
            for indicator in logout_indicators:
                if indicator in content_lower:
                    return True

            # 로그인 버튼이 있으면 로그아웃 상태
            login_indicators = ['login', 'log in', 'sign in', 'signin']
            for indicator in login_indicators:
                if indicator in content_lower:
                    return False

            # URL로 확인
            url = self.page.url.lower()
            if 'login' in url:
                return False

            return self.shared_state.get('logged_in', False)

        except Exception:
            return False

    async def _save_session(self):
        """세션 저장"""
        if not self.context:
            return

        try:
            storage_state = await self.context.storage_state()
            self.session_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(storage_state, f)

            self.log("Session saved")
        except Exception as e:
            self.log(f"Session save error: {e}")

    async def load_session(self) -> dict:
        """세션 로드"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.log(f"Session load error: {e}")
        return None

    def get_interval(self) -> float:
        return 10.0  # 10초마다 체크


class DownloadManagerAgent(SubAgent):
    """다운로드 관리 에이전트"""

    def __init__(self, shared_state: SharedState, download_folder: str = "./limra_downloads"):
        super().__init__("DownloadManager", shared_state)
        self.download_folder = Path(download_folder)
        self.download_folder.mkdir(parents=True, exist_ok=True)
        self._queue_lock = threading.Lock()

    def add_to_queue(self, documents: list):
        """다운로드 큐에 추가"""
        with self._queue_lock:
            queue = self.shared_state.get('download_queue', [])
            queue.extend(documents)
            self.shared_state.set('download_queue', queue)
            self.shared_state.update({
                'download_progress': {
                    'current': 0,
                    'total': len(queue),
                    'current_file': ''
                }
            })
            self.log(f"Added {len(documents)} documents to queue")

    def clear_queue(self):
        """다운로드 큐 클리어"""
        with self._queue_lock:
            self.shared_state.set('download_queue', [])
            self.shared_state.set('download_progress', {
                'current': 0, 'total': 0, 'current_file': ''
            })

    async def run(self):
        """다운로드 큐 상태 모니터링"""
        queue = self.shared_state.get('download_queue', [])
        progress = self.shared_state.get('download_progress', {})

        if queue:
            # 다운로드 진행 중 상태 업데이트
            completed = progress.get('current', 0)
            total = progress.get('total', len(queue))

            if completed < total:
                self.shared_state.set('message',
                    f'다운로드 중... ({completed}/{total})')

    def update_progress(self, current: int, current_file: str = ''):
        """진행률 업데이트"""
        progress = self.shared_state.get('download_progress', {})
        progress['current'] = current
        progress['current_file'] = current_file
        self.shared_state.set('download_progress', progress)

    def get_downloaded_files(self) -> list:
        """다운로드된 파일 목록"""
        files = []
        for f in self.download_folder.iterdir():
            if f.is_file() and f.suffix.lower() == '.pdf':
                files.append({
                    'name': f.name,
                    'size': f.stat().st_size,
                    'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
                })
        return sorted(files, key=lambda x: x['modified'], reverse=True)

    def get_interval(self) -> float:
        return 2.0  # 2초마다 체크


class UISyncAgent(SubAgent):
    """UI 동기화 에이전트"""

    def __init__(self, shared_state: SharedState):
        super().__init__("UISync", shared_state)
        self._callbacks: list[Callable] = []
        self._last_state = {}

    def add_callback(self, callback: Callable):
        """UI 업데이트 콜백 추가"""
        self._callbacks.append(callback)

    async def run(self):
        """상태 변경 감지 및 UI 업데이트"""
        current_state = self.shared_state.get_all()

        # 변경된 항목 감지
        changes = {}
        for key, value in current_state.items():
            if key not in self._last_state or self._last_state[key] != value:
                changes[key] = value

        if changes:
            # 콜백 호출
            for callback in self._callbacks:
                try:
                    callback(changes)
                except Exception as e:
                    self.log(f"Callback error: {e}")

        self._last_state = current_state.copy()

    def get_status_for_api(self) -> dict:
        """API 응답용 상태 반환"""
        state = self.shared_state.get_all()
        return {
            'logged_in': state.get('logged_in', False),
            'is_running': state.get('is_running', False),
            'message': state.get('message', ''),
            'progress': state.get('progress', ''),
            'results': state.get('results', []),
            'ai_enabled': state.get('ai_enabled', False),
            'browser_status': state.get('browser_status', 'closed'),
            'download_progress': state.get('download_progress', {}),
        }

    def get_interval(self) -> float:
        return 0.5  # 0.5초마다 체크


class AgentManager:
    """에이전트 매니저 - 모든 서브에이전트 관리"""

    def __init__(self, download_folder: str = "./limra_downloads"):
        self.shared_state = SharedState()

        # 에이전트 생성
        self.browser_agent = BrowserControllerAgent(self.shared_state)
        self.session_agent = SessionManagerAgent(self.shared_state)
        self.download_agent = DownloadManagerAgent(self.shared_state, download_folder)
        self.ui_agent = UISyncAgent(self.shared_state)

        self._agents = [
            self.browser_agent,
            self.session_agent,
            self.download_agent,
            self.ui_agent,
        ]

    def start_all(self):
        """모든 에이전트 시작"""
        print("[AgentManager] Starting all agents...")
        for agent in self._agents:
            agent.start()
        print("[AgentManager] All agents started")

    def stop_all(self):
        """모든 에이전트 중지"""
        print("[AgentManager] Stopping all agents...")
        for agent in self._agents:
            agent.stop()
        print("[AgentManager] All agents stopped")

    def set_browser_refs(self, browser, context, page):
        """브라우저 참조 설정"""
        self.browser_agent.set_browser_refs(browser, context, page)
        self.session_agent.set_context(context, page)

    def clear_browser_refs(self):
        """브라우저 참조 클리어"""
        self.browser_agent.clear_browser_refs()
        self.session_agent.set_context(None, None)

    def get_status(self) -> dict:
        """현재 상태 반환"""
        return self.ui_agent.get_status_for_api()

    def update_state(self, **kwargs):
        """상태 업데이트"""
        self.shared_state.update(kwargs)

    def get_state(self, key: str, default=None):
        """상태 조회"""
        return self.shared_state.get(key, default)


# 테스트
if __name__ == "__main__":
    print("Testing SubAgents...")

    manager = AgentManager()
    manager.start_all()

    # 상태 변경 테스트
    manager.update_state(logged_in=True, message="Test message")
    time.sleep(2)

    print("Status:", manager.get_status())

    manager.stop_all()
    print("Test complete")
