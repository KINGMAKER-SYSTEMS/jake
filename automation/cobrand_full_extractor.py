"""
Cobrand Full Campaign Extractor
Extracts all active campaigns (without green checkmarks) from Cobrand
"""

import asyncio
import json
import pickle
from pathlib import Path
from playwright.async_api import async_playwright

# Configuration
COBRAND_URL = "https://music.cobrand.com"
COOKIES_FILE = Path("automation/cobrand_cookies.pkl")
MAX_PAGES_TO_SCAN = 4  # Scan first 4 pages
GREEN_CHECK_EMOJI = "✅"


async def load_cookies(context):
    """Load saved cookies to bypass login"""
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, 'rb') as f:
            cookies = pickle.load(f)
        await context.add_cookies(cookies)
        print(f"[OK] Loaded cookies from {COOKIES_FILE}")
        return True
    return False


async def scan_promotions_page(page, page_num):
    """
    Scan a single page of promotions
    Returns list of promotions without green checkmarks
    """
    print(f"\n[INFO] Scanning page {page_num}...")

    # Wait for page to load
    await page.wait_for_timeout(2000)

    # Take screenshot for debugging
    screenshot_path = Path(f"automation/page_{page_num}_screenshot.png")
    await page.screenshot(path=screenshot_path)
    print(f"[OK] Screenshot saved: {screenshot_path}")

    # Extract all promotion rows
    promotions = []

    try:
        # Find all promotion rows in the table
        rows = await page.query_selector_all('tr')

        for row in rows:
            try:
                # Get the text content of the row
                text = await row.text_content()

                if not text or 'Promotions' in text or 'Profile' in text:
                    # Skip header rows
                    continue

                # Look for promotion name pattern (contains "Promo" or "Campaign")
                if 'Promo' in text or 'Campaign' in text:
                    # Check if it has a green checkmark
                    has_green_check = GREEN_CHECK_EMOJI in text or '✓' in text

                    # Try to extract the promotion link
                    link_element = await row.query_selector('a')
                    if link_element:
                        href = await link_element.get_attribute('href')
                        promo_text = await link_element.text_content()

                        promotions.append({
                            'name': promo_text.strip(),
                            'url': href,
                            'has_green_check': has_green_check,
                            'page': page_num,
                            'full_text': text.strip()[:200]  # First 200 chars for context
                        })
            except Exception as e:
                continue

        print(f"[OK] Found {len(promotions)} promotions on page {page_num}")

        # Filter to only non-green promotions
        active_promos = [p for p in promotions if not p['has_green_check']]
        green_promos = [p for p in promotions if p['has_green_check']]

        print(f"[INFO] Active (no green check): {len(active_promos)}")
        print(f"[INFO] Completed (green check): {len(green_promos)}")

        return active_promos, len(green_promos)

    except Exception as e:
        print(f"[ERROR] Failed to extract promotions: {e}")
        return [], 0


async def extract_creators_from_promotion(page, promotion_url, promotion_name):
    """
    Click into a promotion and extract the creator list
    Returns list of creator usernames
    """
    print(f"\n[INFO] Extracting creators from: {promotion_name}")

    try:
        # Navigate to the promotion detail page
        await page.goto(f"{COBRAND_URL}{promotion_url}")
        await page.wait_for_timeout(3000)

        # Take screenshot
        safe_name = promotion_name.replace('/', '-').replace('"', '')[:50]
        screenshot_path = Path(f"automation/promo_{safe_name}.png")
        await page.screenshot(path=screenshot_path)

        creators = []

        # Try to find creator elements
        # Based on the screenshots, creators are in rows with account names
        creator_rows = await page.query_selector_all('tr')

        for row in creator_rows:
            try:
                text = await row.text_content()

                # Look for patterns that indicate creator rows
                # They typically have usernames and post counts like "3/6"
                if '/' in text and any(keyword in text.lower() for keyword in ['post', 'live', 'need']):
                    # Try to extract username
                    # This is a heuristic - we'll refine based on actual structure
                    cells = await row.query_selector_all('td')

                    for cell in cells:
                        cell_text = await cell.text_content()
                        cell_text = cell_text.strip()

                        # Look for usernames (typically no spaces, may have @ or _)
                        if cell_text and len(cell_text) > 2 and len(cell_text) < 30:
                            # Could be a username
                            if '@' in cell_text or '_' in cell_text or cell_text.islower():
                                creators.append({
                                    'username': cell_text.replace('@', ''),
                                    'source': 'cell_extraction',
                                    'row_context': text[:100]
                                })
                                break
            except:
                continue

        print(f"[OK] Found {len(creators)} potential creators")

        # Remove duplicates
        unique_creators = []
        seen = set()
        for c in creators:
            if c['username'] not in seen:
                seen.add(c['username'])
                unique_creators.append(c)

        return unique_creators

    except Exception as e:
        print(f"[ERROR] Failed to extract creators: {e}")
        return []


async def main():
    """Main automation flow"""
    print("\n" + "=" * 60)
    print("COBRAND FULL CAMPAIGN EXTRACTOR")
    print("=" * 60)

    all_active_campaigns = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='en-US',
            timezone_id='America/Los_Angeles'
        )

        page = await context.new_page()

        # Load cookies and navigate to Cobrand
        cookies_loaded = await load_cookies(context)

        if not cookies_loaded:
            print("[ERROR] No cookies found. Please run cobrand_browser_test.py first to login.")
            await browser.close()
            return

        print("\n[INFO] Logging in with saved cookies...")
        await page.goto(f"{COBRAND_URL}/promote")
        await page.wait_for_timeout(3000)

        # Check if login worked
        if "login" in page.url.lower():
            print("[ERROR] Cookies expired. Please run cobrand_browser_test.py to re-login.")
            await browser.close()
            return

        print("[OK] Successfully logged in!")

        # Scan multiple pages
        for page_num in range(1, MAX_PAGES_TO_SCAN + 1):
            # If not on page 1, navigate to the next page
            if page_num > 1:
                # TODO: Implement pagination clicking
                # For now, we'll just scan page 1
                print(f"[INFO] Pagination not yet implemented - only scanning page 1")
                break

            active_promos, green_count = await scan_promotions_page(page, page_num)

            # If more than 70% of the page is green, stop scanning
            total_promos = len(active_promos) + green_count
            if total_promos > 0 and (green_count / total_promos) > 0.7:
                print(f"\n[INFO] Page {page_num} is mostly complete (>70% green) - stopping scan")
                break

            # Extract creators from each active promotion
            for promo in active_promos[:5]:  # Limit to first 5 for testing
                creators = await extract_creators_from_promotion(
                    page,
                    promo['url'],
                    promo['name']
                )

                promo['creators'] = creators
                all_active_campaigns.append(promo)

                # Wait a bit between promotions
                await page.wait_for_timeout(1000)

        # Save results
        output_file = Path("automation/active_campaigns.json")
        with open(output_file, 'w') as f:
            json.dump(all_active_campaigns, f, indent=2)

        print("\n" + "=" * 60)
        print("EXTRACTION COMPLETE!")
        print("=" * 60)
        print(f"\n[OK] Results saved to {output_file}")
        print(f"\nFound {len(all_active_campaigns)} active campaigns")

        for campaign in all_active_campaigns:
            print(f"\n- {campaign['name']}")
            print(f"  Creators found: {len(campaign.get('creators', []))}")

        input("\nPress ENTER to close browser...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
