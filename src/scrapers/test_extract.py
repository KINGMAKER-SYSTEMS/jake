"""Test sound ID extraction from a known video"""
import requests
import json
import re

# The video Jake sent - known to use the Dougie sound
video_url = "https://www.tiktok.com/@onlyupset_/video/7598681874155818253"
target_sound_id = "7582646433275317023"

print(f"Testing: {video_url}")
print(f"Looking for sound ID: {target_sound_id}")

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(video_url, headers=headers, timeout=30)
    response.raise_for_status()
    html = response.text
    
    print(f"\nResponse length: {len(html)} chars")
    
    # Try to find the JSON data
    pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([^<]+)</script>'
    matches = re.findall(pattern, html, re.DOTALL)
    
    if matches:
        print(f"\nFound UNIVERSAL_DATA JSON block ({len(matches[0])} chars)")
        data = json.loads(matches[0])
        
        try:
            music = data['__DEFAULT_SCOPE__']['webapp.video-detail']['itemInfo']['itemStruct']['music']
            sound_id = music.get('id')
            song_title = music.get('title', '')
            author = music.get('authorName', '')
            
            print(f"\nExtracted:")
            print(f"  Sound ID: {sound_id}")
            print(f"  Title: {song_title}")
            print(f"  Author: {author}")
            
            if str(sound_id) == target_sound_id:
                print(f"\n✅ MATCH! Sound ID matches target")
            else:
                print(f"\n❌ NO MATCH. Expected {target_sound_id}, got {sound_id}")
        except KeyError as e:
            print(f"KeyError: {e}")
            print("Trying to find structure...")
            print(json.dumps(data, indent=2)[:2000])
    else:
        print("No UNIVERSAL_DATA found")
        
        # Try alternate pattern
        pattern2 = r'"music":\s*(\{[^}]+\})'
        matches2 = re.findall(pattern2, html)
        if matches2:
            print(f"\nFound music block directly: {matches2[0][:200]}")

except Exception as e:
    print(f"Error: {e}")
