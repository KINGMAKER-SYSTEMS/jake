#!/usr/bin/env python3
"""
Scrape Warner campaign accounts (beau, cody, gavin) since December 15th, 2025.
Shows account totals and song breakdowns.
"""

import sys
import subprocess
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

def get_profile_username(url_or_username):
    """Extract username from TikTok profile URL or handle"""
    if not url_or_username.startswith('http'):
        username = url_or_username.lstrip('@')
        return username
    match = re.search(r'@([\w\.]+)', url_or_username)
    if match:
        return match.group(1)
    return None

def build_profile_url(username):
    """Build TikTok profile URL from username"""
    return f"https://www.tiktok.com/@{username}"

def scrape_account_videos(account, start_datetime=None, limit=500):
    """Scrape videos from a TikTok account and filter by datetime range"""
    username = get_profile_username(account)
    if not username:
        print(f"  [ERROR] Could not extract username from: {account}")
        return []

    profile_url = build_profile_url(username)
    print(f"  Scraping @{username}...")

    import shutil

    yt_dlp_cmd = 'yt-dlp'
    if not shutil.which('yt-dlp'):
        yt_dlp_cmd = [sys.executable, '-m', 'yt_dlp']

    cmd = [
        yt_dlp_cmd if isinstance(yt_dlp_cmd, str) else yt_dlp_cmd[0],
        '--flat-playlist',
        '--dump-json',
        '--playlist-end', str(limit),
        profile_url
    ]

    if not isinstance(yt_dlp_cmd, str):
        cmd = [sys.executable, '-m', 'yt_dlp'] + cmd[1:]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode != 0:
            print(f"    [ERROR] Failed to scrape: {result.stderr[:200]}")
            return []

        videos = []
        total_fetched = 0
        skipped_old = 0

        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                video_data = json.loads(line)
                total_fetched += 1

                # Extract song info
                track = video_data.get('track', '') or 'Unknown'
                artist = video_data.get('artist', '') or (video_data.get('artists', [])[0] if video_data.get('artists') else 'Unknown')

                # Get video URL
                video_url = video_data.get('webpage_url') or video_data.get('url', '')

                if not video_url:
                    continue

                # Determine posted datetime
                video_dt = None
                timestamp = video_data.get('timestamp')
                if timestamp:
                    try:
                        video_dt = datetime.fromtimestamp(timestamp)
                    except (ValueError, OSError):
                        pass

                if not video_dt:
                    upload_date = video_data.get('upload_date')
                    if upload_date:
                        try:
                            video_dt = datetime.strptime(upload_date, '%Y%m%d')
                        except ValueError:
                            pass

                # Filter by start date if provided
                if start_datetime and video_dt:
                    if video_dt.date() < start_datetime:
                        skipped_old += 1
                        continue

                videos.append({
                    'url': video_url,
                    'song': track,
                    'artist': artist,
                    'account': f"@{username}",
                    'views': video_data.get('view_count', 0),
                    'likes': video_data.get('like_count', 0),
                    'upload_date': video_data.get('upload_date', ''),
                    'timestamp': video_dt
                })
            except json.JSONDecodeError:
                continue

        date_info = f" (after {start_datetime})" if start_datetime else ""
        print(f"    Fetched {total_fetched} posts | {len(videos)} within window{date_info} | {skipped_old} too old")
        return videos

    except subprocess.TimeoutExpired:
        print(f"    [ERROR] Timeout scraping @{username}")
        return []
    except Exception as e:
        print(f"    [ERROR] {e}")
        return []

def normalize_song_key(song, artist):
    """Create normalized song key for grouping"""
    song_clean = song.strip() if song else 'Unknown'
    artist_clean = artist.strip() if artist else 'Unknown'
    return f"{song_clean} - {artist_clean}"

def main():
    # Target accounts: beau, cody, gavin
    warner_accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']

    # Start date: December 15th, 2025
    start_date = datetime(2025, 12, 15).date()

    print("=" * 80)
    print("WARNER ACCOUNTS - DECEMBER 15, 2025 TO NOW")
    print("=" * 80)
    print(f"\nScraping {len(warner_accounts)} accounts: {', '.join(['@' + a for a in warner_accounts])}")
    print(f"Start date: {start_date}\n")

    all_videos = []

    # Scrape each account
    for account in warner_accounts:
        # Use higher limit for accounts that post frequently (like Cody)
        limit = 2000 if account in ['codyjames6.7'] else 500
        videos = scrape_account_videos(account, start_datetime=start_date, limit=limit)
        all_videos.extend(videos)

    print(f"\nTotal videos collected since {start_date}: {len(all_videos)}")

    # Group by account for statistics
    accounts_dict = defaultdict(lambda: {
        'videos': [],
        'total_views': 0,
        'total_likes': 0,
        'songs_used': defaultdict(lambda: {'count': 0, 'views': 0, 'likes': 0})
    })

    for video in all_videos:
        account = video['account']
        accounts_dict[account]['videos'].append(video)
        accounts_dict[account]['total_views'] += video['views']
        accounts_dict[account]['total_likes'] += video['likes']

        song_key = normalize_song_key(video['song'], video['artist'])
        accounts_dict[account]['songs_used'][song_key]['count'] += 1
        accounts_dict[account]['songs_used'][song_key]['views'] += video['views']
        accounts_dict[account]['songs_used'][song_key]['likes'] += video['likes']
        accounts_dict[account]['songs_used'][song_key]['song'] = video['song']
        accounts_dict[account]['songs_used'][song_key]['artist'] = video['artist']

    # Sort accounts by total views (descending)
    sorted_accounts = sorted(accounts_dict.items(), key=lambda x: x[1]['total_views'], reverse=True)

    # Print account statistics
    print("\n" + "=" * 80)
    print("ACCOUNT TOTALS (DEC 15 - NOW)")
    print("=" * 80)

    grand_total_videos = 0
    grand_total_views = 0
    grand_total_likes = 0

    for account, data in sorted_accounts:
        grand_total_videos += len(data['videos'])
        grand_total_views += data['total_views']
        grand_total_likes += data['total_likes']

        print(f"\n{account}")
        print("-" * 80)
        print(f"Total Videos: {len(data['videos'])}")
        print(f"Total Views: {data['total_views']:,}")
        print(f"Total Likes: {data['total_likes']:,}")
        print(f"Avg Views per Video: {data['total_views'] / len(data['videos']):,.0f}" if data['videos'] else "N/A")
        print(f"\nSongs Used ({len(data['songs_used'])} unique songs):")

        # Sort songs by views for this account
        sorted_account_songs = sorted(
            data['songs_used'].items(),
            key=lambda x: x[1]['views'],
            reverse=True
        )

        for song_key, song_data in sorted_account_songs:
            try:
                print(f"  • {song_data['song']} - {song_data['artist']}")
            except UnicodeEncodeError:
                song_safe = song_data['song'].encode('ascii', 'ignore').decode('ascii')
                artist_safe = song_data['artist'].encode('ascii', 'ignore').decode('ascii')
                print(f"  • {song_safe} - {artist_safe}")
            print(f"    Uses: {song_data['count']} | Views: {song_data['views']:,} | Likes: {song_data['likes']:,} | Avg: {song_data['views'] / song_data['count']:,.0f}")

    print("\n" + "=" * 80)
    print("GRAND TOTALS (ALL 3 ACCOUNTS)")
    print("=" * 80)
    print(f"Total Videos: {grand_total_videos}")
    print(f"Total Views: {grand_total_views:,}")
    print(f"Total Likes: {grand_total_likes:,}")
    print(f"Avg Views per Video: {grand_total_views / grand_total_videos:,.0f}" if grand_total_videos else "N/A")

    # Save to file
    output_file = Path('output') / 'warner_accounts_dec15_now_totals.txt'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("WARNER ACCOUNTS - TOTALS BY ACCOUNT AND SONG\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Date Range: {start_date} to {datetime.now().date()}\n")
        f.write(f"Accounts: @beaujenkins, @codyjames6.7, @gavin.wilder1\n\n")

        f.write("=" * 80 + "\n")
        f.write("GRAND TOTALS (ALL 3 ACCOUNTS)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Videos: {grand_total_videos}\n")
        f.write(f"Total Views: {grand_total_views:,}\n")
        f.write(f"Total Likes: {grand_total_likes:,}\n")
        if grand_total_videos:
            f.write(f"Avg Views per Video: {grand_total_views / grand_total_videos:,.0f}\n")

        for account, data in sorted_accounts:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"ACCOUNT: {account}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Videos: {len(data['videos'])}\n")
            f.write(f"Total Views: {data['total_views']:,}\n")
            f.write(f"Total Likes: {data['total_likes']:,}\n")
            if data['videos']:
                f.write(f"Avg Views per Video: {data['total_views'] / len(data['videos']):,.0f}\n")
            f.write(f"\nSongs Used ({len(data['songs_used'])} unique songs):\n")
            f.write("-" * 80 + "\n")

            sorted_account_songs = sorted(
                data['songs_used'].items(),
                key=lambda x: x[1]['views'],
                reverse=True
            )

            for song_key, song_data in sorted_account_songs:
                f.write(f"\n  Song: {song_data['song']}\n")
                f.write(f"  Artist: {song_data['artist']}\n")
                f.write(f"  Uses: {song_data['count']}\n")
                f.write(f"  Total Views: {song_data['views']:,}\n")
                f.write(f"  Total Likes: {song_data['likes']:,}\n")
                if song_data['count'] > 0:
                    f.write(f"  Avg Views per Use: {song_data['views'] / song_data['count']:,.0f}\n")

    print(f"\n{'=' * 80}")
    print(f"[SUCCESS] Results saved to: {output_file}")
    print(f"{'=' * 80}\n")

if __name__ == '__main__':
    main()
