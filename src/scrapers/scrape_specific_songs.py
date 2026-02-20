#!/usr/bin/env python3
"""
Scrape a specific TikTok account for specific songs
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.get_post_links_by_song import scrape_account_videos

def matches_song(video, song_name, artist_name):
    """Check if video matches song name and artist (case-insensitive, partial match)"""
    video_song = video.get('song', '').lower()
    video_artist = video.get('artist', '').lower()
    
    song_match = song_name.lower() in video_song or video_song in song_name.lower()
    artist_match = artist_name.lower() in video_artist or video_artist in artist_name.lower()
    
    return song_match and artist_match

def main():
    account = 'eeryyxx'
    start_date = datetime(2025, 10, 24, 0, 0)  # October 24, 2025
    end_date = datetime.now()
    
    # Songs to search for
    target_songs = [
        {'song': 'neversleep', 'artist': 'colorblind'},
        {'song': 'one hit wonder', 'artist': 'attack attack'}
    ]
    
    print("=" * 80)
    print(f"SCRAPING @{account} FOR SPECIFIC SONGS")
    print("=" * 80)
    print(f"\nSearching for:")
    for song_info in target_songs:
        print(f"  - {song_info['song']} by {song_info['artist']}")
    print(f"\nDate range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    print()
    
    # Scrape account
    all_videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=1000)
    
    print(f"\nTotal videos found in date range: {len(all_videos)}")
    
    # Filter for target songs
    matched_videos = []
    for video in all_videos:
        for song_info in target_songs:
            if matches_song(video, song_info['song'], song_info['artist']):
                matched_videos.append({
                    **video,
                    'target_song': song_info['song'],
                    'target_artist': song_info['artist']
                })
                break
    
    print(f"Videos matching target songs: {len(matched_videos)}\n")
    
    # Group by song
    from collections import defaultdict
    songs_dict = defaultdict(list)
    
    for video in matched_videos:
        song_key = f"{video['target_song']} - {video['target_artist']}"
        songs_dict[song_key].append(video)
    
    # Print results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    if not matched_videos:
        print("\nNo videos found matching the specified songs.")
    else:
        for song_key, videos in sorted(songs_dict.items()):
            print(f"\n{'=' * 80}")
            print(f"SONG: {song_key}")
            print(f"Total Videos: {len(videos)}")
            
            # Calculate totals
            total_views = sum(v['views'] for v in videos)
            total_likes = sum(v['likes'] for v in videos)
            print(f"Total Views: {total_views:,}")
            print(f"Total Likes: {total_likes:,}")
            print(f"\nPost Links:")
            print("-" * 80)
            
            # Sort by views descending
            sorted_videos = sorted(videos, key=lambda x: x['views'], reverse=True)
            
            for i, video in enumerate(sorted_videos, 1):
                date_str = video['timestamp'].strftime('%Y-%m-%d') if video.get('timestamp') else 'Unknown date'
                print(f"  {i}. {video['url']}")
                print(f"     Date: {date_str} | Views: {video['views']:,} | Likes: {video['likes']:,}")
    
    # Save to file
    output_file = Path('output') / f'specific_songs_{account}.txt'
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"SPECIFIC SONGS SEARCH RESULTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Account: @{account}\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        if not matched_videos:
            f.write("No videos found matching the specified songs.\n")
        else:
            for song_key, videos in sorted(songs_dict.items()):
                f.write(f"\n{'=' * 80}\n")
                f.write(f"SONG: {song_key}\n")
                f.write(f"Total Videos: {len(videos)}\n")
                
                total_views = sum(v['views'] for v in videos)
                total_likes = sum(v['likes'] for v in videos)
                f.write(f"Total Views: {total_views:,}\n")
                f.write(f"Total Likes: {total_likes:,}\n")
                f.write(f"\nPost Links:\n")
                f.write("-" * 80 + "\n")
                
                sorted_videos = sorted(videos, key=lambda x: x['views'], reverse=True)
                for i, video in enumerate(sorted_videos, 1):
                    date_str = video['timestamp'].strftime('%Y-%m-%d') if video.get('timestamp') else 'Unknown date'
                    f.write(f"  {i}. {video['url']}\n")
                    f.write(f"     Date: {date_str} | Views: {video['views']:,} | Likes: {video['likes']:,}\n")
    
    print(f"\n{'=' * 80}")
    print(f"[SUCCESS] Results saved to: {output_file}")
    print(f"{'=' * 80}\n")

if __name__ == '__main__':
    main()

