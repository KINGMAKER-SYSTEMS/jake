import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'scrapers'))

from master_tracker import (
    extract_sound_id_from_video_robust,
    scrape_tiktok_account,
    extract_sound_ids_parallel,
    load_account_cache,
    save_account_cache
)
from datetime import datetime
import csv

# Reference video to get sound from
reference_url = "https://www.tiktok.com/@lifecontent1/video/7579782013238955286"

print("=" * 80)
print("OPTIMIZED SOUND CAMPAIGN SCRAPER")
print("=" * 80)
print("\nExtracting sound from reference video...")
sound_id, sound_title = extract_sound_id_from_video_robust(reference_url)

if not sound_id:
    print("Failed to extract sound ID from reference video")
    print("Using hardcoded sound ID from previous successful extraction...")
    sound_id = "7429163015519341354"
    sound_title = "original sound"

artist = "Quail P"

print(f"\nTarget Sound:")
print(f"  Title: {sound_title}")
print(f"  Artist: {artist}")
print(f"  Sound ID: {sound_id}")

# Accounts to scrape
accounts = [
    "https://www.tiktok.com/@enzowms",
    "https://www.tiktok.com/@enzorealasf",
    "https://www.tiktok.com/@onlyupset_",
    "https://www.tiktok.com/@inniz"
]

# Start date: November 19, 2025
start_date = datetime(2025, 11, 19)

# Scrape each account with smart caching
all_matching_videos = []
cache_stats = {
    'total_cached': 0,
    'total_new': 0,
    'sound_ids_cached': 0,
    'sound_ids_extracted': 0
}

print("\n" + "=" * 80)
print("SCRAPING ACCOUNTS")
print("=" * 80)

for account in accounts:
    account_name = account.split('/')[-1]
    print(f"\n{'─' * 80}")
    print(f"Account: @{account_name}")
    print(f"{'─' * 80}")

    # Load cache first
    cached_videos, last_scrape = load_account_cache(account, 'tiktok')

    if cached_videos:
        print(f"  ✓ Loaded {len(cached_videos)} videos from cache (last scrape: {last_scrape})")
        cache_stats['total_cached'] += len(cached_videos)

        # Count how many already have sound IDs
        cached_with_sound_ids = [v for v in cached_videos if v.get('extracted_sound_id')]
        print(f"  ✓ {len(cached_with_sound_ids)} videos already have sound IDs extracted")
        cache_stats['sound_ids_cached'] += len(cached_with_sound_ids)

        # Filter cached videos by date
        cached_videos_in_range = [
            v for v in cached_videos
            if v.get('timestamp') and datetime.fromisoformat(str(v['timestamp']).replace('Z', '+00:00')) >= start_date
        ]
        print(f"  ✓ {len(cached_videos_in_range)} cached videos since {start_date.strftime('%b %d, %Y')}")
    else:
        print(f"  ℹ No cache found, will scrape all videos")
        cached_videos = []
        cached_videos_in_range = []

    # Scrape for new videos
    print(f"  → Checking for new videos...")
    all_videos = scrape_tiktok_account(account, start_date, limit=500)

    if not all_videos:
        print(f"  ✗ No videos found")
        # Use cached videos if available
        all_videos = cached_videos_in_range
    else:
        new_count = len(all_videos) - len(cached_videos_in_range)
        if new_count > 0:
            print(f"  ✓ Found {new_count} new videos")
            cache_stats['total_new'] += new_count
        else:
            print(f"  ✓ No new videos (all {len(all_videos)} videos already cached)")

    # Extract sound IDs ONLY for videos that don't have them
    videos_needing_ids = [v for v in all_videos if not v.get('extracted_sound_id')]

    if videos_needing_ids:
        print(f"  → Extracting sound IDs for {len(videos_needing_ids)} videos...")
        all_videos = extract_sound_ids_parallel(all_videos, max_workers=10)
        cache_stats['sound_ids_extracted'] += len(videos_needing_ids)

        # Save updated cache with new sound IDs
        save_account_cache(account, 'tiktok', all_videos, datetime.now())
        print(f"  ✓ Saved updated cache")
    else:
        print(f"  ✓ All videos already have sound IDs (using cache)")

    # Filter for matching sound
    matching = [v for v in all_videos if str(v.get('extracted_sound_id')) == str(sound_id)]

    if matching:
        print(f"  ✓ Found {len(matching)} videos with matching sound")
        # Show top 3
        sorted_matching = sorted(matching, key=lambda x: x.get('views', 0), reverse=True)
        for i, v in enumerate(sorted_matching[:3], 1):
            print(f"     {i}. {v.get('views', 0):,} views | {v.get('likes', 0):,} likes")
    else:
        print(f"  ✗ No videos with matching sound")

    all_matching_videos.extend(matching)

# Output results
print("\n" + "=" * 80)
print("CACHE STATISTICS")
print("=" * 80)
print(f"  Total cached videos: {cache_stats['total_cached']}")
print(f"  New videos scraped: {cache_stats['total_new']}")
print(f"  Sound IDs from cache: {cache_stats['sound_ids_cached']}")
print(f"  Sound IDs extracted: {cache_stats['sound_ids_extracted']}")
print(f"  Time saved: ~{cache_stats['sound_ids_cached'] * 0.5:.0f} seconds (approx)")

if all_matching_videos:
    output_file = f"output/{sound_title.replace(' ', '_')}_{artist.replace(' ', '_')}_campaign_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    print(f"\n{'=' * 80}")
    print(f"RESULTS")
    print(f"{'=' * 80}")
    print(f"Writing {len(all_matching_videos)} matching videos to {output_file}")

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['url', 'account', 'platform', 'song', 'artist', 'views', 'likes', 'timestamp', 'extracted_sound_id', 'extracted_song_title']
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_matching_videos)

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
        account_name = account.split('/')[-1]
        account_videos = [v for v in all_matching_videos if v['account'] == f'@{account_name}']
        if account_videos:
            account_views = sum(v.get('views', 0) for v in account_videos)
            account_likes = sum(v.get('likes', 0) for v in account_videos)
            print(f"  @{account_name}: {len(account_videos)} videos, {account_views:,} views, {account_likes:,} likes")

    print(f"\n✓ Results saved to: {output_file}")
    print("=" * 80)
else:
    print(f"\n✗ No matching videos found")
    print("=" * 80)
