#!/usr/bin/env python3
"""
Get individual account totals from Dec 15 to now
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.get_post_links_by_song import scrape_account_videos

def main():
    start_date = datetime(2025, 12, 15, 0, 0)
    end_date = datetime.now()

    accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']

    print("=" * 80)
    print("INDIVIDUAL ACCOUNT TOTALS - DEC 15 TO NOW")
    print("=" * 80)
    print(f"Date range: {start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y %I:%M %p')}")
    print("=" * 80)

    all_stats = []
    total_videos_all = 0
    total_views_all = 0
    total_likes_all = 0

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

        total_videos_all += len(videos)
        total_views_all += total_views
        total_likes_all += total_likes

        print(f"  Videos: {len(videos)}")
        print(f"  Views: {total_views:,}")
        print(f"  Likes: {total_likes:,}")
        print(f"  Avg Views/Video: {avg_views:,}")

    # Save to file
    output_file = Path('output') / 'individual_account_totals.txt'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("INDIVIDUAL ACCOUNT TOTALS - DEC 15 TO NOW\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%b %d, %Y')} to {end_date.strftime('%b %d, %Y %I:%M %p')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("=" * 80 + "\n")
        f.write("ACCOUNT BREAKDOWN\n")
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
        f.write(f"Total Videos: {total_videos_all}\n")
        f.write(f"Total Views: {total_views_all:,}\n")
        f.write(f"Total Likes: {total_likes_all:,}\n")
        f.write(f"Combined Avg Views per Video: {total_views_all // total_videos_all if total_videos_all else 0:,}\n\n")

        # Ranking
        f.write("=" * 80 + "\n")
        f.write("RANKING BY TOTAL VIEWS\n")
        f.write("=" * 80 + "\n")
        sorted_stats = sorted(all_stats, key=lambda x: x['total_views'], reverse=True)
        for i, stats in enumerate(sorted_stats, 1):
            f.write(f"{i}. @{stats['account']}: {stats['total_views']:,} views ({stats['total_videos']} videos)\n")

    print("\n" + "=" * 80)
    print("COMBINED TOTALS")
    print("=" * 80)
    print(f"Total Videos: {total_videos_all}")
    print(f"Total Views: {total_views_all:,}")
    print(f"Total Likes: {total_likes_all:,}")
    print(f"Combined Avg: {total_views_all // total_videos_all if total_videos_all else 0:,} views/video")

    print("\n" + "=" * 80)
    print("RANKING BY TOTAL VIEWS")
    print("=" * 80)
    sorted_stats = sorted(all_stats, key=lambda x: x['total_views'], reverse=True)
    for i, stats in enumerate(sorted_stats, 1):
        print(f"{i}. @{stats['account']}: {stats['total_views']:,} views ({stats['total_videos']} videos)")

    print(f"\nFull report saved to: {output_file}\n")

if __name__ == '__main__':
    main()
