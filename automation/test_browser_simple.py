"""
Simple browser test - just opens browser to verify Playwright works
Run this directly in your terminal: python automation/test_browser_simple.py
"""

import asyncio
from playwright.async_api import async_playwright

async def main():
    print("\n" + "=" * 60)
    print("SIMPLE BROWSER TEST")
    print("=" * 60)
    print("\nStarting browser...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        print("Opening Cobrand...")
        await page.goto("https://music.cobrand.com")

        print("\nBrowser is open! You should see Cobrand login page.")
        print("The browser will stay open for 30 seconds so you can see it.")

        await asyncio.sleep(30)

        print("\nClosing browser...")
        await browser.close()
        print("Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
