"""
Cobrand Browser Automation - Proof of Concept
This script tests if we can automate Cobrand login and data extraction.

Features:
- First run: Opens browser for manual login, saves cookies
- Future runs: Auto-login using saved cookies
- Extracts campaign data from Cobrand Promotions page
"""

import asyncio
import json
import pickle
from pathlib import Path
from playwright.async_api import async_playwright

# Configuration
COBRAND_URL = "https://music.cobrand.com"
COOKIES_FILE = Path("automation/cobrand_cookies.pkl")
EMAIL = "jake@risingtidesent.com"


async def save_cookies(context):
    """Save browser cookies for session persistence"""
    cookies = await context.cookies()
    COOKIES_FILE.parent.mkdir(exist_ok=True)
    with open(COOKIES_FILE, 'wb') as f:
        pickle.dump(cookies, f)
    print(f"[OK] Cookies saved to {COOKIES_FILE}")


async def load_cookies(context):
    """Load saved cookies to bypass login"""
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, 'rb') as f:
            cookies = pickle.load(f)
        await context.add_cookies(cookies)
        print(f"[OK] Loaded cookies from {COOKIES_FILE}")
        return True
    return False


async def manual_login(page):
    """
    Opens browser for manual login
    User logs in, script saves the session
    """
    print("\n*** MANUAL LOGIN REQUIRED ***")
    print("=" * 60)
    print("1. A browser window will open")
    print("2. Please login to Cobrand manually")
    print("3. Once you see the Promotions page, come back here")
    print("4. Press ENTER in this terminal when ready")
    print("=" * 60)

    await page.goto(COBRAND_URL)

    # Wait for user to login manually
    input("\nPress ENTER after you've logged in and see the Promotions page... ")

    # Verify we're logged in by checking URL
    current_url = page.url
    if "cobrand.com" in current_url:
        print("[OK] Login successful!")
        return True
    else:
        print("[ERROR] Login may have failed. Please try again.")
        return False


async def extract_campaigns(page):
    """
    Extract campaign data from Cobrand Promotions page
    Returns list of campaigns with titles and status
    """
    print("\n[INFO] Extracting campaign data...")

    # Navigate to Promotions page if not already there
    if "/promote/" not in page.url:
        # Try to find and click Promotions link
        try:
            await page.click('text=Promotions', timeout=5000)
            await page.wait_for_load_state('networkidle')
        except:
            print("[WARN] Could not find Promotions link, may already be on correct page")

    # Wait for page to load
    await page.wait_for_timeout(2000)

    # Take screenshot for debugging
    screenshot_path = Path("automation/cobrand_screenshot.png")
    await page.screenshot(path=screenshot_path)
    print(f"[OK] Screenshot saved to {screenshot_path}")

    # Extract campaign titles - we'll need to inspect the HTML structure
    # This is a placeholder - we'll refine after seeing the actual page
    try:
        # Try to find campaign elements
        campaigns = await page.query_selector_all('[class*="promotion"], [class*="campaign"]')

        campaign_data = []
        for idx, campaign in enumerate(campaigns[:5]):  # Get first 5 for testing
            try:
                text_content = await campaign.text_content()
                campaign_data.append({
                    'index': idx,
                    'text': text_content.strip() if text_content else 'N/A'
                })
            except:
                continue

        print(f"\n[OK] Found {len(campaign_data)} campaigns")
        return campaign_data

    except Exception as e:
        print(f"[WARN] Could not extract campaigns: {e}")
        print("We'll refine the selectors after inspecting the page HTML")
        return []


async def main():
    """Main automation flow"""
    print("\n" + "=" * 60)
    print("COBRAND AUTOMATION - PROOF OF CONCEPT")
    print("=" * 60)

    async with async_playwright() as p:
        # Launch browser (visible mode for testing)
        browser = await p.chromium.launch(
            headless=False,  # Show browser for debugging
            slow_mo=500      # Slow down actions for visibility
        )

        # Create context with realistic settings (avoid bot detection)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/Los_Angeles'
        )

        page = await context.new_page()

        # Try to load saved cookies first
        cookies_loaded = await load_cookies(context)

        if cookies_loaded:
            print("\n[INFO] Attempting auto-login with saved cookies...")
            await page.goto(COBRAND_URL)
            await page.wait_for_timeout(3000)

            # Check if we're logged in
            if "login" in page.url.lower():
                print("[WARN] Cookies expired, need manual login")
                cookies_loaded = False

        # Manual login if needed
        if not cookies_loaded:
            login_success = await manual_login(page)
            if login_success:
                await save_cookies(context)
            else:
                print("[ERROR] Login failed, exiting...")
                await browser.close()
                return

        # Extract campaign data
        campaigns = await extract_campaigns(page)

        # Save results
        if campaigns:
            results_file = Path("automation/campaigns_extracted.json")
            with open(results_file, 'w') as f:
                json.dump(campaigns, f, indent=2)
            print(f"\n[OK] Results saved to {results_file}")

        # Display results
        print("\n" + "=" * 60)
        print("EXTRACTED CAMPAIGNS:")
        print("=" * 60)
        for campaign in campaigns:
            print(f"{campaign['index'] + 1}. {campaign['text'][:100]}")

        print("\n[SUCCESS] Proof of concept complete!")
        print("\nNext steps:")
        print("1. Inspect the screenshot and JSON to understand Cobrand's structure")
        print("2. Refine selectors to extract campaign titles and status emojis")
        print("3. Add creator extraction from campaign detail pages")

        # Keep browser open for inspection
        input("\nPress ENTER to close the browser... ")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
