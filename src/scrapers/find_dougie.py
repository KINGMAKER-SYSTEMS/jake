"""Find the Dougie video in cache and test extraction"""
import pickle
from master_tracker import extract_sound_ids_parallel

target_video_id = "7598681874155818253"  # Jake's video
target_sound = "7582646433275317023"

cache = pickle.load(open('cache/tiktok_onlyupset__cache.pkl', 'rb'))

# Find the Dougie video
dougie_video = None
for v in cache['videos']:
    if target_video_id in v['url']:
        dougie_video = v
        break

if dougie_video:
    print("Found the Dougie video!")
    for k, val in dougie_video.items():
        print(f"  {k}: {val}")
    
    print("\nExtracting sound ID...")
    enhanced = extract_sound_ids_parallel([dougie_video], max_workers=1)
    
    result = enhanced[0]
    extracted = result.get('extracted_sound_id')
    print(f"\nExtracted sound ID: {extracted}")
    print(f"Target sound ID: {target_sound}")
    print(f"MATCH: {extracted == target_sound}")
else:
    print(f"Video {target_video_id} NOT FOUND in cache!")
