#!/usr/bin/env python3
"""
Scrape Warner campaigns (Cody, Beau, Gavin) + coffeesentiments
Back to 8am 12/15/25 - compile links by account and sound
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.get_post_links_by_song import scrape_account_videos

def main():
    # Start date: 8am 12/15/25
    start_date = datetime(2025, 12, 15, 8, 0)
    end_date = datetime.now()

    tiktok_accounts = [
        'codyjames6.7',      # Cody
        'beaujenkins',       # Beau
        'gavin.wilder1',     # Gavin
        'coffeesentiments'   # coffeesentiments
    ]

    print("=" * 80)
    print("SCRAPING WARNER CAMPAIGNS - UPDATED VIEW COUNTS")
    print("=" * 80)
    print(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"TikTok Accounts: {', '.join([f'@{acc}' for acc in tiktok_accounts])}")
    print("=" * 80)
    print()

    all_results = {}

    # Scrape each TikTok account
    for account in tiktok_accounts:
        print(f"\nScraping @{account}...")
        videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)

        if videos:
            all_results[account] = videos
            print(f"  [+] Found {len(videos)} videos")
        else:
            all_results[account] = []
            print(f"  [-] No videos found")

    # Compile results by account and sound
    print("\n" + "=" * 80)
    print("COMPILING RESULTS BY ACCOUNT AND SOUND")
    print("=" * 80)

    # Save to file
    output_file = Path('output') / 'warner_campaigns_update_dec15_now.txt'
    copy_paste_file = Path('output') / 'warner_campaigns_update_dec15_now_copy_paste.txt'

    with open(output_file, 'w', encoding='utf-8') as f, \
         open(copy_paste_file, 'w', encoding='utf-8') as cp:

        f.write("WARNER CAMPAIGNS UPDATE - DEC 15 (8AM) TO NOW\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        cp.write("WARNER CAMPAIGNS UPDATE - DEC 15 (8AM) TO NOW - COPY/PASTE FORMAT\n")
        cp.write("=" * 80 + "\n\n")

        total_videos = 0
        total_views = 0
        total_likes = 0

        for account in tiktok_accounts:
            videos = all_results.get(account, [])

            if not videos:
                f.write(f"\n{'=' * 80}\n")
                f.write(f"@{account} - No videos found\n")
                f.write("=" * 80 + "\n\n")
                continue

            # Group by sound
            by_sound = defaultdict(list)
            for video in videos:
                song = video.get('song', 'Unknown')
                artist = video.get('artist', '')
                sound_key = f"{song} - {artist}" if artist else song
                by_sound[sound_key].append(video)

            # Stats
            account_views = sum(v['views'] for v in videos)
            account_likes = sum(v['likes'] for v in videos)
            total_videos += len(videos)
            total_views += account_views
            total_likes += account_likes

            # Write to detailed file
            f.write(f"\n{'=' * 80}\n")
            f.write(f"@{account}\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total Videos: {len(videos)}\n")
            f.write(f"Total Views: {account_views:,}\n")
            f.write(f"Total Likes: {account_likes:,}\n")
            f.write(f"Unique Sounds: {len(by_sound)}\n\n")

            # Group by sound
            for sound_key in sorted(by_sound.keys()):
                sound_videos = sorted(by_sound[sound_key], key=lambda x: x['views'], reverse=True)
                sound_views = sum(v['views'] for v in sound_videos)
                sound_likes = sum(v['likes'] for v in sound_videos)

                f.write(f"\n{sound_key}\n")
                f.write(f"  Videos: {len(sound_videos)} | Views: {sound_views:,} | Likes: {sound_likes:,}\n")
                f.write("-" * 80 + "\n")

                for video in sound_videos:
                    date_str = video['timestamp'].strftime('%Y-%m-%d %H:%M') if video.get('timestamp') else 'Unknown'
                    f.write(f"  {video['url']}\n")
                    f.write(f"    Date: {date_str} | Views: {video['views']:,} | Likes: {video['likes']:,}\n")

                # Write to copy/paste file
                cp.write(f"\n@{account} - {sound_key}\n")
                for video in sound_videos:
                    cp.write(f"{video['url']}\n")

            f.write("\n")

        # Summary
        f.write(f"\n{'=' * 80}\n")
        f.write("OVERALL SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Videos: {total_videos}\n")
        f.write(f"Total Views: {total_views:,}\n")
        f.write(f"Total Likes: {total_likes:,}\n")

    print(f"\n{'=' * 80}")
    print(f"[SUCCESS] Results saved to:")
    print(f"  Detailed: {output_file}")
    print(f"  Copy/Paste: {copy_paste_file}")
    print(f"{'=' * 80}\n")

    # Print summary
    print(f"Total Videos: {total_videos}")
    print(f"Total Views: {total_views:,}")
    print(f"Total Likes: {total_likes:,}")

if __name__ == '__main__':
    main()
