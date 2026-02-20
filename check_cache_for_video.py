import pickle
from pathlib import Path
from datetime import datetime

# Video we're looking for
target_video_id = "7589280138232155399"
target_url = f"https://www.tiktok.com/@somethingicouldntsay/video/{target_video_id}"

cache_files = [
    "cache/tiktok_somethingicouldntsay_cache.pkl",
    "cache/somethingicouldntsay_cache.pkl"
]

print(f"Searching for video: {target_video_id}")
print(f"URL: {target_url}")
print("=" * 80)

for cache_file in cache_files:
    cache_path = Path(cache_file)
    if not cache_path.exists():
        print(f"\n[SKIP] {cache_file} - file not found")
        continue

    print(f"\n[CHECKING] {cache_file}")
    print("-" * 80)

    try:
        with open(cache_path, 'rb') as f:
            cache_data = pickle.load(f)

        # Handle both old and new cache formats
        if isinstance(cache_data, dict):
            cached_data = cache_data.get('videos', [])
            last_updated = cache_data.get('last_scrape_date', 'Unknown')
            cached_at = cache_data.get('cached_at', 'Unknown')
        else:
            # Old format - try to unpack
            print(f"Warning: Old cache format detected")
            cached_data = cache_data
            last_updated = 'Unknown'
            cached_at = 'Unknown'

        print(f"Cache last updated: {last_updated}")
        print(f"Cached at: {cached_at}")
        print(f"Total videos in cache: {len(cached_data)}")

        # Search for our target video
        found = False
        for video in cached_data:
            video_url = video.get('url', '')
            if target_video_id in video_url or video_url == target_url:
                found = True
                print(f"\n[FOUND] Video found in cache!")
                print("=" * 80)
                print(f"URL: {video.get('url')}")
                print(f"Account: {video.get('account')}")
                print(f"Song: {video.get('song')}")
                print(f"Artist: {video.get('artist')}")
                print(f"Views: {video.get('views', 0):,}")
                print(f"Likes: {video.get('likes', 0):,}")
                print(f"Timestamp: {video.get('timestamp')}")
                print(f"Extracted Sound ID: {video.get('extracted_sound_id')}")
                print(f"Extracted Song Title: {video.get('extracted_song_title')}")
                print("=" * 80)

                # Check if sound ID matches target
                target_sound_id = "7582024313956518711"
                extracted_sound_id = video.get('extracted_sound_id')

                if extracted_sound_id:
                    if str(extracted_sound_id) == target_sound_id:
                        print(f"[MATCH] Sound ID matches target: {target_sound_id}")
                    else:
                        print(f"[NO MATCH] Sound ID differs from target")
                        print(f"  Expected: {target_sound_id}")
                        print(f"  Found:    {extracted_sound_id}")
                else:
                    print(f"[NO SOUND ID] Sound ID was not extracted for this video")
                    print(f"  This is why it wasn't matched!")

                break

        if not found:
            print(f"\n[NOT FOUND] Video {target_video_id} not in this cache file")

            # Show some recent videos from the cache for context
            print(f"\nMost recent 5 videos in cache:")
            print("-" * 80)
            # Sort by timestamp if available
            sorted_videos = sorted(
                cached_data,
                key=lambda v: v.get('timestamp', datetime.min),
                reverse=True
            )[:5]

            for i, vid in enumerate(sorted_videos, 1):
                ts = vid.get('timestamp', 'N/A')
                url = vid.get('url', 'N/A')
                # Extract video ID from URL
                vid_id = url.split('/')[-1] if '/' in url else 'N/A'
                print(f"{i}. {ts} - Video ID: {vid_id}")
                print(f"   {url}")

    except Exception as e:
        print(f"Error loading cache: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print("If the video was found in cache but has no extracted_sound_id,")
print("then the sound ID extraction failed during scraping.")
print()
print("If the video was not found in cache at all, then either:")
print("  1. The video wasn't scraped from the account (date filter issue)")
print("  2. The cache is outdated and needs refreshing")
