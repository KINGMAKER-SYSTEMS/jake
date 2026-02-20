#!/usr/bin/env python3
"""
Scrape specific accounts for "Falling Away from Heaven" by Nate Vickers
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.get_post_links_by_song import scrape_account_videos

def matches_song(video, song_name, artist_name):
    """Check if video matches song name and artist (case-insensitive, partial match)"""
    video_song = video.get('song', '').lower().strip()
    video_artist = video.get('artist', '').lower().strip()
    
    # More flexible matching - check if key words match
    song_keywords = song_name.lower().split()
    artist_keywords = artist_name.lower().split()
    
    # Song match: check if all keywords are present OR if song name is contained
    song_match = (
        song_name.lower() in video_song or 
        video_song in song_name.lower() or
        all(keyword in video_song for keyword in song_keywords if len(keyword) > 2)
    )
    
    # Artist match: check if artist name is contained or key part matches
    artist_match = (
        artist_name.lower() in video_artist or 
        video_artist in artist_name.lower() or
        any(keyword in video_artist for keyword in artist_keywords if len(keyword) > 2)
    )
    
    return song_match and artist_match

def main():
    # Accounts to scrape
    accounts = [
        'enzowms',
        'enzorealasf'
    ]
    
    start_date = datetime(2025, 11, 5, 0, 0)  # November 5, 2025
    end_date = datetime.now()
    
    # Song to search for
    target_song = 'Falling Away from Heaven'
    target_artist = 'Nate Vickers'
    
    print("=" * 80)
    print(f"SCRAPING ACCOUNTS FOR: {target_song} by {target_artist}")
    print("=" * 80)
    print(f"\nAccounts to scrape:")
    for account in accounts:
        print(f"  - @{account}")
    print(f"\nDate range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    print()
    
    # Scrape all accounts
    all_videos = []
    for account in accounts:
        videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)
        all_videos.extend(videos)
    
    print(f"\nTotal videos found in date range: {len(all_videos)}")
    
    # Filter for target song
    matched_videos = []
    for video in all_videos:
        if matches_song(video, target_song, target_artist):
            matched_videos.append(video)
    
    print(f"Videos matching '{target_song}' by {target_artist}: {len(matched_videos)}\n")
    
    # Group by account
    from collections import defaultdict
    accounts_dict = defaultdict(list)
    
    for video in matched_videos:
        account = video['account']
        accounts_dict[account].append(video)
    
    # Print results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    
    if not matched_videos:
        print("\nNo videos found matching the specified song.")
    else:
        # Sort accounts by total views
        accounts_sorted = sorted(accounts_dict.items(), 
                                key=lambda x: sum(v['views'] for v in x[1]), 
                                reverse=True)
        
        total_views = sum(v['views'] for v in matched_videos)
        total_likes = sum(v['likes'] for v in matched_videos)
        
        print(f"\nSUMMARY:")
        print(f"  Total Videos: {len(matched_videos)}")
        print(f"  Total Views: {total_views:,}")
        print(f"  Total Likes: {total_likes:,}")
        print(f"  Accounts with videos: {len(accounts_dict)}")
        
        for account, videos in accounts_sorted:
            account_views = sum(v['views'] for v in videos)
            account_likes = sum(v['likes'] for v in videos)
            print(f"\n{'=' * 80}")
            print(f"ACCOUNT: {account}")
            print(f"Videos: {len(videos)} | Views: {account_views:,} | Likes: {account_likes:,}")
            print(f"\nPost Links:")
            print("-" * 80)
            
            # Sort by views descending
            sorted_videos = sorted(videos, key=lambda x: x['views'], reverse=True)
            
            for i, video in enumerate(sorted_videos, 1):
                date_str = video['timestamp'].strftime('%Y-%m-%d') if video.get('timestamp') else 'Unknown date'
                print(f"  {i}. {video['url']}")
                print(f"     Date: {date_str} | Views: {video['views']:,} | Likes: {video['likes']:,}")
    
    # Save to file
    output_file = Path('output') / 'falling_away_scrape_results.txt'
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"FALLING AWAY FROM HEAVEN - NATE VICKERS SCRAPE RESULTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        if not matched_videos:
            f.write("No videos found matching the specified song.\n")
        else:
            total_views = sum(v['views'] for v in matched_videos)
            total_likes = sum(v['likes'] for v in matched_videos)
            
            f.write(f"SUMMARY:\n")
            f.write(f"  Total Videos: {len(matched_videos)}\n")
            f.write(f"  Total Views: {total_views:,}\n")
            f.write(f"  Total Likes: {total_likes:,}\n")
            f.write(f"  Accounts with videos: {len(accounts_dict)}\n\n")
            
            accounts_sorted = sorted(accounts_dict.items(), 
                                    key=lambda x: sum(v['views'] for v in x[1]), 
                                    reverse=True)
            
            for account, videos in accounts_sorted:
                account_views = sum(v['views'] for v in videos)
                account_likes = sum(v['likes'] for v in videos)
                f.write(f"\n{'=' * 80}\n")
                f.write(f"ACCOUNT: {account}\n")
                f.write(f"Videos: {len(videos)} | Views: {account_views:,} | Likes: {account_likes:,}\n")
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

