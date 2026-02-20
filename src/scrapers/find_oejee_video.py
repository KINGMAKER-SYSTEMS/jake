#!/usr/bin/env python3
"""
Try to find the specific @oejee video by scraping more videos
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.get_post_links_by_song import scrape_account_videos

account = 'oejee'
target_video_id = "7580028745411513622"

# Try with a wider date range
start_date = datetime(2025, 10, 1, 0, 0)  # Go back further
end_date = datetime.now()

print("=" * 80)
print(f"SEARCHING FOR VIDEO {target_video_id} IN @{account}")
print("=" * 80)
print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
print("=" * 80)
print()

# Try with very high limit
videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=5000)

print(f"\nTotal videos found: {len(videos)}")

# Look for the specific video
found = False
for video in videos:
    if target_video_id in video.get('url', ''):
        found = True
        print(f"\n✓ FOUND THE VIDEO!")
        print(f"  URL: {video.get('url')}")
        print(f"  Song: '{video.get('song', 'N/A')}'")
        print(f"  Artist: '{video.get('artist', 'N/A')}'")
        print(f"  Date: {video.get('timestamp', 'N/A')}")
        print(f"  Views: {video.get('views', 0):,}")
        print(f"  Likes: {video.get('likes', 0):,}")
        break

if not found:
    print(f"\n✗ Video still not found")
    print(f"  This suggests the video might be:")
    print(f"    1. Posted after {end_date.strftime('%Y-%m-%d')}")
    print(f"    2. Posted before {start_date.strftime('%Y-%m-%d')}")
    print(f"    3. Not accessible via yt-dlp profile scraping")
    print(f"\n  Video IDs near the target (for reference):")
    # Show some video IDs to see the pattern
    for i, video in enumerate(videos[:10]):
        url = video.get('url', '')
        if '/video/' in url:
            vid_id = url.split('/video/')[-1]
            print(f"    {i+1}. {vid_id} - {video.get('timestamp', 'N/A')}")

