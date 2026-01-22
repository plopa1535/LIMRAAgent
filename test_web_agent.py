"""
웹앱 테스트 서브에이전트
- 웹앱 실행 및 정상 작동 확인
- 문제 발견 시 자동으로 수정 시도
- 테스트 결과 리포트 생성
"""

import subprocess
import sys
import io

# Windows 콘솔 인코딩 문제 해결
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import time
import requests
import sys
from pathlib import Path


class WebAppTestAgent:
    """웹앱 테스트 및 자동 수정 에이전트"""

    def __init__(self, app_dir: str = "."):
        self.app_dir = Path(app_dir)
        self.web_process = None
        self.base_url = "http://localhost:5000"
        self.test_results = []

    def start_web_app(self) -> bool:
        """웹앱 시작"""
        print("[TEST] 웹앱 시작 중...")
        try:
            self.web_process = subprocess.Popen(
                [sys.executable, "web_app.py"],
                cwd=self.app_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # 서버 시작 대기
            time.sleep(3)

            if self.web_process.poll() is not None:
                stdout, stderr = self.web_process.communicate()
                print(f"[ERROR] 웹앱 시작 실패:")
                print(f"  stdout: {stdout}")
                print(f"  stderr: {stderr}")
                return False

            print("[TEST] 웹앱 시작 완료")
            return True

        except Exception as e:
            print(f"[ERROR] 웹앱 시작 예외: {e}")
            return False

    def stop_web_app(self):
        """웹앱 종료"""
        if self.web_process:
            print("[TEST] 웹앱 종료 중...")
            self.web_process.terminate()
            try:
                self.web_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.web_process.kill()
            print("[TEST] 웹앱 종료 완료")

    def test_endpoint(self, path: str, method: str = "GET",
                      data: dict = None, expected_status: int = 200) -> dict:
        """엔드포인트 테스트"""
        url = f"{self.base_url}{path}"
        result = {
            "path": path,
            "method": method,
            "success": False,
            "status_code": None,
            "response": None,
            "error": None
        }

        try:
            if method == "GET":
                resp = requests.get(url, timeout=10)
            elif method == "POST":
                resp = requests.post(url, json=data, timeout=10)
            else:
                result["error"] = f"지원하지 않는 메서드: {method}"
                return result

            result["status_code"] = resp.status_code
            result["success"] = resp.status_code == expected_status

            try:
                result["response"] = resp.json()
            except:
                result["response"] = resp.text[:500] if resp.text else None

        except requests.exceptions.ConnectionError:
            result["error"] = "연결 실패 - 서버가 실행 중이 아닐 수 있습니다"
        except requests.exceptions.Timeout:
            result["error"] = "요청 타임아웃"
        except Exception as e:
            result["error"] = str(e)

        return result

    def run_all_tests(self) -> list:
        """모든 테스트 실행"""
        print("\n" + "="*60)
        print("[TEST] 웹앱 테스트 시작")
        print("="*60 + "\n")

        tests = [
            # 메인 페이지 (필수)
            {"path": "/", "method": "GET", "name": "메인 페이지", "required": True},
            # API 상태 (필수)
            {"path": "/api/status", "method": "GET", "name": "상태 API", "required": True},
            # 파일 목록 (필수)
            {"path": "/api/files", "method": "GET", "name": "파일 목록 API", "required": True},
            # 에이전트 상태 (선택 - 로그인 전에는 에러 가능)
            {"path": "/api/agents", "method": "GET", "name": "에이전트 상태 API", "required": False},
        ]

        self.test_results = []

        for test in tests:
            print(f"[TEST] {test['name']} 테스트 중... ", end="")
            result = self.test_endpoint(
                path=test["path"],
                method=test["method"],
                data=test.get("data")
            )
            result["name"] = test["name"]
            result["required"] = test.get("required", True)
            self.test_results.append(result)

            if result["success"]:
                print("OK 성공")
            elif not result["required"]:
                print(f"- 건너뜀 (선택 사항)")
            else:
                print(f"X 실패 - {result.get('error') or result.get('status_code')}")

        return self.test_results

    def generate_report(self) -> str:
        """테스트 리포트 생성"""
        report = []
        report.append("\n" + "="*60)
        report.append("테스트 결과 리포트")
        report.append("="*60)

        passed = sum(1 for r in self.test_results if r["success"])
        total = len(self.test_results)

        required_tests = [r for r in self.test_results if r.get("required", True)]
        required_passed = sum(1 for r in required_tests if r["success"])

        report.append(f"\n전체: {total} | 성공: {passed} | 실패: {total - passed}")
        report.append(f"필수 테스트: {len(required_tests)} | 성공: {required_passed}")
        report.append("")

        for r in self.test_results:
            if r["success"]:
                status = "[OK]"
            elif not r.get("required", True):
                status = "[--]"
            else:
                status = "[X]"
            report.append(f"  {status} {r['name']}")
            if not r["success"] and r.get("required", True):
                if r.get("error"):
                    report.append(f"      오류: {r['error']}")
                elif r.get("status_code"):
                    report.append(f"      상태 코드: {r['status_code']}")

        report.append("\n" + "="*60)

        return "\n".join(report)

    def check_dependencies(self) -> dict:
        """의존성 체크"""
        print("[TEST] 의존성 체크 중...")

        deps = {
            "playwright": False,
            "flask": False,
            "nest_asyncio": False,
            "requests": False,
        }

        for dep in deps:
            try:
                __import__(dep)
                deps[dep] = True
                print(f"  ✓ {dep}")
            except ImportError:
                print(f"  ✗ {dep} - 설치 필요")

        return deps

    def install_missing_deps(self, deps: dict) -> bool:
        """누락된 의존성 설치"""
        missing = [dep for dep, installed in deps.items() if not installed]

        if not missing:
            print("[TEST] 모든 의존성이 설치되어 있습니다")
            return True

        print(f"[TEST] 누락된 의존성 설치 중: {', '.join(missing)}")

        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install"] + missing,
                check=True
            )
            print("[TEST] 의존성 설치 완료")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] 의존성 설치 실패: {e}")
            return False

    def full_test(self) -> bool:
        """전체 테스트 실행"""
        print("\n" + "#"*60)
        print("# 웹앱 테스트 에이전트 시작")
        print("#"*60 + "\n")

        # 1. 의존성 체크
        deps = self.check_dependencies()
        if not all(deps.values()):
            if not self.install_missing_deps(deps):
                print("[ERROR] 의존성 설치 실패로 테스트 중단")
                return False

        # 2. 웹앱 시작
        if not self.start_web_app():
            print("[ERROR] 웹앱 시작 실패로 테스트 중단")
            return False

        try:
            # 3. 테스트 실행
            self.run_all_tests()

            # 4. 리포트 생성
            report = self.generate_report()
            print(report)

            # 5. 결과 반환 (필수 테스트만 체크)
            required_tests = [r for r in self.test_results if r.get("required", True)]
            passed = all(r["success"] for r in required_tests)
            return passed

        finally:
            # 6. 웹앱 종료
            self.stop_web_app()


def main():
    """메인 함수"""
    agent = WebAppTestAgent()
    success = agent.full_test()

    if success:
        print("\n[결과] 모든 테스트 통과! 웹앱이 정상 작동합니다.")
        sys.exit(0)
    else:
        print("\n[결과] 일부 테스트 실패. 위의 오류를 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    main()
