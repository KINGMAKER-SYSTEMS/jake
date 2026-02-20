#!/usr/bin/env python3
"""
Quick scraper for yearnest.hemingway TikTok account
"""

import sys
import csv
from pathlib import Path
from datetime import datetime

# Import from master_tracker
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'scrapers'))
from master_tracker import scrape_tiktok_account, log

def main():
    account = "yearnest.hemingway"
    start_date = datetime(2025, 12, 20).date()

    log(f"Scraping @{account} from {start_date} onwards...")

    # Scrape the account
    videos = scrape_tiktok_account(
        account=account,
        start_date=start_date,
        limit=500,
        use_cache=True
    )

    log(f"Found {len(videos)} videos")

    # Save results
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"yearnest_hemingway_{timestamp}.csv"

    if videos:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['url', 'account', 'song', 'artist', 'views', 'likes',
                         'upload_date', 'timestamp', 'music_id', 'platform']
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')

            writer.writeheader()
            for video in videos:
                writer.writerow(video)

        log(f"Saved {len(videos)} videos to {output_file}")
        print(f"\nResults saved to: {output_file}")
    else:
        log("No videos found", "WARNING")

if __name__ == '__main__':
    main()
