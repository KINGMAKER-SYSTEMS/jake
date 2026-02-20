#!/usr/bin/env python3
"""
Diagnose why @oejee video wasn't found
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import Counter

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.get_post_links_by_song import scrape_account_videos

def matches_song(video, song_name, artist_name):
    """Check if video matches song name and artist (case-insensitive, partial match)"""
    video_song = video.get('song', '').lower()
    video_artist = video.get('artist', '').lower()
    
    song_match = song_name.lower() in video_song or video_song in song_name.lower()
    artist_match = artist_name.lower() in video_artist or video_artist in artist_name.lower()
    
    return song_match and artist_match

# Scrape @oejee
account = 'oejee'
start_date = datetime(2025, 11, 11, 0, 0)
end_date = datetime.now()

target_song = 'Drifting Away'
target_artist = 'Mattilo'

print("=" * 80)
print(f"DIAGNOSING @{account} SCRAPE")
print("=" * 80)
print(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
print(f"Looking for: '{target_song}' by '{target_artist}'")
print("=" * 80)
print()

videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=1000)

print(f"\nTotal videos found in date range: {len(videos)}")

# Check for the specific video
target_video_id = "7580028745411513622"
target_video_url = f"https://www.tiktok.com/@{account}/video/{target_video_id}"

print(f"\nLooking for video: {target_video_url}")

found_video = None
for video in videos:
    if target_video_id in video.get('url', ''):
        found_video = video
        break

if found_video:
    print(f"✓ Video found in scrape results!")
    print(f"  URL: {found_video['url']}")
    print(f"  Song: '{found_video.get('song', 'N/A')}'")
    print(f"  Artist: '{found_video.get('artist', 'N/A')}'")
    print(f"  Date: {found_video.get('timestamp', 'N/A')}")
    
    # Check matching
    matches = matches_song(found_video, target_song, target_artist)
    print(f"  Would match filter: {matches}")
    
    if not matches:
        print(f"\n  Why it didn't match:")
        video_song = found_video.get('song', '').lower()
        video_artist = found_video.get('artist', '').lower()
        song_match = target_song.lower() in video_song or video_song in target_song.lower()
        artist_match = target_artist.lower() in video_artist or video_artist in target_artist.lower()
        print(f"    Song match: {song_match} ('{target_song.lower()}' in '{video_song}' or vice versa)")
        print(f"    Artist match: {artist_match} ('{target_artist.lower()}' in '{video_artist}' or vice versa)")
else:
    print(f"✗ Video NOT found in scrape results")
    print(f"  This could mean:")
    print(f"    1. Video is outside the date range")
    print(f"    2. Video wasn't in the first 1000 videos scraped")
    print(f"    3. Video was filtered out for some reason")

# Show all unique songs found
print(f"\n" + "=" * 80)
print("ALL UNIQUE SONGS FOUND FOR @oejee:")
print("=" * 80)

song_counter = Counter()
for video in videos:
    song = video.get('song', 'Unknown')
    artist = video.get('artist', 'Unknown')
    song_key = f"{song} - {artist}"
    song_counter[song_key] += 1

for song_key, count in song_counter.most_common(20):
    print(f"  {song_key}: {count} videos")

# Check for any songs with "drifting" or "mattilo"
print(f"\n" + "=" * 80)
print("SONGS CONTAINING 'drifting' OR 'mattilo':")
print("=" * 80)

drifting_videos = []
for video in videos:
    song = video.get('song', '').lower()
    artist = video.get('artist', '').lower()
    if 'drifting' in song or 'mattilo' in artist:
        drifting_videos.append(video)

if drifting_videos:
    for video in drifting_videos:
        print(f"  {video.get('song', 'N/A')} - {video.get('artist', 'N/A')}")
        print(f"    URL: {video.get('url', 'N/A')}")
        print(f"    Date: {video.get('timestamp', 'N/A')}")
        print()
else:
    print("  None found")

