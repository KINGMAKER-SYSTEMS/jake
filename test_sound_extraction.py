import requests
import json
import re

video_url = "https://www.tiktok.com/@somethingicouldntsay/video/7589280138232155399"

print(f"Testing sound ID extraction for: {video_url}")
print("=" * 80)

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    response = requests.get(video_url, headers=headers, timeout=15)

    print(f"HTTP Status: {response.status_code}")

    if response.status_code != 200:
        print(f"ERROR: HTTP {response.status_code}")
        exit(1)

    html = response.text

    # Extract JSON data
    pattern = r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>'
    matches = re.findall(pattern, html, re.DOTALL)

    if not matches:
        print("ERROR: No __UNIVERSAL_DATA_FOR_REHYDRATION__ script found")

        # Try to find any script tags with data
        print("\nSearching for alternative data sources...")
        script_pattern = r'<script[^>]*>(.*?)</script>'
        all_scripts = re.findall(script_pattern, html, re.DOTALL)
        print(f"Found {len(all_scripts)} script tags total")

        # Look for any that might contain music/sound data
        for i, script in enumerate(all_scripts[:10]):  # Check first 10
            if 'music' in script.lower() or 'sound' in script.lower():
                print(f"\nScript {i} contains music/sound keywords (first 500 chars):")
                print(script[:500])

        exit(1)

    print(f"Found __UNIVERSAL_DATA_FOR_REHYDRATION__ script")
    print(f"JSON length: {len(matches[0])} characters")

    # Parse JSON
    data = json.loads(matches[0])

    print("\nJSON structure keys:")
    print(f"  Root keys: {list(data.keys())}")

    if '__DEFAULT_SCOPE__' in data:
        print(f"  __DEFAULT_SCOPE__ keys: {list(data['__DEFAULT_SCOPE__'].keys())}")

        if 'webapp.video-detail' in data['__DEFAULT_SCOPE__']:
            video_detail = data['__DEFAULT_SCOPE__']['webapp.video-detail']
            print(f"  webapp.video-detail keys: {list(video_detail.keys())}")

            if 'itemInfo' in video_detail:
                item_info = video_detail['itemInfo']
                print(f"  itemInfo keys: {list(item_info.keys())}")

                if 'itemStruct' in item_info:
                    item_struct = item_info['itemStruct']
                    print(f"  itemStruct keys: {list(item_struct.keys())}")

                    if 'music' in item_struct:
                        music = item_struct['music']
                        print(f"\n{'=' * 80}")
                        print("MUSIC DATA FOUND:")
                        print(f"{'=' * 80}")
                        print(json.dumps(music, indent=2))

                        sound_id = music.get('id')
                        song_title = music.get('title', '')
                        author_name = music.get('authorName', '')

                        print(f"\n{'=' * 80}")
                        print("EXTRACTED VALUES:")
                        print(f"{'=' * 80}")
                        print(f"Sound ID: {sound_id}")
                        print(f"Song Title: {song_title}")
                        print(f"Author Name: {author_name}")

                        # Check if it matches our target
                        target_id = "7582024313956518711"
                        print(f"\nTarget Sound ID: {target_id}")
                        if str(sound_id) == target_id:
                            print("[MATCH] This video uses the target sound!")
                        else:
                            print(f"[NO MATCH] This video uses a different sound")
                            print(f"  Expected: {target_id}")
                            print(f"  Found:    {sound_id}")
                    else:
                        print("\nERROR: No 'music' key in itemStruct")
                        print(f"Available keys: {list(item_struct.keys())}")
                else:
                    print("\nERROR: No 'itemStruct' in itemInfo")
            else:
                print("\nERROR: No 'itemInfo' in video-detail")
        else:
            print("\nERROR: No 'webapp.video-detail' in __DEFAULT_SCOPE__")
    else:
        print("\nERROR: No '__DEFAULT_SCOPE__' in data")

except Exception as e:
    print(f"\nEXCEPTION: {e}")
    import traceback
    traceback.print_exc()
