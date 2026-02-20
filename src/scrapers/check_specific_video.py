#!/usr/bin/env python3
"""Check a specific video directly"""

import subprocess
import json
import sys
import shutil
from datetime import datetime

video_url = "https://www.tiktok.com/@oejee/video/7580028745411513622"

print("Fetching video metadata directly...")
print("=" * 80)

# Use yt-dlp
yt_dlp_cmd = 'yt-dlp'
if not shutil.which('yt-dlp'):
    yt_dlp_cmd = [sys.executable, '-m', 'yt_dlp']

cmd = [
    yt_dlp_cmd if isinstance(yt_dlp_cmd, str) else yt_dlp_cmd[0],
    '--dump-json',
    video_url
]

if not isinstance(yt_dlp_cmd, str):
    cmd = [sys.executable, '-m', 'yt_dlp'] + cmd[1:]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    
    if result.returncode != 0:
        print(f"Error fetching video: {result.stderr}")
    else:
        data = json.loads(result.stdout)
        
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
        
        print(f"Video URL: {video_url}")
        print(f"Song: '{track}'")
        print(f"Artist: '{artist}'")
        print(f"Date: {video_date}")
        print(f"Views: {data.get('view_count', 0):,}")
        print(f"Likes: {data.get('like_count', 0):,}")
        
        # Check against our criteria
        start_date = datetime(2025, 11, 11, 0, 0)
        end_date = datetime.now()
        
        print(f"\n" + "=" * 80)
        print("ANALYSIS:")
        print("=" * 80)
        
        if video_date:
            in_range = start_date <= video_date <= end_date
            print(f"Date range: {start_date} to {end_date}")
            print(f"Video date: {video_date}")
            print(f"In date range: {in_range}")
        else:
            print("Could not determine video date")
        
        target_song = 'Drifting Away'
        target_artist = 'Mattilo'
        
        song_match = target_song.lower() in track.lower() or track.lower() in target_song.lower()
        artist_match = target_artist.lower() in artist.lower() or artist.lower() in target_artist.lower()
        
        print(f"\nSong matching:")
        print(f"  Looking for: '{target_song}' by '{target_artist}'")
        print(f"  Found: '{track}' by '{artist}'")
        print(f"  Song match: {song_match}")
        print(f"  Artist match: {artist_match}")
        print(f"  Would be included: {song_match and artist_match}")
        
except subprocess.TimeoutExpired:
    print("Timeout fetching video")
except Exception as e:
    print(f"Error: {e}")

