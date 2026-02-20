"""Quick targeted scrape for Dougie videos from onlyupset_"""
import pickle
from master_tracker import extract_sound_ids_parallel, match_video_to_sounds

target_sound = "7582646433275317023"
sound_ids = {target_sound}
sound_keys = {'teach me how to dougie mashup - malcolm todd'}

# Load all videos from cache
cache = pickle.load(open('cache/tiktok_onlyupset__cache.pkl', 'rb'))
videos = cache['videos']

print(f"Total videos in cache: {len(videos)}")
print(f"Looking for sound: {target_sound}")

# Extract sound IDs (this might take a minute)
print("\nExtracting sound IDs from all videos...")
enhanced = extract_sound_ids_parallel(videos, max_workers=10)

# Find matches
matches = []
for v in enhanced:
    if match_video_to_sounds(v, sound_ids, sound_keys):
        matches.append(v)

print(f"\n\nFOUND {len(matches)} MATCHES!")
for m in matches:
    print(f"  {m['url']}")
    print(f"    uploaded: {m.get('upload_date', 'unknown')}")
    print(f"    sound_id: {m.get('extracted_sound_id', 'unknown')}")
