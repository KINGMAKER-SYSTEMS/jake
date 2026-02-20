"""Debug a mini run to see what's happening with sound ID extraction"""
import pickle
from master_tracker import extract_sound_ids_parallel, match_video_to_sounds

# Load a subset of videos from cache
cache = pickle.load(open('cache/tiktok_onlyupset__cache.pkl', 'rb'))
test_videos = cache['videos'][:5]  # Just test 5 videos

print("Original videos:")
for v in test_videos:
    print(f"  {v['url'][:60]}... | sound_id: {v.get('extracted_sound_id', 'NONE')}")

# Run extraction
print("\nExtracting sound IDs...")
enhanced = extract_sound_ids_parallel(test_videos, max_workers=3)

print("\nAfter extraction:")
for v in enhanced:
    print(f"  {v['url'][:60]}... | extracted_sound_id: {v.get('extracted_sound_id', 'NONE')}")

# Test matching
sound_ids = {'7582646433275317023'}
sound_keys = {'teach me how to dougie mashup - malcolm todd'}

print(f"\nMatching against sound_ids: {sound_ids}")
for v in enhanced:
    matched = match_video_to_sounds(v, sound_ids, sound_keys)
    print(f"  {v.get('extracted_sound_id', 'NONE')} -> Match: {matched}")
