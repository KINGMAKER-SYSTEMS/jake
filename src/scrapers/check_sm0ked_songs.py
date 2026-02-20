#!/usr/bin/env python3
"""Check what songs are in sm0ked.9 videos"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.get_post_links_by_song import scrape_account_videos

account = 'sm0ked.9'
print(f"Checking first 20 videos from @{account}...")
videos = scrape_account_videos(account, start_datetime=None, end_datetime=None, limit=20)

print(f"\nFound {len(videos)} videos\n")
print("Sample songs/artists:")
print("=" * 80)
for i, video in enumerate(videos[:20], 1):
    song = video.get('song', 'Unknown')
    artist = video.get('artist', 'Unknown')
    print(f"{i}. Song: {song} | Artist: {artist}")

# Also search for any containing "halfway"
print("\n" + "=" * 80)
print("Videos containing 'halfway' in song or artist:")
print("=" * 80)
halfway_videos = [v for v in videos if 'halfway' in v.get('song', '').lower() or 'halfway' in v.get('artist', '').lower()]
if halfway_videos:
    for video in halfway_videos:
        print(f"Song: {video.get('song', 'Unknown')} | Artist: {video.get('artist', 'Unknown')}")
        print(f"URL: {video['url']}\n")
else:
    print("None found in first 20 videos")

