"""
Simple Cobrand Scraper - Just keep browser open!
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

COBRAND_URL = "https://music.cobrand.com"
OUTPUT_DIR = Path("automation/output")
OUTPUT_DIR.mkdir(exist_ok=True)


async def main():
    print("\n" + "=" * 60)
    print("COBRAND SIMPLE SCRAPER")
    print("=" * 60)

    async with async_playwright() as p:
        # Launch browser and KEEP IT OPEN
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720}
        )
        page = await context.new_page()

        # Navigate to Cobrand
        print("\n[INFO] Opening Cobrand...")
        await page.goto(f"{COBRAND_URL}/promote")
        await page.wait_for_timeout(3000)

        # Let user login and switch profile
        print("\n" + "=" * 60)
        print("MANUAL SETUP")
        print("=" * 60)
        print("\nThe browser is now open.")
        print("\nPlease:")
        print("1. Log in if needed")
        print("2. Switch to Rising Tides profile")
        print("3. Navigate to the Promotions page")
        print("4. Come back here and press ENTER to start scanning")
        print("=" * 60)

        input("\nPress ENTER when ready... ")

        print("\n[INFO] Starting scan...")

        all_incomplete_creators = []

        # Scan pages until mostly green
        page_num = 1
        max_pages = 10

        while page_num <= max_pages:
            print(f"\n[INFO] Scanning promotions page {page_num}...")

            await page.wait_for_timeout(2000)

            # Find all promotion links
            rows = await page.query_selector_all('table tbody tr')
            print(f"[DEBUG] Found {len(rows)} rows in promotions table")

            # Debug: print first 3 rows to see what we're working with
            for idx in range(min(3, len(rows))):
                try:
                    debug_text = await rows[idx].text_content()
                    print(f"[DEBUG] Promo row {idx}: {debug_text[:200]}")
                except:
                    pass

            active_promos = []
            green_count = 0

            for row in rows:
                try:
                    link = await row.query_selector('a')
                    if not link:
                        continue

                    link_text = await link.text_content()
                    href = await link.get_attribute('href')

                    if not link_text or not href:
                        continue

                    link_text = link_text.strip()

                    # Only promo links
                    if 'Promo' not in link_text or '/promote/' not in href:
                        continue

                    # Check for green checkmark
                    if '✅' in link_text or '✓' in link_text:
                        green_count += 1
                        print(f"  [SKIP] {link_text}")
                    else:
                        active_promos.append({
                            'name': link_text,
                            'url': href
                        })
                        print(f"  [ACTIVE] {link_text}")

                except:
                    continue

            print(f"[OK] Page {page_num}: {len(active_promos)} active, {green_count} complete")

            # Stop if page is mostly green
            total = len(active_promos) + green_count
            if total > 0 and green_count / total >= 0.95:
                print(f"[INFO] Page {page_num} is 95%+ complete - stopping")
                break

            # Check each active promotion
            for promo in active_promos[:10]:  # Limit to first 10
                print(f"\n[INFO] Checking: {promo['name']}")

                # Navigate to promotion detail page
                await page.goto(f"{COBRAND_URL}{promo['url']}")
                await page.wait_for_timeout(4000)

                # Wait for the creator table to load
                try:
                    await page.wait_for_selector('table', timeout=8000)
                except:
                    print(f"  [WARN] No table found - skipping")
                    await page.goto(f"{COBRAND_URL}/promote")
                    await page.wait_for_timeout(2000)
                    continue

                # Find all creator rows
                creator_rows = await page.query_selector_all('table tbody tr')
                print(f"  [INFO] Scanning {len(creator_rows)} creators...")

                creators_found = 0
                import re

                # Debug: print first 3 rows to see actual format
                for idx in range(min(3, len(creator_rows))):
                    try:
                        debug_text = await creator_rows[idx].text_content()
                        print(f"  [DEBUG] Row {idx}: {debug_text[:250]}")
                    except:
                        pass

                for row in creator_rows:
                    try:
                        row_text = await row.text_content()

                        # Skip rows without Live Post status
                        if 'Live Post' not in row_text:
                            continue

                        print(f"  [DEBUG] Found 'Live Post' in row: {row_text[:150]}")

                        # Look for incomplete posts like "Live Post (9/10)"
                        match = re.search(r'Live Post[^\d]*\((\d+)/(\d+)\)', row_text)

                        if not match:
                            continue

                        current = int(match.group(1))
                        total = int(match.group(2))

                        # Only care about incomplete
                        if current >= total:
                            continue

                        # Extract username with @ symbol
                        username_match = re.search(r'@([a-zA-Z0-9_\.]+)', row_text)

                        if not username_match:
                            continue

                        username = username_match.group(1)

                        # Check for duplicates across all promotions
                        if any(c['username'] == username for c in all_incomplete_creators):
                            continue

                        # Add to results
                        all_incomplete_creators.append({
                            'username': username,
                            'posts_current': current,
                            'posts_needed': total,
                            'posts_remaining': total - current,
                            'promotion': promo['name']
                        })

                        print(f"  [FOUND] @{username} needs {total - current} more ({current}/{total})")
                        creators_found += 1

                    except Exception as e:
                        continue

                if creators_found == 0:
                    print(f"  [OK] All creators complete in this promotion")

                # Go back to promotions list
                await page.goto(f"{COBRAND_URL}/promote")
                await page.wait_for_timeout(2000)

            # Try to go to next page (if there is one)
            try:
                next_button = await page.query_selector('[aria-label="Next page"]')
                if next_button:
                    is_disabled = await next_button.get_attribute('disabled')
                    if not is_disabled:
                        await next_button.click()
                        await page.wait_for_timeout(2000)
                        page_num += 1
                        continue
            except:
                pass

            break

        # Save results
        results_file = OUTPUT_DIR / f"incomplete_creators_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(all_incomplete_creators, f, indent=2)

        # Print summary
        print("\n" + "=" * 60)
        print("SCAN COMPLETE!")
        print("=" * 60)
        print(f"\nFound {len(all_incomplete_creators)} creators needing posts")
        print(f"Results saved to: {results_file}")

        if all_incomplete_creators:
            print("\n" + "=" * 60)
            print("CREATORS TO SCRAPE:")
            print("=" * 60)
            for creator in all_incomplete_creators:
                print(f"\n@{creator['username']}")
                print(f"  Campaign: {creator['promotion']}")
                print(f"  Needs: {creator['posts_remaining']} more post(s)")

            # Save simple username list
            usernames_file = OUTPUT_DIR / "usernames_to_scrape.txt"
            with open(usernames_file, 'w') as f:
                for creator in all_incomplete_creators:
                    f.write(f"{creator['username']}\n")

            print(f"\n[OK] Username list: {usernames_file}")

        input("\nPress ENTER to close browser...")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
