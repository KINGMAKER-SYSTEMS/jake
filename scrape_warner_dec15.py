#!/usr/bin/env python3
"""
Scrape beau, cody, gavin, and coffee.yearnings from Dec 15 onwards
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent / 'src'))

from utils.get_post_links_by_song import scrape_account_videos

def scrape_account(account, start_date, end_date):
    """Scrape an account and return videos and statistics"""
    print(f"\nScraping @{account}...")
    videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)

    if not videos:
        return {
            'account': account,
            'videos': [],
            'count': 0,
            'total_views': 0,
            'total_likes': 0,
            'avg_views': 0,
            'top_video_views': 0,
            'top_video_url': ''
        }

    videos_by_views = sorted(videos, key=lambda x: x['views'], reverse=True)
    total_views = sum(v['views'] for v in videos)
    total_likes = sum(v['likes'] for v in videos)
    avg_views = total_views // len(videos) if videos else 0

    return {
        'account': account,
        'videos': videos,
        'count': len(videos),
        'total_views': total_views,
        'total_likes': total_likes,
        'avg_views': avg_views,
        'top_video_views': videos_by_views[0]['views'] if videos_by_views else 0,
        'top_video_url': videos_by_views[0]['url'] if videos_by_views else ''
    }

def main():
    start_date = datetime(2025, 12, 15, 0, 0)
    end_date = datetime.now()

    accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1', 'coffee.yearnings']

    print("=" * 80)
    print("WARNER CAMPAIGN - ALL 4 ACCOUNTS")
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
    print("STATISTICS SUMMARY (Dec 15 - Now)")
    print("=" * 80)

    for account in accounts:
        stats = results[account]
        print(f"\n@{stats['account']}:")
        print(f"  Total Videos: {stats['count']}")
        print(f"  Total Views: {stats['total_views']:,}")
        print(f"  Total Likes: {stats['total_likes']:,}")
        print(f"  Average Views per Video: {stats['avg_views']:,}")
        print(f"  Top Video Views: {stats['top_video_views']:,}")

    # Combined totals
    total_videos = sum(r['count'] for r in results.values())
    total_views = sum(r['total_views'] for r in results.values())
    total_likes = sum(r['total_likes'] for r in results.values())
    combined_avg = total_views // total_videos if total_videos > 0 else 0

    print(f"\n{'=' * 80}")
    print("COMBINED TOTALS")
    print("=" * 80)
    print(f"Total Videos (All 4 Accounts): {total_videos}")
    print(f"Total Views (All 4 Accounts): {total_views:,}")
    print(f"Total Likes (All 4 Accounts): {total_likes:,}")
    print(f"Combined Average Views per Video: {combined_avg:,}")

    # Ranking
    print(f"\n{'=' * 80}")
    print("RANKING BY TOTAL VIEWS")
    print("=" * 80)
    sorted_by_views = sorted(results.items(), key=lambda x: x[1]['total_views'], reverse=True)
    for i, (account, stats) in enumerate(sorted_by_views, 1):
        print(f"{i}. @{stats['account']}: {stats['total_views']:,} views ({stats['count']} videos)")

    # Save CSV with all video data
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = Path('output') / f"warner_4_accounts_dec15_{timestamp}.csv"
    csv_file.parent.mkdir(exist_ok=True)

    # Combine all videos into one dataframe
    all_videos = []
    for account in accounts:
        for video in results[account]['videos']:
            video['account'] = f'@{account}'
            all_videos.append(video)

    import pandas as pd
    df = pd.DataFrame(all_videos)
    df.to_csv(csv_file, index=False)

    # Save stats to file
    output_file = Path('output') / f"warner_4_accounts_dec15_{timestamp}.txt"
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("WARNER CAMPAIGN - ALL 4 ACCOUNTS STATISTICS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("STATISTICS SUMMARY\n")
        f.write("=" * 80 + "\n")

        for account in accounts:
            stats = results[account]
            f.write(f"\n@{stats['account']}:\n")
            f.write(f"  Total Videos: {stats['count']}\n")
            f.write(f"  Total Views: {stats['total_views']:,}\n")
            f.write(f"  Total Likes: {stats['total_likes']:,}\n")
            f.write(f"  Average Views per Video: {stats['avg_views']:,}\n")
            f.write(f"  Top Video Views: {stats['top_video_views']:,}\n")
            if stats['top_video_url']:
                f.write(f"  Top Video: {stats['top_video_url']}\n")

        f.write(f"\n{'=' * 80}\n")
        f.write("COMBINED TOTALS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Videos (All 4 Accounts): {total_videos}\n")
        f.write(f"Total Views (All 4 Accounts): {total_views:,}\n")
        f.write(f"Total Likes (All 4 Accounts): {total_likes:,}\n")
        f.write(f"Combined Average Views per Video: {combined_avg:,}\n")

        f.write(f"\n{'=' * 80}\n")
        f.write("RANKING BY TOTAL VIEWS\n")
        f.write("=" * 80 + "\n")
        for i, (account, stats) in enumerate(sorted_by_views, 1):
            f.write(f"{i}. @{stats['account']}: {stats['total_views']:,} views ({stats['count']} videos)\n")

    # Save all links in copy-paste format
    links_file = Path('output') / f"warner_4_accounts_dec15_{timestamp}_links.txt"

    with open(links_file, 'w', encoding='utf-8') as f:
        for account in accounts:
            stats = results[account]
            f.write(f"@{account}:\n")

            # Sort by date (newest first)
            sorted_videos = sorted(stats['videos'], key=lambda x: x.get('timestamp', ''), reverse=True)

            for video in sorted_videos:
                f.write(f"{video['url']}\n")

            f.write("\n")

    print(f"\n{'=' * 80}")
    print(f"[SUCCESS] CSV saved to: {csv_file}")
    print(f"[SUCCESS] Stats saved to: {output_file}")
    print(f"[SUCCESS] Links saved to: {links_file}")
    print(f"{'=' * 80}\n")

if __name__ == '__main__':
    main()
