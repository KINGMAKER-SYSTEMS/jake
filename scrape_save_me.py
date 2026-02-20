"""
Scraper for Save Me by Realest K Campaign
Start Date: January 12, 2026
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'scrapers'))

from master_tracker import extract_sound_id_from_video_robust, scrape_tiktok_account, extract_sound_ids_parallel, save_account_cache
from datetime import datetime
import csv

# Sound URL: https://www.tiktok.com/music/original-sound-7591401425243081492
sound_id = "7591401425243081492"
sound_title = "Save Me"

artist = "Realest K"
song = "Save Me"

print(f"\nTarget Sound:")
print(f"  Title: {sound_title}")
print(f"  Artist: {artist}")
print(f"  Song: {song}")

# Accounts to scrape
accounts = [
    "seraahr",
    "venald.b",
    "amiri.da",
    "saptxc._",
    "stringer2703",
    "dazz_needs_rest",
    "mkryspin",
    "lifecontent1",
    "kikydylvm"
]

# Start date: January 12, 2026
start_date = datetime(2026, 1, 12).date()

# Scrape each account
all_videos = []

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

        # Filter for matching sound
        matching = [v for v in videos if str(v.get('extracted_sound_id')) == str(sound_id)]
        print(f"  Found {len(matching)} videos with matching sound (out of {len(videos)} total)")
        all_videos.extend(matching)
    else:
        print(f"  No videos found")

# Output matching results
if all_videos:
    output_file = f"output/save_me_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    print(f"\nWriting {len(all_videos)} matching videos to {output_file}")

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['url', 'account', 'platform', 'song', 'artist', 'views', 'likes', 'timestamp', 'extracted_sound_id', 'extracted_song_title']
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()

        # Add artist and song to each video
        for video in all_videos:
            video['artist'] = artist
            video['song'] = song

        writer.writerows(all_videos)

    print(f"\nResults saved to: {output_file}")

    # Summary
    total_views = sum(v.get('views', 0) for v in all_videos)
    total_likes = sum(v.get('likes', 0) for v in all_videos)

    print(f"\nSummary:")
    print(f"  Total Videos: {len(all_videos)}")
    print(f"  Total Views: {total_views:,}")
    print(f"  Total Likes: {total_likes:,}")

    # By account
    print(f"\nBreakdown by Account:")
    for account in accounts:
        account_name = account.lstrip('@')
        account_videos = [v for v in all_videos if v['account'] == f'@{account_name}']
        if account_videos:
            account_views = sum(v.get('views', 0) for v in account_videos)
            account_likes = sum(v.get('likes', 0) for v in account_videos)
            print(f"  @{account_name}: {len(account_videos)} videos, {account_views:,} views, {account_likes:,} likes")

else:
    print("\nNo matching videos found for Save Me by Realest K")
