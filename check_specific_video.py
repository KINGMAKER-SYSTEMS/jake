import yt_dlp
import json
from datetime import datetime

# Video to check
video_url = "https://www.tiktok.com/@somethingicouldntsay/video/7589280138232155399"

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}

print(f"Checking video: {video_url}")
print("=" * 80)

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)

        # Get basic info
        title = info.get('title', 'N/A')
        description = info.get('description', 'N/A')
        upload_date = info.get('upload_date', 'N/A')
        views = info.get('view_count', 0)
        likes = info.get('like_count', 0)

        # Format date
        if upload_date != 'N/A':
            formatted_date = datetime.strptime(upload_date, '%Y%m%d').strftime('%Y-%m-%d')
        else:
            formatted_date = 'N/A'

        print(f"Title: {title}")
        print(f"Description: {description}")
        print(f"Upload Date: {formatted_date}")
        print(f"Views: {views:,}")
        print(f"Likes: {likes:,}")
        print()

        # Try to extract sound ID from description
        sound_id = None
        if 'music' in info:
            music_info = info['music']
            print(f"Music info found: {music_info}")

        # Check for creator in description (TikTok often includes sound info)
        if 'creator' in info:
            print(f"Creator: {info['creator']}")

        # Look for sound/music ID in various fields
        print("\nSearching for sound ID...")
        print("-" * 80)

        # Method 1: Check if there's a music/sound field
        if 'music_id' in info:
            sound_id = info['music_id']
            print(f"Found music_id: {sound_id}")

        # Method 2: Parse from description (common TikTok format)
        if description and 'original sound' in description.lower():
            print(f"Description mentions 'original sound'")
            # Look for patterns like "original sound - username"
            if '-' in description:
                parts = description.split('-')
                for part in parts:
                    if 'original sound' in part.lower():
                        print(f"  Found in description: {part.strip()}")

        # Method 3: Check the full JSON structure for sound-related fields
        print("\nFull info keys available:")
        for key in sorted(info.keys()):
            if 'music' in key.lower() or 'sound' in key.lower() or 'audio' in key.lower():
                print(f"  {key}: {info[key]}")

        print("\n" + "=" * 80)
        print("DUMPING FULL JSON (looking for sound ID):")
        print("=" * 80)

        # Dump the full JSON to see everything
        json_str = json.dumps(info, indent=2, default=str)

        # Search for potential sound IDs (typically 19-digit numbers)
        import re
        potential_ids = re.findall(r'\b7\d{18}\b', json_str)

        if potential_ids:
            print(f"\nPotential sound IDs found (19-digit numbers starting with 7):")
            for pid in set(potential_ids):
                print(f"  {pid}")
            print()

            # Check if our target sound ID is in there
            target_id = "7582024313956518711"
            if target_id in potential_ids:
                print(f"[MATCH] TARGET SOUND ID {target_id} FOUND!")
            else:
                print(f"[NO MATCH] Target sound ID {target_id} NOT found")
                print(f"  We're looking for: {target_id}")
                print(f"  Found instead: {[pid for pid in potential_ids if pid != '7589280138232155399']}")

        # Find where the sound IDs appear in the JSON
        print("\nSearching JSON structure for sound IDs:")
        print("-" * 80)

        def find_in_dict(d, target_ids, path=""):
            """Recursively search for target IDs in nested dict/list structures"""
            if isinstance(d, dict):
                for key, value in d.items():
                    new_path = f"{path}.{key}" if path else key
                    if isinstance(value, (str, int)):
                        value_str = str(value)
                        for tid in target_ids:
                            if tid in value_str:
                                print(f"  Found {tid} at: {new_path} = {value}")
                    elif isinstance(value, (dict, list)):
                        find_in_dict(value, target_ids, new_path)
            elif isinstance(d, list):
                for i, item in enumerate(d):
                    new_path = f"{path}[{i}]"
                    find_in_dict(item, target_ids, new_path)

        if potential_ids:
            non_video_ids = [pid for pid in potential_ids if pid != '7589280138232155399']
            if non_video_ids:
                find_in_dict(info, non_video_ids)

        # Print relevant parts of JSON
        print("\nRelevant JSON fields:")
        for key in ['description', 'title', 'uploader', 'uploader_id', 'webpage_url']:
            if key in info:
                print(f"  {key}: {info[key]}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
