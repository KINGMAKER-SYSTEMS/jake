#!/usr/bin/env python3
"""
Scrape Warner accounts (Beau, Cody, Gavin) from 12/15/25
Generate statistics and copy/paste link pages
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.get_post_links_by_song import scrape_account_videos

def main():
    # Start date: 12/15/25 midnight
    start_date = datetime(2025, 12, 15, 0, 0)
    end_date = datetime.now()

    accounts = {
        'beaujenkins': 'Beau',
        'codyjames6.7': 'Cody',
        'gavin.wilder1': 'Gavin',
        'coffeesentiments': 'Coffee',
        'yearnest.hemingway': 'Yearnest'
    }

    print("=" * 80)
    print("SCRAPING WARNER ACCOUNTS - LATEST UPDATE")
    print("=" * 80)
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"Accounts: {', '.join([f'@{acc}' for acc in accounts.keys()])}")
    print("=" * 80)
    print()

    all_results = {}

    # Scrape each account
    for account, name in accounts.items():
        print(f"\nScraping @{account} ({name})...")
        videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)

        if videos:
            all_results[account] = videos
            print(f"  [+] Found {len(videos)} videos")
        else:
            all_results[account] = []
            print(f"  [-] No videos found")

    # Generate output files
    print("\n" + "=" * 80)
    print("GENERATING OUTPUT FILES")
    print("=" * 80)

    output_dir = Path('output')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    stats_file = output_dir / f'warner_stats_{timestamp}.txt'
    links_file = output_dir / f'warner_all_links_{timestamp}.txt'

    # Calculate totals
    total_videos = sum(len(videos) for videos in all_results.values())
    total_views = sum(v['views'] for videos in all_results.values() for v in videos)
    total_likes = sum(v['likes'] for videos in all_results.values() for v in videos)

    # Collect all sounds across all accounts
    all_sounds = defaultdict(lambda: {'videos': [], 'views': 0, 'likes': 0})
    for account in accounts.keys():
        videos = all_results.get(account, [])
        for video in videos:
            song = video.get('song', 'Unknown')
            artist = video.get('artist', '')
            sound_key = f"{song} - {artist}" if artist else song
            all_sounds[sound_key]['videos'].append(video)
            all_sounds[sound_key]['views'] += video['views']
            all_sounds[sound_key]['likes'] += video['likes']

    # Write statistics file
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("WARNER ACCOUNTS - STATISTICS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("OVERALL SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Videos: {total_videos}\n")
        f.write(f"Total Views: {total_views:,}\n")
        f.write(f"Total Likes: {total_likes:,}\n")
        f.write(f"Average Views per Video: {total_views // total_videos if total_videos > 0 else 0:,}\n")
        f.write(f"Unique Sounds: {len(all_sounds)}\n\n")

        # Add BREAKDOWN BY SOUND section at the top
        f.write("BREAKDOWN BY SOUND (Sorted by Total Views)\n")
        f.write("=" * 80 + "\n")
        sorted_sounds = sorted(all_sounds.items(), key=lambda x: x[1]['views'], reverse=True)
        for sound_key, data in sorted_sounds:
            f.write(f"\n{sound_key}\n")
            f.write(f"  Videos: {len(data['videos'])} | Views: {data['views']:,} | Likes: {data['likes']:,}\n")

            # Show which accounts used this sound
            accounts_for_sound = defaultdict(int)
            for video in data['videos']:
                # Extract account from URL
                url = video['url']
                account_name = url.split('@')[1].split('/')[0] if '@' in url else 'Unknown'
                accounts_for_sound[account_name] += 1

            account_summary = ', '.join([f"@{acc}({count})" for acc, count in sorted(accounts_for_sound.items())])
            f.write(f"  Accounts: {account_summary}\n")
        f.write("\n")

        # Stats by account
        for account, name in accounts.items():
            videos = all_results.get(account, [])
            if not videos:
                f.write(f"\n{'=' * 80}\n")
                f.write(f"@{account} ({name}) - No videos found\n")
                f.write("=" * 80 + "\n\n")
                continue

            account_views = sum(v['views'] for v in videos)
            account_likes = sum(v['likes'] for v in videos)
            avg_views = account_views // len(videos)

            # Group by sound
            by_sound = defaultdict(list)
            for video in videos:
                song = video.get('song', 'Unknown')
                artist = video.get('artist', '')
                sound_key = f"{song} - {artist}" if artist else song
                by_sound[sound_key].append(video)

            f.write(f"\n{'=' * 80}\n")
            f.write(f"@{account} ({name})\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total Videos: {len(videos)}\n")
            f.write(f"Total Views: {account_views:,}\n")
            f.write(f"Total Likes: {account_likes:,}\n")
            f.write(f"Average Views: {avg_views:,}\n")
            f.write(f"Unique Sounds: {len(by_sound)}\n\n")

            f.write("TOP 10 VIDEOS:\n")
            f.write("-" * 80 + "\n")
            top_videos = sorted(videos, key=lambda x: x['views'], reverse=True)[:10]
            for i, video in enumerate(top_videos, 1):
                date_str = video['timestamp'].strftime('%Y-%m-%d') if video.get('timestamp') else 'Unknown'
                song = video.get('song', 'Unknown')
                f.write(f"{i:2}. {video['url']}\n")
                f.write(f"    Views: {video['views']:,} | Likes: {video['likes']:,} | Date: {date_str}\n")
                f.write(f"    Sound: {song}\n\n")

            f.write("\nBREAKDOWN BY SOUND:\n")
            f.write("-" * 80 + "\n")
            for sound_key in sorted(by_sound.keys()):
                sound_videos = by_sound[sound_key]
                sound_views = sum(v['views'] for v in sound_videos)
                sound_likes = sum(v['likes'] for v in sound_videos)
                f.write(f"\n{sound_key}\n")
                f.write(f"  Videos: {len(sound_videos)} | Views: {sound_views:,} | Likes: {sound_likes:,}\n")

    # Write links-only file (copy/paste ready)
    with open(links_file, 'w', encoding='utf-8') as f:
        f.write("WARNER ACCOUNTS - ALL VIDEO LINKS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Date: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")
        f.write(f"Total Videos: {total_videos}\n")
        f.write("=" * 80 + "\n\n")

        for account, name in accounts.items():
            videos = all_results.get(account, [])
            if not videos:
                continue

            f.write(f"\n@{account} ({name}) - {len(videos)} videos\n")
            f.write("-" * 80 + "\n")
            for video in videos:
                f.write(f"{video['url']}\n")

        f.write(f"\n{'=' * 80}\n")
        f.write("ALL LINKS (NO HEADERS):\n")
        f.write("=" * 80 + "\n")
        for account in accounts.keys():
            videos = all_results.get(account, [])
            for video in videos:
                f.write(f"{video['url']}\n")

    print(f"\n{'=' * 80}")
    print(f"[SUCCESS] Files saved:")
    print(f"  Statistics: {stats_file}")
    print(f"  All Links: {links_file}")
    print(f"{'=' * 80}\n")

    # Print summary
    print("SUMMARY:")
    print(f"Total Videos: {total_videos}")
    print(f"Total Views: {total_views:,}")
    print(f"Total Likes: {total_likes:,}")
    print()
    for account, name in accounts.items():
        videos = all_results.get(account, [])
        if videos:
            print(f"  @{account} ({name}): {len(videos)} videos")

if __name__ == '__main__':
    main()
