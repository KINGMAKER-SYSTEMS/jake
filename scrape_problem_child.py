"""
Scraper for Problem Child by Jake Balik Campaign
Sound URL: https://www.tiktok.com/music/problem-child-7579020876851611665
Start Date: January 1, 2026
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'scrapers'))

from master_tracker import extract_sound_id_from_video_robust, scrape_tiktok_account, extract_sound_ids_parallel, save_account_cache
from datetime import datetime
import csv

# Sound URL to get sound ID from
sound_url = "https://www.tiktok.com/music/problem-child-7579020876851611665"
# Extract the sound ID directly from the URL
import re
match = re.search(r'-(\d+)$', sound_url)
if match:
    sound_id = match.group(1)
    sound_title = "problem child"
    print(f"Extracted sound ID from URL: {sound_id}")
else:
    print("Failed to extract sound ID from sound URL")
    sys.exit(1)

artist = "Jake Balik"
song = "problem child"

print(f"\nTarget Sound:")
print(f"  Title: {sound_title}")
print(f"  Artist: {artist}")
print(f"  Song: {song}")
print(f"  Sound ID: {sound_id}")

# Accounts to scrape (existing + new)
accounts = [
    "eeryyxx",
    "ijdncc",
    "jeddvdlim",
    "itsdxnmusic",
    "enzorealasf",
    "enzowms",
    "amiri.da"
]

# Start date: January 1, 2026
start_date = datetime(2026, 1, 1).date()

# Scrape each account
all_matching_videos = []

for account in accounts:
    account_name = account.lstrip('@')
    print(f"\nScraping @{account_name}...")

    videos = scrape_tiktok_account(account, start_date, limit=500)

    if videos:
        # Extract sound IDs for videos that don't have them
        videos_needing_ids = [v for v in videos if not v.get('extracted_sound_id')]
        if videos_needing_ids:
            print(f"  Extracting sound IDs for {len(videos_needing_ids)} videos...")
            videos = extract_sound_ids_parallel(videos)
            # Save updated cache with sound IDs
            save_account_cache(account, 'tiktok', videos, datetime.now())
            print(f"  Saved updated cache with sound IDs")

        # Filter for matching sound (compare as strings)
        matching = [v for v in videos if str(v.get('extracted_sound_id')) == str(sound_id)]
        print(f"  Found {len(matching)} videos with matching sound (out of {len(videos)} total)")

        all_matching_videos.extend(matching)
    else:
        print(f"  No videos found")

# Output results
if all_matching_videos:
    output_file = f"output/problem_child_campaign_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    print(f"\nWriting {len(all_matching_videos)} matching videos to {output_file}")

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['url', 'account', 'platform', 'song', 'artist', 'views', 'likes', 'timestamp', 'extracted_sound_id', 'extracted_song_title']
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        # Add artist and song to each video
        for video in all_matching_videos:
            video['artist'] = artist
            video['song'] = song

        writer.writerows(all_matching_videos)

    print(f"\nResults saved to: {output_file}")

    # Summary
    total_views = sum(v.get('views', 0) for v in all_matching_videos)
    total_likes = sum(v.get('likes', 0) for v in all_matching_videos)

    print(f"\nSummary:")
    print(f"  Total Videos: {len(all_matching_videos)}")
    print(f"  Total Views: {total_views:,}")
    print(f"  Total Likes: {total_likes:,}")

    # By account
    print(f"\nBreakdown by Account:")
    for account in accounts:
        account_name = account.lstrip('@')
        account_videos = [v for v in all_matching_videos if v['account'] == f'@{account_name}']
        if account_videos:
            account_views = sum(v.get('views', 0) for v in account_videos)
            account_likes = sum(v.get('likes', 0) for v in account_videos)
            print(f"  @{account_name}: {len(account_videos)} videos, {account_views:,} views, {account_likes:,} likes")
else:
    print("\nNo matching videos found")
