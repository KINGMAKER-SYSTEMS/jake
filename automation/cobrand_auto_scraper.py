"""
Cobrand Auto Scraper - Complete Automation
Extracts incomplete campaigns and runs your scrapers automatically
"""

import asyncio
import json
import pickle
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

# Configuration
COBRAND_URL = "https://music.cobrand.com"
COOKIES_FILE = Path("automation/cobrand_cookies.pkl")
GREEN_CHECK = "✅"
OUTPUT_DIR = Path("automation/output")
OUTPUT_DIR.mkdir(exist_ok=True)


async def load_cookies(context):
    """Load saved cookies"""
    if COOKIES_FILE.exists():
        with open(COOKIES_FILE, 'rb') as f:
            cookies = pickle.load(f)
        await context.add_cookies(cookies)
        return True
    return False


async def scan_promotions_page(page, page_num):
    """
    Scan a single promotions page
    Returns: (active_promotions, green_check_count)
    """
    print(f"\n[INFO] Scanning promotions page {page_num}...")

    await page.wait_for_timeout(2000)

    # Take screenshot for debugging
    screenshot = OUTPUT_DIR / f"page_{page_num}_promotions.png"
    await page.screenshot(path=screenshot)
    print(f"[DEBUG] Screenshot: {screenshot}")

    promotions = []
    green_count = 0

    try:
        # Look specifically for the promotions table
        table = await page.query_selector('table')

        if not table:
            print(f"[WARN] Could not find promotions table")
            return [], 0

        rows = await table.query_selector_all('tbody tr')

        for row in rows:
            try:
                # Find the first link in the row (the promotion name)
                link = await row.query_selector('a')

                if not link:
                    continue

                link_text = await link.text_content()
                href = await link.get_attribute('href')

                if not link_text or not href:
                    continue

                link_text = link_text.strip()

                # ONLY look for links that contain "Promo" in the text
                # This matches: "JYT 'Say Less' Promo", "Bobby Uncle 'Kiss Me' Promo", etc.
                if 'Promo' not in link_text:
                    continue

                # Must have /promote/ in URL
                if '/promote/' not in href:
                    continue

                promo_name = link_text

                # Check for green checkmark
                has_green = GREEN_CHECK in promo_name or '✓' in promo_name

                if has_green:
                    green_count += 1
                    print(f"  [SKIP] {promo_name} (has green check)")
                else:
                    # Make sure we don't add duplicates
                    if not any(p['name'] == promo_name for p in promotions):
                        promotions.append({
                            'name': promo_name,
                            'url': href,
                            'page': page_num
                        })
                        print(f"  [ACTIVE] {promo_name}")

            except Exception as e:
                continue

        print(f"[OK] Page {page_num}: {len(promotions)} active, {green_count} completed")

        return promotions, green_count

    except Exception as e:
        print(f"[ERROR] Failed to scan page {page_num}: {e}")
        return [], 0


async def extract_campaigns_from_promotion(page, promotion_name, promotion_url):
    """
    Navigate to promotion and extract incomplete campaigns
    Returns: list of campaigns with creators needing posts
    """
    print(f"\n[INFO] Checking promotion: {promotion_name}")

    try:
        # Navigate to promotion - the creator table loads automatically
        full_url = f"{COBRAND_URL}{promotion_url}"
        print(f"  [INFO] Navigating to {full_url}")
        await page.goto(full_url, wait_until='networkidle')
        await page.wait_for_timeout(3000)  # Wait for page to fully load

        # Wait for creator table to be visible
        try:
            await page.wait_for_selector('table', timeout=10000)
            print("  [OK] Found creator table")
        except Exception as e:
            print(f"  [WARN] Could not find table: {e}")
            # Take debug screenshot
            await page.screenshot(path=OUTPUT_DIR / f"debug_no_table_{promotion_name[:20]}.png")
            return []

        # Scroll to see more content if needed
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await page.wait_for_timeout(1000)

        # Take screenshot AFTER scrolling
        safe_name = promotion_name.replace('/', '-').replace('"', '').replace("'", '')[:40]
        screenshot = OUTPUT_DIR / f"promo_{safe_name}.png"
        await page.screenshot(path=screenshot, full_page=True)  # Full page screenshot

        incomplete_creators = []

        # Loop through all pages of creators
        creator_page = 1
        max_creator_pages = 10  # Safety limit

        while creator_page <= max_creator_pages:
            print(f"  [INFO] Scanning creator page {creator_page}...")

            # Look for "Live Post" status showing X/Y format
            rows = await page.query_selector_all('table tbody tr')
            print(f"  [DEBUG] Found {len(rows)} rows in table")

            found_on_page = 0

            for idx, row in enumerate(rows):
                try:
                    row_text = await row.text_content()

                    # Debug: print first few rows to see format
                    if idx < 3:
                        print(f"  [DEBUG] Row {idx}: {row_text[:200]}")

                    # Look for Live Post pattern with (X/Y) format
                    # Example: "Live Post (2/2)" or "Live Post (10/18)"
                    import re

                    # First check if row has "Live Post" text
                    if 'Live Post' not in row_text:
                        continue

                    # Extract the post count - look for pattern (X/Y)
                    match = re.search(r'Live Post[^\d]*\((\d+)/(\d+)\)', row_text)

                    if match:
                        current = int(match.group(1))
                        total = int(match.group(2))
                        print(f"  [DEBUG] Found post count: {current}/{total}")

                        if current < total:  # Incomplete!
                            # Extract username - look for @ symbol followed by username
                            # Example: "@lifecontent1" or "@thedailbacker"
                            username_match = re.search(r'@([a-zA-Z0-9_\.]+)', row_text)

                            if username_match:
                                username = username_match.group(1)
                                print(f"  [DEBUG] Extracted username: @{username}")

                                # Check for duplicates
                                if not any(c['username'] == username for c in incomplete_creators):
                                    incomplete_creators.append({
                                        'username': username,
                                        'posts_current': current,
                                        'posts_needed': total,
                                        'posts_remaining': total - current,
                                        'promotion': promotion_name,
                                        'row_context': row_text[:200]
                                    })

                                    print(f"  [FOUND] @{username} needs {total - current} more posts ({current}/{total})")
                                    found_on_page += 1
                            else:
                                print(f"  [DEBUG] No @ username found in row with incomplete posts")
                                print(f"  [DEBUG] Row snippet: {row_text[:150]}")
                        else:
                            print(f"  [DEBUG] Row has complete posts ({current}/{total})")

                except Exception as e:
                    print(f"  [DEBUG] Error processing row {idx}: {e}")
                    continue

            # Try to find "Next" button for creator pagination
            try:
                next_button = await page.query_selector('[aria-label="Next page"]')
                if not next_button:
                    next_button = await page.query_selector('button:has-text("›")')
                if not next_button:
                    # Try finding by text
                    next_button = await page.query_selector('text=Next')

                if next_button:
                    # Check if it's disabled
                    is_disabled = await next_button.get_attribute('disabled')
                    if is_disabled:
                        print(f"  [INFO] No more creator pages")
                        break

                    await next_button.click()
                    await page.wait_for_timeout(2000)
                    creator_page += 1
                else:
                    print(f"  [INFO] No more creator pages")
                    break

            except Exception as e:
                print(f"  [INFO] No pagination found or end of creators")
                break

        if not incomplete_creators:
            print(f"  [OK] All campaigns complete in this promotion")

        return incomplete_creators

    except Exception as e:
        print(f"[ERROR] Failed to extract from {promotion_name}: {e}")
        return []


async def navigate_to_next_page(page, current_page):
    """
    Click the next page button
    Returns: True if successful, False if no more pages
    """
    try:
        # Look for "Page X" text and next arrow
        next_button = await page.query_selector('[aria-label="Next page"]')

        if not next_button:
            # Try finding by text
            next_button = await page.query_selector('text=›')

        if next_button:
            await next_button.click()
            await page.wait_for_timeout(2000)
            return True
        else:
            return False

    except Exception as e:
        print(f"[WARN] Could not navigate to next page: {e}")
        return False


async def main():
    """Main automation flow"""
    print("\n" + "=" * 60)
    print("COBRAND AUTO SCRAPER")
    print("=" * 60)

    all_incomplete_creators = []
    promotions_scanned = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=500)

        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )

        page = await context.new_page()

        # Login
        if not await load_cookies(context):
            print("[ERROR] No cookies. Run cobrand_browser_test.py first to login.")
            await browser.close()
            return

        print("\n[INFO] Logging in to Cobrand...")
        await page.goto(f"{COBRAND_URL}/promote", wait_until='domcontentloaded')
        await page.wait_for_timeout(4000)  # Give it time to load

        # Simple check: if we see "Sign in" button, we're NOT logged in
        sign_in_button = await page.query_selector('button:has-text("Sign in"), button:has-text("Log in")')

        if sign_in_button:
            print("[ERROR] Not logged in. Cookies may have expired.")
            print("[INFO] Please run: python automation/cobrand_browser_test.py")
            await page.screenshot(path=OUTPUT_DIR / "debug_login_failed.png")
            await browser.close()
            return

        print("[OK] Logged in successfully!")
        print(f"[DEBUG] Current URL: {page.url}")

        # Automatic profile switching
        print("\n" + "=" * 60)
        print("PROFILE SWITCHING")
        print("=" * 60)

        try:
            # Click the profile dropdown in top right
            # Look for text containing the current profile name (Johnny Balik or Rising Tides)
            print("\n[INFO] Looking for profile dropdown...")

            # Try to find the profile button - it might have the org name
            profile_button = await page.query_selector('button:has-text("Rising Tides")')

            if not profile_button:
                # Try looking for any button in the header area that might be the profile
                profile_button = await page.query_selector('header button')

            if not profile_button:
                # Last resort - look for text with profile names
                profile_button = await page.query_selector('text=/Johnny Balik|Rising Tides|No Organization/')

            if profile_button:
                print("[INFO] Found profile dropdown, clicking...")
                await profile_button.click()
                await page.wait_for_timeout(1500)
                print("[OK] Opened profile menu")

                # Now click "Rising Tides" in the dropdown
                print("[INFO] Looking for 'Rising Tides' option...")
                rising_tides = await page.query_selector('text="Rising Tides"')

                if rising_tides:
                    print("[INFO] Clicking 'Rising Tides'...")
                    await rising_tides.click()
                    await page.wait_for_timeout(2000)
                    print("[OK] Switched to Rising Tides profile!")
                else:
                    print("[WARN] Could not find 'Rising Tides' option in dropdown")
                    print("[INFO] Continuing anyway - you may already be on the right profile")
            else:
                print("[WARN] Could not find profile dropdown")
                print("[INFO] Continuing anyway - you may already be on Rising Tides")

        except Exception as e:
            print(f"[WARN] Profile switching failed: {e}")
            print("[INFO] Continuing anyway...")

        # Navigate to Promotions page
        print("\n[INFO] Navigating to Promotions page...")
        await page.goto(f"{COBRAND_URL}/promote")
        await page.wait_for_timeout(2000)
        print("[OK] On Promotions page!")

        # Scan pages until we hit a fully green page
        page_num = 1
        max_pages = 10  # Safety limit

        while page_num <= max_pages:
            # Scan current page
            active_promos, green_count = await scan_promotions_page(page, page_num)

            # Calculate if page is mostly green (70% threshold)
            total_promos = len(active_promos) + green_count
            if total_promos > 0:
                green_percentage = green_count / total_promos
                print(f"[INFO] Page {page_num}: {green_percentage:.0%} complete")

                # Stop if entire page is green
                if green_percentage >= 0.95:
                    print(f"[INFO] Page {page_num} is fully complete - stopping scan")
                    break

            # Extract campaigns from each active promotion
            for promo in active_promos[:10]:  # Limit to first 10 per page for safety
                creators = await extract_campaigns_from_promotion(
                    page,
                    promo['name'],
                    promo['url']
                )

                for creator in creators:
                    all_incomplete_creators.append(creator)

                promotions_scanned += 1

                # Go back to promotions list
                await page.goto(f"{COBRAND_URL}/promote")
                await page.wait_for_timeout(2000)

            # Try to go to next page
            if not await navigate_to_next_page(page, page_num):
                print(f"[INFO] No more pages to scan")
                break

            page_num += 1

        # Save results
        results_file = OUTPUT_DIR / f"incomplete_creators_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(all_incomplete_creators, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("SCAN COMPLETE")
        print("=" * 60)
        print(f"\nPromotions scanned: {promotions_scanned}")
        print(f"Creators needing posts: {len(all_incomplete_creators)}")
        print(f"\nResults saved to: {results_file}")

        # Display results
        if all_incomplete_creators:
            print("\n" + "=" * 60)
            print("CREATORS TO SCRAPE:")
            print("=" * 60)

            for creator in all_incomplete_creators:
                print(f"\n@{creator['username']}")
                print(f"  Campaign: {creator['promotion']}")
                print(f"  Status: {creator['posts_current']}/{creator['posts_needed']} posts")
                print(f"  Need: {creator['posts_remaining']} more post(s)")

            # Create simple username list for scraping
            usernames_file = OUTPUT_DIR / "usernames_to_scrape.txt"
            with open(usernames_file, 'w') as f:
                for creator in all_incomplete_creators:
                    f.write(f"{creator['username']}\n")

            print(f"\n[OK] Username list saved to: {usernames_file}")
            print("\nNext step: Run your scrapers on these accounts!")

        else:
            print("\n[INFO] All campaigns are complete! No scraping needed.")

        input("\nPress ENTER to close browser...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
