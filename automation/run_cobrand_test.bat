@echo off
cd /d "%~dp0.."
echo.
echo ============================================================
echo  Running Cobrand Browser Automation Test
echo ============================================================
echo.
python automation/cobrand_browser_test.py
pause
python automation\cobrand_browser_test.py
