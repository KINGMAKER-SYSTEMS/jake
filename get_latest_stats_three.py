#!/usr/bin/env python3
"""
Get the most up-to-date statistics for Beau, Gavin, and Cody
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.get_post_links_by_song import scrape_account_videos

def main():
    start_date = datetime(2025, 11, 15, 0, 0)
    end_date = datetime.now()

    accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']

    print("=" * 80)
    print("LATEST STATISTICS - BEAU, CODY & GAVIN")
    print("=" * 80)
    print(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    all_stats = []

    for account in accounts:
        print(f"\nScraping @{account}...")
        videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)

        total_views = sum(v['views'] for v in videos)
        total_likes = sum(v['likes'] for v in videos)
        avg_views = total_views // len(videos) if videos else 0

        # Find top video
        top_video = max(videos, key=lambda v: v['views']) if videos else None

        stats = {
            'account': account,
            'total_videos': len(videos),
            'total_views': total_views,
            'total_likes': total_likes,
            'avg_views': avg_views,
            'top_video': top_video
        }
        all_stats.append(stats)

        print(f"  Total Videos: {len(videos)}")
        print(f"  Total Views: {total_views:,}")
        print(f"  Total Likes: {total_likes:,}")
        print(f"  Average Views per Video: {avg_views:,}")
        if top_video:
            print(f"  Top Video Views: {top_video['views']:,}")
            print(f"  Top Video: {top_video.get('link', top_video.get('url', 'N/A'))}")

    # Calculate combined totals
    total_videos_all = sum(s['total_videos'] for s in all_stats)
    total_views_all = sum(s['total_views'] for s in all_stats)
    total_likes_all = sum(s['total_likes'] for s in all_stats)
    combined_avg = total_views_all // total_videos_all if total_videos_all else 0

    # Save to file
    output_file = Path('output') / 'latest_stats_beau_cody_gavin.txt'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("LATEST UPDATE - BEAU, CODY & GAVIN STATISTICS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("STATISTICS SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        for stats in all_stats:
            f.write(f"@{stats['account']}:\n")
            f.write(f"  Total Videos: {stats['total_videos']}\n")
            f.write(f"  Total Views: {stats['total_views']:,}\n")
            f.write(f"  Total Likes: {stats['total_likes']:,}\n")
            f.write(f"  Average Views per Video: {stats['avg_views']:,}\n")
            if stats['top_video']:
                f.write(f"  Top Video Views: {stats['top_video']['views']:,}\n")
                f.write(f"  Top Video: {stats['top_video'].get('link', stats['top_video'].get('url', 'N/A'))}\n")
            f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("COMBINED TOTALS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Videos (All 3 Accounts): {total_videos_all}\n")
        f.write(f"Total Views (All 3 Accounts): {total_views_all:,}\n")
        f.write(f"Total Likes (All 3 Accounts): {total_likes_all:,}\n")
        f.write(f"Combined Average Views per Video: {combined_avg:,}\n\n")

        f.write("=" * 80 + "\n")
        f.write("RANKING BY TOTAL VIEWS\n")
        f.write("=" * 80 + "\n")
        sorted_stats = sorted(all_stats, key=lambda x: x['total_views'], reverse=True)
        for i, stats in enumerate(sorted_stats, 1):
            f.write(f"{i}. @{stats['account']}: {stats['total_views']:,} views ({stats['total_videos']} videos)\n")
        f.write("\n")

    print("\n" + "=" * 80)
    print("COMBINED TOTALS")
    print("=" * 80)
    print(f"Total Videos (All 3 Accounts): {total_videos_all}")
    print(f"Total Views (All 3 Accounts): {total_views_all:,}")
    print(f"Total Likes (All 3 Accounts): {total_likes_all:,}")
    print(f"Combined Average Views per Video: {combined_avg:,}")

    print("\n" + "=" * 80)
    print("RANKING BY TOTAL VIEWS")
    print("=" * 80)
    sorted_stats = sorted(all_stats, key=lambda x: x['total_views'], reverse=True)
    for i, stats in enumerate(sorted_stats, 1):
        print(f"{i}. @{stats['account']}: {stats['total_views']:,} views ({stats['total_videos']} videos)")

    print("\n" + "=" * 80)
    print(f"Results saved to: {output_file}")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    main()
