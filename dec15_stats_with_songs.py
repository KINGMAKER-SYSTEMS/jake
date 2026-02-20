#!/usr/bin/env python3
"""
Get stats from Dec 15 to now for Beau, Gavin, and Cody with individual song breakdowns
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.get_post_links_by_song import scrape_account_videos

def normalize_song_key(song, artist):
    """Create normalized song key for grouping"""
    song_clean = (song or 'Unknown').strip()
    artist_clean = (artist or 'Unknown').strip()
    return f"{song_clean} - {artist_clean}"

def main():
    start_date = datetime(2025, 12, 15, 0, 0)
    end_date = datetime.now()

    accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']

    print("=" * 80)
    print("STATS FROM DEC 15 TO NOW - BEAU, CODY & GAVIN")
    print("=" * 80)
    print(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    all_account_stats = []
    all_videos_combined = []

    # Scrape each account and get individual stats
    for account in accounts:
        print(f"\nScraping @{account}...")
        videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)
        all_videos_combined.extend(videos)

        total_views = sum(v['views'] for v in videos)
        total_likes = sum(v['likes'] for v in videos)
        avg_views = total_views // len(videos) if videos else 0

        # Find top video
        top_video = max(videos, key=lambda v: v['views']) if videos else None

        # Group by song for this account
        songs_dict = defaultdict(lambda: {
            'song': '',
            'artist': '',
            'videos': [],
            'total_views': 0,
            'total_likes': 0
        })

        for video in videos:
            song = video.get('song', 'Unknown')
            artist = video.get('artist', 'Unknown')
            song_key = normalize_song_key(song, artist)

            songs_dict[song_key]['song'] = song
            songs_dict[song_key]['artist'] = artist
            songs_dict[song_key]['videos'].append(video)
            songs_dict[song_key]['total_views'] += video['views']
            songs_dict[song_key]['total_likes'] += video['likes']

        # Sort songs by views
        sorted_songs = sorted(songs_dict.items(), key=lambda x: x[1]['total_views'], reverse=True)

        account_stats = {
            'account': account,
            'total_videos': len(videos),
            'total_views': total_views,
            'total_likes': total_likes,
            'avg_views': avg_views,
            'top_video': top_video,
            'songs': sorted_songs
        }
        all_account_stats.append(account_stats)

        print(f"  Total Videos: {len(videos)}")
        print(f"  Total Views: {total_views:,}")
        print(f"  Total Likes: {total_likes:,}")
        print(f"  Average Views per Video: {avg_views:,}")

    # Calculate combined totals
    total_videos_all = sum(s['total_videos'] for s in all_account_stats)
    total_views_all = sum(s['total_views'] for s in all_account_stats)
    total_likes_all = sum(s['total_likes'] for s in all_account_stats)
    combined_avg = total_views_all // total_videos_all if total_videos_all else 0

    # Group all videos by song for combined stats
    combined_songs_dict = defaultdict(lambda: {
        'song': '',
        'artist': '',
        'videos': [],
        'accounts': set(),
        'total_views': 0,
        'total_likes': 0
    })

    for video in all_videos_combined:
        song = video.get('song', 'Unknown')
        artist = video.get('artist', 'Unknown')
        song_key = normalize_song_key(song, artist)

        combined_songs_dict[song_key]['song'] = song
        combined_songs_dict[song_key]['artist'] = artist
        combined_songs_dict[song_key]['videos'].append(video)
        combined_songs_dict[song_key]['accounts'].add(video['account'])
        combined_songs_dict[song_key]['total_views'] += video['views']
        combined_songs_dict[song_key]['total_likes'] += video['likes']

    sorted_combined_songs = sorted(combined_songs_dict.items(), key=lambda x: x[1]['total_views'], reverse=True)

    # Save to file
    output_file = Path('output') / 'dec15_stats_with_songs.txt'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("STATS FROM DEC 15 TO NOW - BEAU, CODY & GAVIN WITH SONG BREAKDOWNS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Overall Summary
        f.write("=" * 80 + "\n")
        f.write("OVERALL SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        for stats in all_account_stats:
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
        f.write(f"Combined Average Views per Video: {combined_avg:,}\n")
        f.write(f"Unique Songs: {len(combined_songs_dict)}\n\n")

        # Individual account song breakdowns
        f.write("=" * 80 + "\n")
        f.write("INDIVIDUAL ACCOUNT SONG BREAKDOWNS\n")
        f.write("=" * 80 + "\n\n")

        for stats in all_account_stats:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"@{stats['account']} - SONGS BREAKDOWN\n")
            f.write(f"{'=' * 80}\n\n")

            for song_key, data in stats['songs']:
                f.write(f"  Song: {data['song']}\n")
                f.write(f"  Artist: {data['artist']}\n")
                f.write(f"  Videos: {len(data['videos'])}\n")
                f.write(f"  Total Views: {data['total_views']:,}\n")
                f.write(f"  Total Likes: {data['total_likes']:,}\n")
                f.write(f"  Avg Views/Video: {data['total_views'] // len(data['videos']) if data['videos'] else 0:,}\n")
                f.write(f"  {'-' * 76}\n")

        # Combined song stats
        f.write("\n" + "=" * 80 + "\n")
        f.write("COMBINED SONG STATS (ALL THREE ACCOUNTS)\n")
        f.write("=" * 80 + "\n\n")

        for song_key, data in sorted_combined_songs:
            f.write(f"{'=' * 80}\n")
            f.write(f"Song: {data['song']}\n")
            f.write(f"Artist: {data['artist']}\n")
            f.write(f"Total Videos: {len(data['videos'])}\n")
            f.write(f"Accounts: {', '.join(sorted(data['accounts']))}\n")
            f.write(f"Total Views: {data['total_views']:,}\n")
            f.write(f"Total Likes: {data['total_likes']:,}\n")
            f.write(f"Average Views per Video: {data['total_views'] // len(data['videos']) if data['videos'] else 0:,}\n\n")

    print("\n" + "=" * 80)
    print("COMBINED TOTALS")
    print("=" * 80)
    print(f"Total Videos (All 3 Accounts): {total_videos_all}")
    print(f"Total Views (All 3 Accounts): {total_views_all:,}")
    print(f"Total Likes (All 3 Accounts): {total_likes_all:,}")
    print(f"Combined Average Views per Video: {combined_avg:,}")
    print(f"Unique Songs: {len(combined_songs_dict)}")

    print("\n" + "=" * 80)
    print("TOP 5 SONGS (COMBINED)")
    print("=" * 80)
    for i, (song_key, data) in enumerate(sorted_combined_songs[:5], 1):
        print(f"{i}. {data['song']} - {data['artist']}: {data['total_views']:,} views ({len(data['videos'])} videos)")

    print("\n" + "=" * 80)
    print(f"Full results saved to: {output_file}")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    main()
