#!/usr/bin/env python3
"""Check specific video metadata"""
import subprocess
import json
import sys
import shutil

video_url = "https://www.tiktok.com/@smoked.999/video/7585496797909470482"

yt_dlp_cmd = 'yt-dlp'
if not shutil.which('yt-dlp'):
    yt_dlp_cmd = [sys.executable, '-m', 'yt_dlp']

cmd = [yt_dlp_cmd if isinstance(yt_dlp_cmd, str) else yt_dlp_cmd[0], '--dump-json', video_url]
if not isinstance(yt_dlp_cmd, str):
    cmd = [sys.executable, '-m', 'yt_dlp'] + cmd[1:]

print(f"Checking video: {video_url}")
print("=" * 80)

result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

if result.returncode != 0:
    print(f"ERROR: {result.stderr}")
    sys.exit(1)

data = json.loads(result.stdout)

print(f"Song: {data.get('track', 'N/A')}")
print(f"Artist: {data.get('artist', 'N/A')}")
print(f"Title: {data.get('title', 'N/A')}")
print(f"Description: {data.get('description', 'N/A')[:200]}")

# Check all fields for "halfway"
print("\n" + "=" * 80)
print("Fields containing 'halfway':")
for k, v in data.items():
    if isinstance(v, str) and 'halfway' in v.lower():
        print(f"{k}: {v}")

