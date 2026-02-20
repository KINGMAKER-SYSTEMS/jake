"""
Cobrand Campaign Extractor
==========================
Extracts active campaigns and creator data from Cobrand using browser automation.
Generates per-campaign CSVs with creator progress.

Usage:
    python cobrand_campaign_extractor.py [--pages 4] [--output-dir ./output/campaigns]
"""

import asyncio
import json
import csv
import re
import sys
import io
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Try to import playwright
try:
    from playwright.async_api import async_playwright, Page
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

COBRAND_URL = "https://music.cobrand.com"
ORG_ID = "652c1528-f525-4c80-be5d-fda2aa6005fd"
OUTPUT_DIR = Path("output/campaigns")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GREEN_CHECK = "✅"
PAUSE_EMOJI = "⏸️"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Creator:
    """A creator booked for a campaign"""
    handle: str
    display_name: str
    status: str  # "Hired", "Live Post", "Paid", etc.
    posts_done: int
    posts_owed: int
    needs_scraping: bool
    price: Optional[float] = None
    email: Optional[str] = None
    platform: str = "tiktok"  # or "instagram"


@dataclass 
class Campaign:
    """A campaign/promotion from Cobrand"""
    name: str
    promo_id: str
    artist: str
    sound_name: Optional[str] = None
    sound_url: Optional[str] = None
    status: str = "Active"
    total_budget: float = 0
    spent: float = 0
    live_posts: int = 0
    creators: List[Creator] = None
    
    def __post_init__(self):
        if self.creators is None:
            self.creators = []


# =============================================================================
# EXTRACTION FUNCTIONS
# =============================================================================

async def wait_for_load(page: Page, timeout: int = 5000):
    """Wait for page to be reasonably loaded"""
    try:
        await page.wait_for_load_state('networkidle', timeout=timeout)
    except:
        await page.wait_for_timeout(2000)


async def extract_promotions_list(page: Page) -> List[dict]:
    """Extract promotion list from current page"""
    promotions = []
    
    # Wait for table to load
    await page.wait_for_selector('table', timeout=10000)
    await page.wait_for_timeout(1000)
    
    # Get all rows
    rows = await page.query_selector_all('table tbody tr, [role="row"]')
    
    for row in rows:
        try:
            row_text = await row.text_content()
            if not row_text:
                continue
                
            # Skip completed campaigns (green check)
            if GREEN_CHECK in row_text or '✓' in row_text:
                print(f"  [SKIP] Completed: {row_text[:50]}...")
                continue
            
            # Find the promotion link
            link = await row.query_selector('a[href*="/promote/"]')
            if not link:
                continue
                
            link_text = await link.text_content()
            href = await link.get_attribute('href')
            
            if not link_text or not href:
                continue
            
            # Extract promo ID from URL
            promo_id_match = re.search(r'/promote/([a-f0-9-]+)', href)
            if not promo_id_match:
                continue
                
            promo_id = promo_id_match.group(1)
            
            # Check for Promo in name (standard format)
            if 'Promo' not in link_text and 'Campaign' not in link_text:
                continue
            
            # Check for pause emoji (paused campaigns)
            is_paused = PAUSE_EMOJI in row_text
            
            promotions.append({
                'name': link_text.strip(),
                'promo_id': promo_id,
                'url': href,
                'is_paused': is_paused,
                'row_text': row_text[:200]
            })
            
            status = "[PAUSED]" if is_paused else "[ACTIVE]"
            print(f"  {status} {link_text.strip()[:50]}")
            
        except Exception as e:
            continue
    
    return promotions


async def extract_campaign_details(page: Page, promo: dict) -> Optional[Campaign]:
    """Navigate to a promotion and extract creator details"""
    
    print(f"\n[INFO] Extracting: {promo['name'][:50]}")
    
    try:
        # Navigate to promotion page
        full_url = f"{COBRAND_URL}{promo['url']}"
        await page.goto(full_url, wait_until='domcontentloaded')
        await wait_for_load(page, timeout=10000)
        
        # Wait for creator table to appear
        await page.wait_for_timeout(2000)
        
        # Extract campaign info
        campaign = Campaign(
            name=promo['name'],
            promo_id=promo['promo_id'],
            artist="",
            status="Paused" if promo.get('is_paused') else "Active"
        )
        
        # Try to find sound URL from the page
        sound_links = await page.query_selector_all('a[href*="tiktok.com/music"]')
        if sound_links:
            for link in sound_links:
                href = await link.get_attribute('href')
                text = await link.text_content()
                if href and 'music' in href:
                    campaign.sound_url = href
                    campaign.sound_name = text.strip() if text else None
                    break
        
        # Find creator rows
        # Look for rows with creator info (they have profile images and handles)
        creator_rows = await page.query_selector_all('[role="row"], table tbody tr')
        
        for row in creator_rows:
            try:
                row_text = await row.text_content()
                if not row_text:
                    continue
                
                # Skip header rows
                if 'Campaign Stage' in row_text or 'Campaign Price' in row_text:
                    continue
                
                # Look for creator handle pattern (usually has @ or is a username)
                # The row should have status like "Hired" or "Live Post (X/Y)"
                
                # Extract handle - look for the second occurrence of the name pattern
                # Format is usually: "DisplayName handle Note ..."
                
                # Find all text nodes that could be handles
                handle_elem = await row.query_selector('[class*="handle"], [class*="username"]')
                if not handle_elem:
                    # Try to find by pattern in row text
                    # Look for patterns like "lifecontent1" after a display name
                    pass
                
                # Parse status - look for "Hired", "Live Post (X/Y)", "Paid", etc.
                status_match = re.search(r'(Hired|Live Post(?:\s*\((\d+)/(\d+)\))?|Paid|Draft Ready|Negotiating|Outreached)', row_text)
                
                if not status_match:
                    continue
                
                status = status_match.group(0)
                posts_done = 0
                posts_owed = 0
                
                # Parse X/Y from "Live Post (X/Y)"
                if status_match.group(2) and status_match.group(3):
                    posts_done = int(status_match.group(2))
                    posts_owed = int(status_match.group(3))
                elif 'Hired' in status:
                    # Hired means 0 posts done, need to find expected
                    posts_match = re.search(r'(\d+)\s*Live\s*Posts?', row_text)
                    if posts_match:
                        posts_owed = int(posts_match.group(1))
                
                # Determine if needs scraping
                needs_scraping = posts_done < posts_owed or status == 'Hired'
                
                # Try to extract handle from row
                # Usually in format: "DisplayName username Note ..."
                # Look for TikTok-style handles
                handle_match = re.search(r'([a-zA-Z0-9_\.]{3,30})\s+(?:Note|Add Tags|Hired|Live Post)', row_text)
                if not handle_match:
                    # Try another pattern
                    handle_match = re.search(r'(?:^|\s)([a-zA-Z0-9_\.]{3,25})\s+(?:Note|pov|Add)', row_text)
                
                if handle_match:
                    handle = handle_match.group(1).strip()
                    
                    # Skip if handle looks like a status or action
                    if handle.lower() in ['note', 'add', 'tags', 'hired', 'live', 'post', 'paid']:
                        continue
                    
                    # Extract display name (usually before handle)
                    display_name = handle  # Default to handle
                    
                    # Extract price if present
                    price = None
                    price_match = re.search(r'\$(\d+(?:\.\d{2})?)', row_text)
                    if price_match:
                        price = float(price_match.group(1))
                    
                    # Extract email if present
                    email = None
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', row_text)
                    if email_match:
                        email = email_match.group(0)
                    
                    creator = Creator(
                        handle=handle,
                        display_name=display_name,
                        status=status,
                        posts_done=posts_done,
                        posts_owed=posts_owed,
                        needs_scraping=needs_scraping,
                        price=price,
                        email=email
                    )
                    
                    campaign.creators.append(creator)
                    
                    scrape_status = "🔍 SCRAPE" if needs_scraping else "✅ DONE"
                    print(f"    {scrape_status} @{handle}: {posts_done}/{posts_owed}")
                    
            except Exception as e:
                continue
        
        print(f"  [OK] Found {len(campaign.creators)} creators")
        return campaign
        
    except Exception as e:
        print(f"  [ERROR] Failed to extract: {e}")
        return None


def save_campaign_csv(campaign: Campaign, output_dir: Path):
    """Save campaign data to CSV"""
    
    # Clean filename
    safe_name = re.sub(r'[^\w\s-]', '', campaign.name)
    safe_name = re.sub(r'\s+', '_', safe_name)[:50]
    
    csv_path = output_dir / f"{safe_name}.csv"
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Header with metadata
        writer.writerow(['# Campaign:', campaign.name])
        writer.writerow(['# Artist:', campaign.artist])
        writer.writerow(['# Sound:', campaign.sound_name or 'Unknown'])
        writer.writerow(['# Sound URL:', campaign.sound_url or ''])
        writer.writerow(['# Status:', campaign.status])
        writer.writerow(['# Extracted:', datetime.now().isoformat()])
        writer.writerow([])
        
        # Creator data
        writer.writerow(['Handle', 'Display Name', 'Status', 'Posts Done', 'Posts Owed', 'Needs Scraping', 'Price', 'Email'])
        
        for creator in campaign.creators:
            writer.writerow([
                creator.handle,
                creator.display_name,
                creator.status,
                creator.posts_done,
                creator.posts_owed,
                'Yes' if creator.needs_scraping else 'No',
                creator.price or '',
                creator.email or ''
            ])
    
    print(f"  [SAVED] {csv_path}")
    return csv_path


# =============================================================================
# MAIN
# =============================================================================

async def main(max_pages: int = 4, output_dir: Path = OUTPUT_DIR, headless: bool = False):
    """Main extraction flow"""
    
    print("=" * 60)
    print("COBRAND CAMPAIGN EXTRACTOR")
    print("=" * 60)
    print(f"Max pages: {max_pages}")
    print(f"Output dir: {output_dir}")
    print()
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_campaigns = []
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900}
        )
        page = await context.new_page()
        
        # Navigate to Cobrand promotions
        print("[INFO] Opening Cobrand...")
        await page.goto(f"{COBRAND_URL}/promote/?oid={ORG_ID}", wait_until='domcontentloaded')
        await wait_for_load(page)
        
        # Check if logged in
        if 'login' in page.url.lower() or 'auth' in page.url.lower():
            print("[ERROR] Not logged in! Please log in manually first.")
            print("[INFO] Opening browser for manual login...")
            await page.wait_for_timeout(60000)  # Wait for manual login
        
        # Scan promotion pages
        all_promotions = []
        
        for page_num in range(1, max_pages + 1):
            print(f"\n[INFO] Scanning page {page_num}...")
            
            promotions = await extract_promotions_list(page)
            
            if not promotions:
                print(f"  No promotions found on page {page_num}")
                break
            
            all_promotions.extend(promotions)
            
            # Try to go to next page
            try:
                next_btn = await page.query_selector('button:has(img[alt*="next"]), button:has-text("›")')
                if next_btn:
                    is_disabled = await next_btn.get_attribute('disabled')
                    if not is_disabled:
                        await next_btn.click()
                        await wait_for_load(page)
                    else:
                        break
                else:
                    break
            except:
                break
        
        print(f"\n[INFO] Found {len(all_promotions)} active promotions")
        
        # Extract details from each promotion
        for promo in all_promotions:
            campaign = await extract_campaign_details(page, promo)
            
            if campaign and campaign.creators:
                all_campaigns.append(campaign)
                save_campaign_csv(campaign, output_dir)
            
            # Go back to promotions list
            await page.goto(f"{COBRAND_URL}/promote/?oid={ORG_ID}", wait_until='domcontentloaded')
            await wait_for_load(page)
        
        await browser.close()
    
    # Summary
    print("\n" + "=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Campaigns extracted: {len(all_campaigns)}")
    
    # Count creators needing scraping
    total_creators = sum(len(c.creators) for c in all_campaigns)
    needs_scraping = sum(1 for c in all_campaigns for cr in c.creators if cr.needs_scraping)
    
    print(f"Total creators: {total_creators}")
    print(f"Need scraping: {needs_scraping}")
    print(f"CSVs saved to: {output_dir}")
    
    # Create summary JSON
    summary = {
        'extracted_at': datetime.now().isoformat(),
        'campaigns': len(all_campaigns),
        'total_creators': total_creators,
        'needs_scraping': needs_scraping,
        'campaigns_data': [
            {
                'name': c.name,
                'sound': c.sound_name,
                'sound_url': c.sound_url,
                'creator_count': len(c.creators),
                'needs_scraping': sum(1 for cr in c.creators if cr.needs_scraping)
            }
            for c in all_campaigns
        ]
    }
    
    summary_path = output_dir / 'extraction_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Summary saved to: {summary_path}")
    
    return all_campaigns


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract campaigns from Cobrand')
    parser.add_argument('--pages', type=int, default=4, help='Number of pages to scan')
    parser.add_argument('--output-dir', type=str, default='output/campaigns', help='Output directory')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    asyncio.run(main(
        max_pages=args.pages,
        output_dir=Path(args.output_dir),
        headless=args.headless
    ))
