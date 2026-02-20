"""Check if Jake's video was in the scraped set"""
import pickle

# The video Jake sent
target_video_id = "7598681874155818253"

cache_file = 'cache/tiktok_onlyupset__cache.pkl'
cache = pickle.load(open(cache_file, 'rb'))

videos = cache['videos']
print(f"Total videos in cache: {len(videos)}")

# Find the target video
found = False
for v in videos:
    if target_video_id in v.get('url', ''):
        print(f"\nFOUND TARGET VIDEO!")
        for k, val in v.items():
            print(f"  {k}: {val}")
        found = True
        break

if not found:
    print(f"\nTarget video {target_video_id} NOT in cache!")
    
# Show date range of videos
dates = [v.get('upload_date', 'unknown') for v in videos if v.get('upload_date')]
if dates:
    print(f"\nDate range in cache: {min(dates)} to {max(dates)}")
    
# Count by date prefix
from collections import Counter
date_prefixes = [d[:6] if d else 'unknown' for d in dates]  # YYYYMM
print(f"\nVideos by month: {Counter(date_prefixes)}")
