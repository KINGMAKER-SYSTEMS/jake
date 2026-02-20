#!/usr/bin/env python3
"""
Re-scrape @codyjames6.7 for latest view counts
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.get_post_links_by_song import scrape_account_videos

account = 'codyjames6.7'
start_date = datetime(2025, 11, 15, 0, 0)
end_date = datetime.now()

print("=" * 80)
print(f"RE-SCRAPING @{account} FOR LATEST VIEW COUNTS")
print("=" * 80)
print(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
print("=" * 80)
print()

videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)

if not videos:
    print("No videos found.")
else:
    # Sort by views descending for top videos
    videos_by_views = sorted(videos, key=lambda x: x['views'], reverse=True)
    # Sort by date for chronological listing
    videos_by_date = sorted(videos, key=lambda x: x.get('timestamp', datetime.min) if x.get('timestamp') else datetime.min, reverse=True)
    
    total_views = sum(v['views'] for v in videos)
    total_likes = sum(v['likes'] for v in videos)
    avg_views = total_views // len(videos)
    
    print(f"\n{'=' * 80}")
    print("UPDATED STATISTICS")
    print("=" * 80)
    print(f"Total Videos: {len(videos)}")
    print(f"Total Views: {total_views:,}")
    print(f"Total Likes: {total_likes:,}")
    print(f"Average Views per Video: {avg_views:,}")
    print(f"Top Video Views: {videos_by_views[0]['views']:,}")
    
    print(f"\n{'=' * 80}")
    print("TOP 10 VIDEOS BY VIEWS (Latest View Counts)")
    print("=" * 80)
    
    for i, video in enumerate(videos_by_views[:10], 1):
        date_str = video['timestamp'].strftime('%Y-%m-%d') if video.get('timestamp') else 'Unknown'
        print(f"{i:2}. Views: {video['views']:,} | Likes: {video['likes']:,} | Date: {date_str}")
        print(f"    {video['url']}")

