@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================================
echo LIMRA Web App - 테스트 에이전트
echo ============================================================
echo.

python test_web_agent.py

echo.
pause
