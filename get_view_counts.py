#!/usr/bin/env python3
"""
Quick script to get total view counts for specified accounts since Nov 15
"""

import sys
from pathlib import Path
from datetime import datetime
import importlib.util

# Load master_tracker from src/scrapers directory
script_dir = Path(__file__).parent
scraper_path = script_dir / "src" / "scrapers" / "master_tracker.py"

if not scraper_path.exists():
    print(f"ERROR: Could not find master_tracker.py at {scraper_path}")
    sys.exit(1)

spec = importlib.util.spec_from_file_location("master_tracker", scraper_path)
master_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(master_module)

scrape_tiktok_account = master_module.scrape_tiktok_account
get_profile_username = master_module.get_profile_username
log = master_module.log

def get_account_views(account_url, start_date=None, limit=2000):
    """Get total views for an account since start_date"""

    username = get_profile_username(account_url)
    log(f"=== SCRAPING @{username} ===")

    # Scrape account without date filter to avoid date comparison issues
    videos = scrape_tiktok_account(account_url, None, limit=limit, use_cache=False)
    log(f"Scraped {len(videos)} videos")

    if not videos:
        log("No videos found!", "ERROR")
        return None

    # Filter by date if needed
    if start_date:
        filtered_videos = []
        for video in videos:
            video_dt = video.get('timestamp')
            if video_dt:
                if isinstance(video_dt, datetime):
                    if video_dt >= start_date:
                        filtered_videos.append(video)
                elif hasattr(video_dt, 'date'):
                    if video_dt.date() >= start_date.date():
                        filtered_videos.append(video)
            else:
                # If no timestamp, include it
                filtered_videos.append(video)
        videos = filtered_videos
        log(f"Filtered to {len(videos)} videos after {start_date.date()}")

    # Calculate total views
    total_views = sum(video.get('views', 0) for video in videos)
    total_likes = sum(video.get('likes', 0) for video in videos)

    return {
        'username': username,
        'total_videos': len(videos),
        'total_views': total_views,
        'total_likes': total_likes,
        'avg_views_per_video': total_views / len(videos) if videos else 0
    }

def main():
    accounts = [
        "https://www.tiktok.com/@beaujenkins",
        "https://www.tiktok.com/@codyjames6.7"
    ]

    start_date = datetime(2025, 11, 15, 0, 0, 0)

    print("\n" + "="*80)
    print(f"VIEW COUNT REPORT - Since {start_date.date()}")
    print("="*80 + "\n")

    results = []
    for account in accounts:
        try:
            result = get_account_views(account, start_date=start_date, limit=2000)
            if result:
                results.append(result)
        except Exception as e:
            log(f"Error scraping {account}: {e}", "ERROR")

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"{'Account':<20} {'Videos':<10} {'Total Views':<20} {'Avg Views/Video':<15}")
    print("-"*80)

    for result in results:
        print(f"@{result['username']:<19} {result['total_videos']:<10} {result['total_views']:<20,} {result['avg_views_per_video']:<15,.0f}")

    # Grand total
    total_views_all = sum(r['total_views'] for r in results)
    total_videos_all = sum(r['total_videos'] for r in results)

    print("-"*80)
    print(f"{'TOTAL':<20} {total_videos_all:<10} {total_views_all:<20,}")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
