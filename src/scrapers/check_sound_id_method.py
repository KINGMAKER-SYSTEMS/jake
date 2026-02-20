#!/usr/bin/env python3
"""Check different methods to get sound ID from TikTok video"""
import subprocess
import json
import sys
import shutil
import re
import requests

video_url = "https://www.tiktok.com/@venald.b/video/7584555371113565470"
target_sound_id = "7534110676248316686"

print("Method 1: Check yt-dlp with --write-info-json")
print("=" * 80)

yt_dlp_cmd = 'yt-dlp'
if not shutil.which('yt-dlp'):
    yt_dlp_cmd = [sys.executable, '-m', 'yt_dlp']

# Try with different extractors or options
cmd = [yt_dlp_cmd if isinstance(yt_dlp_cmd, str) else yt_dlp_cmd[0], 
       '--dump-json', 
       '--extractor-args', 'tiktok:webpage_download',
       video_url]
if not isinstance(yt_dlp_cmd, str):
    cmd = [sys.executable, '-m', 'yt_dlp'] + cmd[1:]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
if result.returncode == 0:
    data = json.loads(result.stdout)
    print("Found fields:")
    for k in ['track', 'artist', 'webpage_url', 'description', 'title']:
        if k in data:
            print(f"  {k}: {data[k]}")

print("\n\nMethod 2: Try to extract from webpage HTML")
print("=" * 80)
try:
    # Try to get the page and look for sound ID in the HTML
    response = requests.get(video_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
    if response.status_code == 200:
        html = response.text
        # Look for music/sound links in the HTML
        sound_matches = re.findall(r'/music/(?:original-sound-)?(\d+)', html)
        if sound_matches:
            print(f"Found sound IDs in HTML: {set(sound_matches)}")
        else:
            print("No sound IDs found in HTML")
        
        # Look for JSON data in script tags
        script_matches = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
        for i, script in enumerate(script_matches[:5]):  # Check first 5 scripts
            if 'music' in script.lower() or 'sound' in script.lower():
                sound_ids = re.findall(r'["\']?(\d{15,20})["\']?', script)
                if sound_ids:
                    print(f"Found potential sound IDs in script {i}: {sound_ids[:3]}")
except Exception as e:
    print(f"Error fetching HTML: {e}")

print("\n\nMethod 3: Check if we can get it from the video's music page link")
print("=" * 80)
print("Note: For 'original sound' videos, the sound ID should be in the video's music link")
print("We may need to check the video page for a link to the music/sound page")

