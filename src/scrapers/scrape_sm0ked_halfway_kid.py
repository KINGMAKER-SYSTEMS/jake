#!/usr/bin/env python3
"""
Scrape @sm0ked.999 for all videos using The Halfway Kid sound
"""
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.get_post_links_by_song import scrape_account_videos

def matches_halfway_kid(video):
    """Check if video matches The Halfway Kid (case-insensitive, partial match)"""
    video_song = video.get('song', '').lower()
    video_artist = video.get('artist', '').lower()
    
    # Check for "halfway" in song or artist (more flexible matching)
    # The Halfway Kid might appear as:
    # - Artist: "The Halfway Kid" or "halfway kid" or "halfwaykid"
    # - Song might contain "halfway" or "when i get back on my feet"
    
    # Check if "halfway" appears in artist or song
    if 'halfway' in video_artist or 'halfway' in video_song:
        return True
    
    # Also check for "when i get back on my feet" which is a Halfway Kid song
    if 'when i get back' in video_song or 'when i get back' in video_artist:
        return True
    
    # Check for "halfway kid" as two words
    if 'halfway' in video_artist and 'kid' in video_artist:
        return True
    if 'halfway' in video_song and 'kid' in video_song:
        return True
    
    return False

def main():
    account = 'smoked.999'  # Correct account name from the video URL
    
    print("=" * 80)
    print("SCRAPING @sm0ked.999 FOR THE HALFWAY KID SOUND")
    print("=" * 80)
    print(f"\nAccount: @{account}")
    print("Searching for: The Halfway Kid")
    print("=" * 80)
    
    # Scrape all videos (no date limit to get all)
    print(f"\nScraping @{account}...")
    videos = scrape_account_videos(account, start_datetime=None, end_datetime=None, limit=2000)
    
    print(f"Total videos scraped: {len(videos)}")
    
    # Filter for matching songs
    matching_videos = [v for v in videos if matches_halfway_kid(v)]
    
    print(f"\nMatching videos: {len(matching_videos)}")
    
    if matching_videos:
        # Sort by views (descending)
        sorted_videos = sorted(matching_videos, key=lambda x: x['views'], reverse=True)
        
        total_views = sum(v['views'] for v in matching_videos)
        total_likes = sum(v['likes'] for v in matching_videos)
        
        print("\n" + "=" * 80)
        print("RESULTS")
        print("=" * 80)
        print(f"Total Videos: {len(matching_videos)}")
        print(f"Total Views: {total_views:,}")
        print(f"Total Likes: {total_likes:,}")
        
        print(f"\nVideos (sorted by views):")
        print("-" * 80)
        for i, video in enumerate(sorted_videos, 1):
            print(f"\n{i}. {video['url']}")
            print(f"   Song: {video.get('song', 'Unknown')}")
            print(f"   Artist: {video.get('artist', 'Unknown')}")
            print(f"   Views: {video['views']:,} | Likes: {video['likes']:,}")
            if video.get('timestamp'):
                print(f"   Posted: {video['timestamp'].strftime('%Y-%m-%d %H:%M')}")
        
        # Save results
        output_file = Path(__file__).parent.parent.parent / 'output' / 'sm0ked_halfway_kid_results.txt'
        copy_paste_file = Path(__file__).parent.parent.parent / 'output' / 'sm0ked_halfway_kid_copy_paste.txt'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("SM0KED.999 - THE HALFWAY KID SOUND\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Account: @{account}\n")
            f.write(f"Total matching videos: {len(matching_videos)}\n")
            f.write(f"Total views: {total_views:,}\n")
            f.write(f"Total likes: {total_likes:,}\n\n")
            
            for i, video in enumerate(sorted_videos, 1):
                f.write(f"{i}. {video['url']}\n")
                f.write(f"   Song: {video.get('song', 'Unknown')}\n")
                f.write(f"   Artist: {video.get('artist', 'Unknown')}\n")
                f.write(f"   Views: {video['views']:,} | Likes: {video['likes']:,}\n")
                if video.get('timestamp'):
                    f.write(f"   Posted: {video['timestamp'].strftime('%Y-%m-%d %H:%M')}\n")
                f.write("\n")
        
        with open(copy_paste_file, 'w', encoding='utf-8') as f:
            f.write("SM0KED.999 - THE HALFWAY KID SOUND (COPY/PASTE)\n")
            f.write("=" * 80 + "\n\n")
            for video in sorted_videos:
                f.write(f"{video['url']}\n")
        
        print(f"\n[SUCCESS] Results saved to:")
        print(f"  Detailed: {output_file}")
        print(f"  Copy/Paste: {copy_paste_file}")
    else:
        print("\n[X] No matching videos found")
    
    print("=" * 80)

if __name__ == '__main__':
    main()

