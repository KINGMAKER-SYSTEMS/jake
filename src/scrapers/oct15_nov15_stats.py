#!/usr/bin/env python3
"""
Scrape beau, cody, and gavin for statistics between October 15 and November 15
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.get_post_links_by_song import scrape_account_videos

def scrape_account(account, start_date, end_date):
    """Scrape an account and return statistics"""
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
            'top_video_url': '',
            'videos_list': []
        }
    
    videos_by_views = sorted(videos, key=lambda x: x['views'], reverse=True)
    total_views = sum(v['views'] for v in videos)
    total_likes = sum(v['likes'] for v in videos)
    avg_views = total_views // len(videos) if videos else 0
    
    return {
        'account': account,
        'videos': len(videos),
        'total_views': total_views,
        'total_likes': total_likes,
        'avg_views': avg_views,
        'top_video_views': videos_by_views[0]['views'] if videos_by_views else 0,
        'top_video_url': videos_by_views[0]['url'] if videos_by_views else '',
        'videos_list': videos_by_views
    }

def main():
    start_date = datetime(2025, 10, 15, 0, 0)  # October 15, 2025
    end_date = datetime(2025, 11, 15, 0, 0)    # November 15, 2025
    
    accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']
    
    print("=" * 80)
    print("STATISTICS FOR OCTOBER 15 - NOVEMBER 15, 2025")
    print("=" * 80)
    print(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"Accounts: {', '.join([f'@{acc}' for acc in accounts])}")
    print("=" * 80)
    
    # Scrape all accounts
    results = {}
    for account in accounts:
        results[account] = scrape_account(account, start_date, end_date)
    
    # Print summary
    print("\n" + "=" * 80)
    print("STATISTICS SUMMARY")
    print("=" * 80)
    
    for account in accounts:
        stats = results[account]
        print(f"\n@{stats['account']}:")
        print(f"  Total Videos: {stats['videos']}")
        print(f"  Total Views: {stats['total_views']:,}")
        print(f"  Total Likes: {stats['total_likes']:,}")
        if stats['videos'] > 0:
            print(f"  Average Views per Video: {stats['avg_views']:,}")
            print(f"  Top Video Views: {stats['top_video_views']:,}")
            if stats['top_video_url']:
                print(f"  Top Video: {stats['top_video_url']}")
    
    # Combined totals
    total_videos = sum(r['videos'] for r in results.values())
    total_views = sum(r['total_views'] for r in results.values())
    total_likes = sum(r['total_likes'] for r in results.values())
    combined_avg = total_views // total_videos if total_videos > 0 else 0
    
    print(f"\n{'=' * 80}")
    print("COMBINED TOTALS")
    print("=" * 80)
    print(f"Total Videos (All 3 Accounts): {total_videos}")
    print(f"Total Views (All 3 Accounts): {total_views:,}")
    print(f"Total Likes (All 3 Accounts): {total_likes:,}")
    print(f"Combined Average Views per Video: {combined_avg:,}")
    
    # Ranking
    print(f"\n{'=' * 80}")
    print("RANKING BY TOTAL VIEWS")
    print("=" * 80)
    sorted_by_views = sorted(results.items(), key=lambda x: x[1]['total_views'], reverse=True)
    for i, (account, stats) in enumerate(sorted_by_views, 1):
        print(f"{i}. @{stats['account']}: {stats['total_views']:,} views ({stats['videos']} videos)")
    
    # Top videos across all accounts
    print(f"\n{'=' * 80}")
    print("TOP 10 VIDEOS (All Accounts Combined)")
    print("=" * 80)
    all_videos = []
    for account in accounts:
        all_videos.extend(results[account]['videos_list'])
    
    all_sorted = sorted(all_videos, key=lambda x: x['views'], reverse=True)
    for i, video in enumerate(all_sorted[:10], 1):
        date_str = video['timestamp'].strftime('%Y-%m-%d') if video.get('timestamp') else 'Unknown'
        print(f"{i:2}. {video['account']} - {video['views']:,} views | {video['likes']:,} likes | {date_str}")
        print(f"    {video['url']}")
    
    # Save to file
    output_file = Path('output') / 'oct15_nov15_statistics.txt'
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("STATISTICS - OCTOBER 15 TO NOVEMBER 15, 2025\n")
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
            if stats['videos'] > 0:
                f.write(f"  Average Views per Video: {stats['avg_views']:,}\n")
                f.write(f"  Top Video Views: {stats['top_video_views']:,}\n")
                if stats['top_video_url']:
                    f.write(f"  Top Video: {stats['top_video_url']}\n")
        
        f.write(f"\n{'=' * 80}\n")
        f.write("COMBINED TOTALS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Videos (All 3 Accounts): {total_videos}\n")
        f.write(f"Total Views (All 3 Accounts): {total_views:,}\n")
        f.write(f"Total Likes (All 3 Accounts): {total_likes:,}\n")
        f.write(f"Combined Average Views per Video: {combined_avg:,}\n")
        
        f.write(f"\n{'=' * 80}\n")
        f.write("RANKING BY TOTAL VIEWS\n")
        f.write("=" * 80 + "\n")
        for i, (account, stats) in enumerate(sorted_by_views, 1):
            f.write(f"{i}. @{stats['account']}: {stats['total_views']:,} views ({stats['videos']} videos)\n")
        
        f.write(f"\n{'=' * 80}\n")
        f.write("TOP 20 VIDEOS (All Accounts Combined)\n")
        f.write("=" * 80 + "\n\n")
        for i, video in enumerate(all_sorted[:20], 1):
            date_str = video['timestamp'].strftime('%Y-%m-%d %H:%M') if video.get('timestamp') else 'Unknown date'
            song = video.get('song', 'Unknown')
            artist = video.get('artist', 'Unknown')
            f.write(f"{i}. {video['account']} - {video['views']:,} views | {video['likes']:,} likes\n")
            f.write(f"   Date: {date_str}\n")
            f.write(f"   {video['url']}\n")
            if song != 'Unknown':
                f.write(f"   Song: {song} - {artist}\n")
            f.write("\n")
    
    print(f"\n{'=' * 80}")
    print(f"[SUCCESS] Results saved to: {output_file}")
    print(f"{'=' * 80}\n")

if __name__ == '__main__':
    main()

