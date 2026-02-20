"""
Test script to capture campaign detail page structure
This will help us understand how to extract creator usernames
"""

import asyncio
import pickle
from pathlib import Path
from playwright.async_api import async_playwright

COBRAND_URL = "https://music.cobrand.com"
COOKIES_FILE = Path("automation/cobrand_cookies.pkl")


async def load_cookies(context):
    """Load saved cookies"""
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, 'rb') as f:
            cookies = pickle.load(f)
        await context.add_cookies(cookies)
        return True
    return False


async def main():
    print("\n" + "=" * 60)
    print("CAMPAIGN DETAIL PAGE TEST")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        page = await context.new_page()

        # Load cookies
        if not await load_cookies(context):
            print("[ERROR] No cookies found. Run cobrand_browser_test.py first.")
            await browser.close()
            return

        print("[INFO] Logging in with saved cookies...")
        await page.goto(f"{COBRAND_URL}/promote")
        await page.wait_for_timeout(3000)

        # Check login
        if "login" in page.url.lower():
            print("[ERROR] Cookies expired. Please re-login.")
            await browser.close()
            return

        print("[OK] Logged in successfully!")

        # Take screenshot of promotions list
        await page.screenshot(path="automation/step1_promotions_list.png")
        print("[OK] Screenshot 1: Promotions list")

        # Try to find and click the first promotion link
        print("\n[INFO] Looking for first promotion...")

        try:
            # Look for promotion links - try different selectors
            first_promo = await page.query_selector('a[href*="/promote/"]')

            if first_promo:
                promo_text = await first_promo.text_content()
                print(f"[INFO] Found promotion: {promo_text.strip()}")

                # Click it
                await first_promo.click()
                await page.wait_for_timeout(3000)

                # Take screenshot of campaign detail page
                await page.screenshot(path="automation/step2_campaign_detail.png")
                print("[OK] Screenshot 2: Campaign detail page")

                # Extract all text content for analysis
                page_content = await page.content()

                # Save HTML for inspection
                with open("automation/campaign_detail.html", 'w', encoding='utf-8') as f:
                    f.write(page_content)
                print("[OK] Saved HTML to campaign_detail.html")

                # Try to extract visible text
                body = await page.query_selector('body')
                if body:
                    all_text = await body.text_content()
                    with open("automation/campaign_detail_text.txt", 'w', encoding='utf-8') as f:
                        f.write(all_text)
                    print("[OK] Saved text content to campaign_detail_text.txt")

            else:
                print("[WARN] Could not find promotion link")

        except Exception as e:
            print(f"[ERROR] Failed to navigate: {e}")

        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        print("\nFiles created:")
        print("- step1_promotions_list.png")
        print("- step2_campaign_detail.png")
        print("- campaign_detail.html")
        print("- campaign_detail_text.txt")

        input("\nPress ENTER to close browser...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
