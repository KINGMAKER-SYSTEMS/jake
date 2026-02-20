#!/usr/bin/env python3
"""
Scrape accounts from CSV for "Fight Song (Rachel's Version)" by Rachel Platten
"""
import sys
import csv
from pathlib import Path
from datetime import datetime

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
    # Read accounts from CSV
    csv_path = Path('output') / 'Fight_Song_Rachel_Platten_campaign.csv'
    
    accounts = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            account_url = row['Account']
            # Extract username from URL
            if '@' in account_url:
                username = account_url.split('@')[1].split('/')[0]
                accounts.append(username)
    
    print("=" * 80)
    print("SCRAPING 'FIGHT SONG (RACHEL'S VERSION)' CAMPAIGN")
    print("=" * 80)
    print(f"\nAccounts to scrape: {len(accounts)}")
    for acc in accounts:
        print(f"  - @{acc}")
    
    # Start date: December 3, 2025
    start_date = datetime(2025, 12, 3, 0, 0)
    end_date = datetime.now()
    
    print(f"\nDate range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    target_song = 'Fight Song'
    target_artist = 'Rachel Platten'
    
    all_videos = []
    
    # Scrape each account
    for account in accounts:
        print(f"\nScraping @{account}...")
        videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)
        all_videos.extend(videos)
    
    # Filter for matching song
    matching_videos = [v for v in all_videos if matches_song(v, target_song, target_artist)]
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total videos scraped: {len(all_videos)}")
    print(f"Matching videos: {len(matching_videos)}")
    
    if matching_videos:
        # Group by account
        from collections import defaultdict
        by_account = defaultdict(list)
        for video in matching_videos:
            by_account[video['account']].append(video)
        
        # Sort by total views per account
        account_totals = {acc: sum(v['views'] for v in videos) for acc, videos in by_account.items()}
        sorted_accounts = sorted(account_totals.items(), key=lambda x: x[1], reverse=True)
        
        total_views = sum(v['views'] for v in matching_videos)
        total_likes = sum(v['likes'] for v in matching_videos)
        
        print(f"\nTotal Views: {total_views:,}")
        print(f"Total Likes: {total_likes:,}")
        
        print(f"\nBreakdown by Account:")
        for account, _ in sorted_accounts:
            videos = by_account[account]
            account_views = sum(v['views'] for v in videos)
            account_likes = sum(v['likes'] for v in videos)
            print(f"  {account}: {len(videos)} videos, {account_views:,} views, {account_likes:,} likes")
        
        # Save results
        output_file = Path('output') / 'Fight_Song_scrape_results.txt'
        copy_paste_file = Path('output') / 'Fight_Song_copy_paste.txt'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"FIGHT SONG (RACHEL'S VERSION) - SCRAPE RESULTS\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Total matching videos: {len(matching_videos)}\n")
            f.write(f"Total views: {total_views:,}\n")
            f.write(f"Total likes: {total_likes:,}\n\n")
            
            for account, _ in sorted_accounts:
                videos = sorted(by_account[account], key=lambda x: x['views'], reverse=True)
                f.write(f"\n{account}:\n")
                f.write("-" * 80 + "\n")
                for video in videos:
                    f.write(f"  {video['url']}\n")
                    f.write(f"    Views: {video['views']:,} | Likes: {video['likes']:,}\n")
        
        with open(copy_paste_file, 'w', encoding='utf-8') as f:
            f.write(f"FIGHT SONG (RACHEL'S VERSION) - COPY/PASTE FORMAT\n")
            f.write("=" * 80 + "\n\n")
            for account, _ in sorted_accounts:
                videos = sorted(by_account[account], key=lambda x: x['views'], reverse=True)
                for video in videos:
                    f.write(f"{video['url']}\n")
        
        print(f"\n[SUCCESS] Results saved to:")
        print(f"  Detailed: {output_file}")
        print(f"  Copy/Paste: {copy_paste_file}")
    else:
        print("\n[X] No matching videos found")
    
    print("=" * 80)

if __name__ == '__main__':
    main()

