#!/usr/bin/env python3
"""
Scrape @beaujenkins and @gavin.wilder1 accounts for videos since November 15th with current view counts
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.get_post_links_by_song import scrape_account_videos

def scrape_and_summarize(account, start_date, end_date):
    """Scrape an account and return summary statistics"""
    print(f"\nScraping @{account}...")
    videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)
    
    if not videos:
        return {
            'account': account,
            'videos': 0,
            'total_views': 0,
            'total_likes': 0,
            'avg_views': 0,
            'top_video_views': 0,
            'videos_list': []
        }
    
    # Sort by views descending
    videos_sorted = sorted(videos, key=lambda x: x['views'], reverse=True)
    
    total_views = sum(v['views'] for v in videos)
    total_likes = sum(v['likes'] for v in videos)
    avg_views = total_views // len(videos) if videos else 0
    
    return {
        'account': account,
        'videos': len(videos),
        'total_views': total_views,
        'total_likes': total_likes,
        'avg_views': avg_views,
        'top_video_views': videos_sorted[0]['views'] if videos_sorted else 0,
        'videos_list': videos_sorted
    }

def main():
    start_date = datetime(2025, 11, 15, 0, 0)  # November 15, 2025
    end_date = datetime.now()
    
    accounts = ['beaujenkins', 'gavin.wilder1']
    
    print("=" * 80)
    print("SCRAPING ACCOUNTS FOR CURRENT VIEW COUNTS")
    print("=" * 80)
    print(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"Accounts: {', '.join([f'@{acc}' for acc in accounts])}")
    print("=" * 80)
    
    # Scrape all accounts
    results = {}
    for account in accounts:
        results[account] = scrape_and_summarize(account, start_date, end_date)
    
    # Print summary statistics
    print("\n" + "=" * 80)
    print("STATISTICS SUMMARY")
    print("=" * 80)
    
    for account in accounts:
        stats = results[account]
        print(f"\n@{stats['account']}:")
        print(f"  Total Videos: {stats['videos']}")
        print(f"  Total Views: {stats['total_views']:,}")
        print(f"  Total Likes: {stats['total_likes']:,}")
        print(f"  Average Views per Video: {stats['avg_views']:,}")
        print(f"  Top Video Views: {stats['top_video_views']:,}")
    
    # Print detailed results
    print("\n" + "=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)
    
    for account in accounts:
        stats = results[account]
        print(f"\n{'=' * 80}")
        print(f"@{stats['account']} - {stats['videos']} videos")
        print("=" * 80)
        
        if stats['videos'] == 0:
            print("No videos found in the specified date range.")
            continue
        
        # Show top 10 videos
        print("\nTop 10 Videos (by views):")
        print("-" * 80)
        for i, video in enumerate(stats['videos_list'][:10], 1):
            date_str = video['timestamp'].strftime('%Y-%m-%d') if video.get('timestamp') else 'Unknown'
            print(f"{i:2}. {video['url']}")
            print(f"    Date: {date_str} | Views: {video['views']:,} | Likes: {video['likes']:,}")
    
    # Save to file
    output_file = Path('output') / 'beau_gavin_views_nov15_now.txt'
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"BEAU JENKINS & GAVIN WILDER - VIEW COUNTS (Nov 15 - Now)\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("STATISTICS SUMMARY\n")
        f.write("=" * 80 + "\n")
        
        for account in accounts:
            stats = results[account]
            f.write(f"\n@{stats['account']}:\n")
            f.write(f"  Total Videos: {stats['videos']}\n")
            f.write(f"  Total Views: {stats['total_views']:,}\n")
            f.write(f"  Total Likes: {stats['total_likes']:,}\n")
            f.write(f"  Average Views per Video: {stats['avg_views']:,}\n")
            f.write(f"  Top Video Views: {stats['top_video_views']:,}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("=" * 80 + "\n")
        
        for account in accounts:
            stats = results[account]
            f.write(f"\n{'=' * 80}\n")
            f.write(f"@{stats['account']} - {stats['videos']} videos\n")
            f.write("=" * 80 + "\n\n")
            
            if stats['videos'] == 0:
                f.write("No videos found in the specified date range.\n\n")
                continue
            
            for i, video in enumerate(stats['videos_list'], 1):
                date_str = video['timestamp'].strftime('%Y-%m-%d %H:%M') if video.get('timestamp') else 'Unknown date'
                song = video.get('song', 'Unknown')
                artist = video.get('artist', 'Unknown')
                f.write(f"{i}. {video['url']}\n")
                f.write(f"   Date: {date_str} | Views: {video['views']:,} | Likes: {video['likes']:,}\n")
                if song != 'Unknown':
                    f.write(f"   Song: {song} - {artist}\n")
                f.write("\n")
    
    print(f"\n{'=' * 80}")
    print(f"[SUCCESS] Results saved to: {output_file}")
    print(f"{'=' * 80}\n")

if __name__ == '__main__':
    main()

