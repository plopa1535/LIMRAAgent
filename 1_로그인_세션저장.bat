@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================================
echo LIMRA 수동 로그인 및 세션 저장
echo ============================================================
echo.
echo 브라우저가 열리면:
echo   1. 이메일 입력
echo   2. CAPTCHA 체크박스 클릭
echo   3. Next 버튼 클릭
echo   4. 비밀번호 입력 후 로그인
echo.
echo 로그인 완료되면 자동으로 세션이 저장됩니다.
echo ============================================================
echo.

python manual_login_save_session.py

echo.
pause
