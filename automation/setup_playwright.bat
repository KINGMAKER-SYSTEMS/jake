@echo off
echo ============================================================
echo  Installing Playwright for Cobrand Automation
echo ============================================================
echo.

echo Step 1: Installing Playwright Python package...
python -m pip install playwright

echo.
echo Step 2: Installing Playwright browsers (Chromium)...
python -m playwright install chromium

echo.
echo ============================================================
echo  Installation Complete!
echo ============================================================
echo.
echo You can now run: python automation/cobrand_browser_test.py
echo.
pause
