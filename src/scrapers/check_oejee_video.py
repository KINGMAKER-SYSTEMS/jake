#!/usr/bin/env python3
"""Check a specific video to see why it wasn't found"""

import subprocess
import json
from datetime import datetime

video_url = "https://www.tiktok.com/@oejee/video/7580028745411513622"

print("Checking video:", video_url)
print("=" * 80)

# Get video metadata
cmd = ['yt-dlp', '--dump-json', video_url]
result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode != 0:
    print(f"Error: {result.stderr}")
else:
    data = json.loads(result.stdout)
    
    # Extract info
    track = data.get('track', '') or 'Unknown'
    artist = data.get('artist', '') or (data.get('artists', [])[0] if data.get('artists') else 'Unknown')
    
    timestamp = data.get('timestamp')
    if timestamp:
        video_date = datetime.fromtimestamp(timestamp)
    else:
        upload_date = data.get('upload_date', '')
        if upload_date:
            try:
                video_date = datetime.strptime(upload_date, '%Y%m%d')
            except:
                video_date = None
        else:
            video_date = None
    
    print(f"Song: {track}")
    print(f"Artist: {artist}")
    print(f"Date: {video_date}")
    print(f"Views: {data.get('view_count', 0):,}")
    print(f"Likes: {data.get('like_count', 0):,}")
    
    # Check if it matches
    target_song = 'Drifting Away'
    target_artist = 'Mattilo'
    
    song_match = target_song.lower() in track.lower() or track.lower() in target_song.lower()
    artist_match = target_artist.lower() in artist.lower() or artist.lower() in target_artist.lower()
    
    print(f"\nMatching check:")
    print(f"  Song match: {song_match} (looking for '{target_song}', found '{track}')")
    print(f"  Artist match: {artist_match} (looking for '{target_artist}', found '{artist}')")
    print(f"  Would match: {song_match and artist_match}")
    
    # Check date range
    start_date = datetime(2025, 11, 11, 0, 0)
    end_date = datetime.now()
    
    if video_date:
        in_range = start_date <= video_date <= end_date
        print(f"\nDate range check:")
        print(f"  Start: {start_date}")
        print(f"  Video date: {video_date}")
        print(f"  End: {end_date}")
        print(f"  In range: {in_range}")

