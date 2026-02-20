#!/usr/bin/env python3
"""Debug script to check video metadata"""
import subprocess
import json
import sys
import shutil
import re

video_url = "https://www.tiktok.com/@venald.b/video/7584555371113565470"
target_sound_id = "7534110676248316686"

yt_dlp_cmd = 'yt-dlp'
if not shutil.which('yt-dlp'):
    yt_dlp_cmd = [sys.executable, '-m', 'yt_dlp']

cmd = [yt_dlp_cmd if isinstance(yt_dlp_cmd, str) else yt_dlp_cmd[0], '--dump-json', video_url]
if not isinstance(yt_dlp_cmd, str):
    cmd = [sys.executable, '-m', 'yt_dlp'] + cmd[1:]

print(f"Fetching metadata for: {video_url}")
print("=" * 80)

result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

if result.returncode != 0:
    print(f"ERROR: {result.stderr}")
    sys.exit(1)

data = json.loads(result.stdout)

print("\nAll fields containing 'sound', 'music', 'track', or 'audio':")
print("-" * 80)
for k, v in data.items():
    if any(term in k.lower() for term in ['sound', 'music', 'track', 'audio']):
        print(f"{k}: {v}")

print("\n\nWebpage URL:")
print(data.get('webpage_url', 'N/A'))

print("\n\nAll keys in data:")
print(list(data.keys())[:50])

print("\n\nFull JSON (first 5000 chars):")
print(json.dumps(data, indent=2)[:5000])

# Try to extract sound ID
print("\n\n" + "=" * 80)
print("ATTEMPTING TO EXTRACT SOUND ID:")
print("-" * 80)

sound_id_match = None

# Check webpage_url
webpage_url = data.get('webpage_url', '')
sound_match = re.search(r'/music/(?:original-sound-)?(\d+)', webpage_url)
if sound_match:
    sound_id_match = sound_match.group(1)
    print(f"Found in webpage_url: {sound_id_match}")

# Check other URL fields
if not sound_id_match:
    for field in ['music_url', 'audio_url', 'sound_url', 'url']:
        if field in data:
            url_val = str(data[field])
            sound_match = re.search(r'/music/(?:original-sound-)?(\d+)', url_val)
            if sound_match:
                sound_id_match = sound_match.group(1)
                print(f"Found in {field}: {sound_id_match}")
                break

# Check ID fields
if not sound_id_match:
    for field in ['track_id', 'sound_id', 'music_id', 'audio_id', 'music_track_id']:
        if field in data:
            val = str(data[field])
            if val.isdigit():
                sound_id_match = val
                print(f"Found in {field}: {sound_id_match}")
                break

# Check description
if not sound_id_match:
    description = data.get('description', '') or data.get('title', '')
    sound_match = re.search(r'/music/(?:original-sound-)?(\d+)', description)
    if sound_match:
        sound_id_match = sound_match.group(1)
        print(f"Found in description: {sound_id_match}")

print(f"\nExtracted Sound ID: {sound_id_match}")
print(f"Target Sound ID: {target_sound_id}")
print(f"Match: {sound_id_match == target_sound_id}")

