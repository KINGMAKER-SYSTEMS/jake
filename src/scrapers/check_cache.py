import pickle
import os

cache_file = 'cache/tiktok_onlyupset__cache.pkl'
target_sound = '7582646433275317023'

if os.path.exists(cache_file):
    cache = pickle.load(open(cache_file, 'rb'))
    print(f"Total videos in cache: {len(cache['videos'])}")
    
    videos = cache['videos']
    print(f"Type of videos: {type(videos)}")
    
    if isinstance(videos, list):
        matches = []
        for v in videos:
            sound_id = v.get('sound_id', '') if isinstance(v, dict) else ''
            if sound_id == target_sound:
                matches.append(v.get('id', 'unknown'))
        
        print(f"\nVideos matching sound {target_sound}: {len(matches)}")
        for m in matches[:10]:
            print(f"  - {m}")
        
        # Show first entry structure
        print("\nFirst video entry structure:")
        if videos:
            v = videos[0]
            if isinstance(v, dict):
                for k, val in v.items():
                    print(f"  {k}: {str(val)[:100]}")
            else:
                print(f"  Entry type: {type(v)}, value: {v}")
else:
    print(f"Cache file not found: {cache_file}")
