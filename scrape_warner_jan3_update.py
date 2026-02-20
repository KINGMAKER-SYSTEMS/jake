#!/usr/bin/env python3
"""
Scrape Warner campaign accounts (beau, cody, gavin) since January 3rd, 2026.
Shows all videos grouped by song.
"""

import sys
import subprocess
import json
import re
import csv
from collections import defaultdict
from datetime import datetime, timedelta
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

    # Use yt-dlp to get video metadata
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

    # Start date: January 3rd, 2026
    start_date = datetime(2026, 1, 3).date()

    print("=" * 80)
    print("WARNER CAMPAIGN ACCOUNTS SCRAPE - SINCE JANUARY 3, 2026")
    print("=" * 80)
    print(f"\nScraping {len(warner_accounts)} Warner accounts: {', '.join(['@' + a for a in warner_accounts])}")
    print(f"Start date: {start_date}\n")

    all_videos = []

    # Scrape each account
    for account in warner_accounts:
        # Use higher limit for accounts that post frequently (like Cody)
        limit = 2000 if account in ['codyjames6.7'] else 500
        videos = scrape_account_videos(account, start_datetime=start_date, limit=limit)
        all_videos.extend(videos)

    print(f"\nTotal videos collected since {start_date}: {len(all_videos)}")

    # Group by song
    songs_dict = defaultdict(lambda: {
        'song': '',
        'artist': '',
        'videos': [],
        'accounts': set(),
        'total_views': 0,
        'total_likes': 0
    })

    for video in all_videos:
        song_key = normalize_song_key(video['song'], video['artist'])
        songs_dict[song_key]['song'] = video['song']
        songs_dict[song_key]['artist'] = video['artist']
        songs_dict[song_key]['videos'].append(video)
        songs_dict[song_key]['accounts'].add(video['account'])
        songs_dict[song_key]['total_views'] += video['views']
        songs_dict[song_key]['total_likes'] += video['likes']

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
    print("ACCOUNT STATISTICS (JAN 3 - NOW)")
    print("=" * 80)

    for account, data in sorted_accounts:
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
            print(f"    Uses: {song_data['count']} | Views: {song_data['views']:,} | Likes: {song_data['likes']:,}")

    # Sort songs by total views (descending)
    sorted_songs = sorted(songs_dict.items(), key=lambda x: x[1]['total_views'], reverse=True)

    # Print results
    print("\n" + "=" * 80)
    print("RESULTS GROUPED BY SONG")
    print("=" * 80)

    for song_key, data in sorted_songs:
        print(f"\n{'=' * 80}")
        try:
            print(f"SONG: {data['song']}")
            print(f"ARTIST: {data['artist']}")
        except UnicodeEncodeError:
            print(f"SONG: {data['song'].encode('ascii', 'ignore').decode('ascii')}")
            print(f"ARTIST: {data['artist'].encode('ascii', 'ignore').decode('ascii')}")
        print(f"Total Uses: {len(data['videos'])}")
        print(f"Accounts: {', '.join(sorted(data['accounts']))}")
        print(f"Total Views: {data['total_views']:,}")
        print(f"Total Likes: {data['total_likes']:,}")
        print(f"\nPost Links ({len(data['videos'])} videos):")
        print("-" * 80)

        sorted_videos = sorted(data['videos'], key=lambda x: x['views'], reverse=True)
        for i, video in enumerate(sorted_videos, 1):
            print(f"  {i}. {video['url']}")
            print(f"     Account: {video['account']} | Views: {video['views']:,} | Likes: {video['likes']:,}")

    # Save account statistics to separate file
    stats_file = Path('output') / 'warner_accounts_jan3_now_stats.txt'
    stats_file.parent.mkdir(exist_ok=True)

    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("WARNER ACCOUNTS STATISTICS - JANUARY 3 TO NOW\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Date Range: {start_date} to {datetime.now().date()}\n")
        f.write(f"Accounts processed: {len(warner_accounts)}\n")
        f.write(f"Total videos: {len(all_videos)}\n\n")

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

    # Save to file
    output_file = Path('output') / 'warner_accounts_jan3_now.txt'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("WARNER CAMPAIGN ACCOUNTS - POST LINKS GROUPED BY SONG\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Start Date: {start_date}\n")
        f.write(f"Accounts processed: {len(warner_accounts)}\n")
        f.write(f"Total videos: {len(all_videos)}\n")
        f.write(f"Unique songs: {len(songs_dict)}\n\n")

        for song_key, data in sorted_songs:
            f.write(f"\n{'=' * 80}\n")
            song_safe = data['song'].encode('utf-8', errors='replace').decode('utf-8')
            artist_safe = data['artist'].encode('utf-8', errors='replace').decode('utf-8')
            f.write(f"SONG: {song_safe}\n")
            f.write(f"ARTIST: {artist_safe}\n")
            f.write(f"Total Uses: {len(data['videos'])}\n")
            f.write(f"Accounts: {', '.join(sorted(data['accounts']))}\n")
            f.write(f"Total Views: {data['total_views']:,}\n")
            f.write(f"Total Likes: {data['total_likes']:,}\n")
            f.write(f"\nPost Links ({len(data['videos'])} videos):\n")
            f.write("-" * 80 + "\n")

            sorted_videos = sorted(data['videos'], key=lambda x: x['views'], reverse=True)
            for i, video in enumerate(sorted_videos, 1):
                f.write(f"  {i}. {video['url']}\n")
                f.write(f"     Account: {video['account']} | Views: {video['views']:,} | Likes: {video['likes']:,}\n")

    # Copy-paste version - flat list of all links
    copy_paste_file = Path('output') / 'warner_accounts_jan3_now_copy_paste.txt'

    # Sort all videos by views (descending) for the flat list
    all_videos_sorted = sorted(all_videos, key=lambda x: x['views'], reverse=True)

    with open(copy_paste_file, 'w', encoding='utf-8') as f:
        f.write("WARNER CAMPAIGN ACCOUNTS - COPY/PASTE FORMAT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Start Date: {start_date}\n")
        f.write(f"Accounts: {', '.join(['@' + a for a in warner_accounts])}\n")
        f.write(f"Total videos: {len(all_videos)}\n\n")
        f.write("=" * 80 + "\n\n")

        # Just list all links without song grouping
        for video in all_videos_sorted:
            f.write(f"{video['url']}\n")

    print(f"\n{'=' * 80}")
    print(f"[SUCCESS] Results saved to:")
    print(f"  Account Statistics: {stats_file}")
    print(f"  Detailed (by song): {output_file}")
    print(f"  Copy/Paste: {copy_paste_file}")
    print(f"{'=' * 80}\n")

if __name__ == '__main__':
    main()
