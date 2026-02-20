#!/usr/bin/env python3
"""Check video date and see if it matches our criteria"""
import subprocess
import json
import sys
import shutil
from datetime import datetime, timedelta

video_url = "https://www.tiktok.com/@venald.b/video/7584555371113565470"
target_sound_id = "7534110676248316686"

yt_dlp_cmd = 'yt-dlp'
if not shutil.which('yt-dlp'):
    yt_dlp_cmd = [sys.executable, '-m', 'yt_dlp']

cmd = [yt_dlp_cmd if isinstance(yt_dlp_cmd, str) else yt_dlp_cmd[0], '--dump-json', video_url]
if not isinstance(yt_dlp_cmd, str):
    cmd = [sys.executable, '-m', 'yt_dlp'] + cmd[1:]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
data = json.loads(result.stdout)

print("Video Information:")
print("=" * 80)
print(f"URL: {video_url}")
print(f"Track: {data.get('track', 'N/A')}")
print(f"Artist: {data.get('artist', 'N/A')}")
print(f"Title: {data.get('title', 'N/A')}")

# Get timestamp
timestamp = data.get('timestamp')
upload_date = data.get('upload_date')

video_dt = None
if timestamp:
    try:
        video_dt = datetime.fromtimestamp(timestamp)
    except:
        pass

if not video_dt and upload_date:
    try:
        video_dt = datetime.strptime(upload_date, '%Y%m%d')
    except:
        pass

if video_dt:
    print(f"Posted: {video_dt.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if within last 24 hours
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=24)
    
    print(f"\n24-hour window: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    
    if start_date <= video_dt <= end_date:
        print("✓ Video IS within last 24 hours")
    else:
        print("✗ Video is NOT within last 24 hours")
        if video_dt < start_date:
            hours_ago = (start_date - video_dt).total_seconds() / 3600
            print(f"  Video is {hours_ago:.1f} hours too old")
        else:
            print("  Video is in the future (shouldn't happen)")
else:
    print("Could not determine video date")

# Check if artist matches
artist = data.get('artist', '').lower()
track = data.get('track', '').lower()
print(f"\nArtist check: '{artist}' contains 'chance' and 'pena'?")
print(f"  'chance' in artist: {'chance' in artist}")
print(f"  'pena' in artist or track: {('pena' in artist) or ('pena' in track)}")
print(f"  Track is 'original sound': {'original sound' in track}")

print(f"\nThis video should match if:")
print(f"  1. It's within the date range (last 24 hours)")
print(f"  2. The sound ID extraction finds: {target_sound_id}")
print(f"  3. OR we match by artist='chancepena' and track='original sound'")

