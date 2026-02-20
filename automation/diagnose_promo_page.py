"""
Diagnostic script to see what's actually on a promotion detail page
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
    print("PROMOTION PAGE DIAGNOSTICS")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        page = await context.new_page()

        # Login
        if not await load_cookies(context):
            print("[ERROR] No cookies. Run cobrand_browser_test.py first.")
            await browser.close()
            return

        await page.goto(f"{COBRAND_URL}/promote")
        await page.wait_for_timeout(3000)

        print("\n[INFO] Browser is open")
        print("\nPlease:")
        print("1. Switch to Rising Tides profile")
        print("2. Click on ANY promotion (like 'JYT Say Less Promo')")
        print("3. Come back here and press ENTER")

        input("\nPress ENTER when you're on a promotion page... ")

        print("\n[INFO] Analyzing page...")
        await page.wait_for_timeout(2000)

        # Get current URL
        print(f"\n[INFO] Current URL: {page.url}")

        # Take initial screenshot
        await page.screenshot(path="automation/diag_initial.png")
        print("[OK] Screenshot 1: Initial page")

        # Find all links on the page
        print("\n" + "=" * 60)
        print("ALL LINKS ON PAGE:")
        print("=" * 60)
        links = await page.query_selector_all('a')
        for idx, link in enumerate(links[:20]):  # First 20 links
            try:
                text = await link.text_content()
                href = await link.get_attribute('href')
                if text and text.strip():
                    print(f"{idx+1}. '{text.strip()[:50]}' -> {href}")
            except:
                continue

        # Find all buttons
        print("\n" + "=" * 60)
        print("ALL BUTTONS ON PAGE:")
        print("=" * 60)
        buttons = await page.query_selector_all('button')
        for idx, button in enumerate(buttons[:20]):  # First 20 buttons
            try:
                text = await button.text_content()
                if text and text.strip():
                    print(f"{idx+1}. '{text.strip()[:50]}'")
            except:
                continue

        # Find all tables
        print("\n" + "=" * 60)
        print("ALL TABLES ON PAGE:")
        print("=" * 60)
        tables = await page.query_selector_all('table')
        print(f"Found {len(tables)} table(s)")

        for idx, table in enumerate(tables):
            try:
                rows = await table.query_selector_all('tr')
                print(f"\nTable {idx+1}: {len(rows)} rows")

                # Print first few rows
                for row_idx, row in enumerate(rows[:3]):
                    text = await row.text_content()
                    print(f"  Row {row_idx+1}: {text.strip()[:100]}")
            except:
                continue

        # Look for text containing "Campaign" or "Creator"
        print("\n" + "=" * 60)
        print("SEARCHING FOR 'CAMPAIGNS' OR 'CREATORS':")
        print("=" * 60)

        body = await page.query_selector('body')
        if body:
            body_text = await body.text_content()

            if 'Campaign' in body_text or 'campaign' in body_text:
                print("[FOUND] 'Campaign' appears in page text")
            else:
                print("[NOT FOUND] 'Campaign' does not appear")

            if 'Creator' in body_text or 'creator' in body_text:
                print("[FOUND] 'Creator' appears in page text")
            else:
                print("[NOT FOUND] 'Creator' does not appear")

        # Save full HTML
        content = await page.content()
        with open("automation/diag_page.html", 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n[OK] Saved full HTML to automation/diag_page.html")

        print("\n" + "=" * 60)
        print("DIAGNOSIS COMPLETE")
        print("=" * 60)
        print("\nFiles created:")
        print("- automation/diag_initial.png")
        print("- automation/diag_page.html")

        input("\nPress ENTER to close browser...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
