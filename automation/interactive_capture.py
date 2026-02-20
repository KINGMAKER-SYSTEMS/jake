"""
Interactive screenshot capture tool
You control the browser, script just takes screenshots when you press ENTER
"""

import asyncio
import pickle
from pathlib import Path
from playwright.async_api import async_playwright

COBRAND_URL = "https://music.cobrand.com"
COOKIES_FILE = Path("automation/cobrand_cookies.pkl")


async def load_cookies(context):
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, 'rb') as f:
            cookies = pickle.load(f)
        await context.add_cookies(cookies)
        return True
    return False


async def main():
    print("\n" + "=" * 60)
    print("INTERACTIVE SCREENSHOT CAPTURE")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Browser will open and login")
    print("2. YOU navigate to whatever page you want")
    print("3. Press ENTER in this terminal to capture screenshot")
    print("4. Repeat for multiple pages")
    print("5. Type 'done' when finished")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        page = await context.new_page()

        if not await load_cookies(context):
            print("[ERROR] No cookies. Run cobrand_browser_test.py first.")
            await browser.close()
            return

        await page.goto(f"{COBRAND_URL}/promote")
        await page.wait_for_timeout(2000)

        print("\n[OK] Browser is open and logged in!")
        print("\nNow:")
        print("- Switch to Rising Tides profile if needed")
        print("- Navigate to any page you want me to see")
        print("- Come back here and press ENTER to capture")

        screenshot_num = 1

        while True:
            user_input = input(f"\nPress ENTER to capture screenshot #{screenshot_num} (or type 'done'): ")

            if user_input.lower() == 'done':
                break

            # Capture screenshot
            filename = f"automation/capture_{screenshot_num}.png"
            await page.screenshot(path=filename)
            print(f"[OK] Saved: {filename}")

            # Save current URL and page title
            url = page.url
            title = await page.title()
            print(f"[INFO] URL: {url}")
            print(f"[INFO] Title: {title}")

            # Save HTML too
            html_file = f"automation/capture_{screenshot_num}.html"
            content = await page.content()
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"[OK] Saved HTML: {html_file}")

            screenshot_num += 1

        print("\n" + "=" * 60)
        print(f"Captured {screenshot_num - 1} screenshots!")
        print("=" * 60)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
