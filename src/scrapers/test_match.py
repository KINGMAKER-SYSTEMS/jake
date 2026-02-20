"""Test the actual matching logic"""
import requests
import json
import re

# Simulate what the scraper does
target_sound_id = "7582646433275317023"  # From CSV (string)
sound_ids = {target_sound_id}  # Set of strings

# Extract sound ID from video (like the scraper does)
video_url = "https://www.tiktok.com/@onlyupset_/video/7598681874155818253"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
response = requests.get(video_url, headers=headers, timeout=30)
html = response.text

pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([^<]+)</script>'
matches = re.findall(pattern, html, re.DOTALL)
data = json.loads(matches[0])

music = data['__DEFAULT_SCOPE__']['webapp.video-detail']['itemInfo']['itemStruct']['music']
extracted_id = music.get('id')

print(f"CSV sound_ids set: {sound_ids}")
print(f"  Type of element: {type(target_sound_id)}")
print()
print(f"Extracted from video: {extracted_id}")
print(f"  Type: {type(extracted_id)}")
print()

# Test matching
print("Testing match strategies:")
print(f"  str(extracted_id) in sound_ids: {str(extracted_id) in sound_ids}")
print(f"  extracted_id in sound_ids: {extracted_id in sound_ids}")
print(f"  {repr(str(extracted_id))} == {repr(target_sound_id)}: {str(extracted_id) == target_sound_id}")

# The actual matching code from master_tracker.py
if extracted_id and str(extracted_id) in sound_ids:
    print("\nMATCH WOULD SUCCEED")
else:
    print("\nMATCH WOULD FAIL")
    print(f"  extracted_id truthy: {bool(extracted_id)}")
    print(f"  str(extracted_id): {repr(str(extracted_id))}")
