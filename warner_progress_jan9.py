#!/usr/bin/env python3
"""
Warner Accounts Progress Report - Dec 15, 2025 to Now
Shows song totals in table format and compares to targets
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

def categorize_artist(song, artist):
    """Categorize artist for tracking against targets"""
    artist_lower = artist.lower()
    song_lower = song.lower()

    if 'blake whiten' in artist_lower:
        return 'Blake Whiten'
    elif 'pecos' in artist_lower or 'rooftops' in artist_lower:
        return 'Pecos'
    elif 'warren zeiders' in artist_lower:
        return 'Warren Zeiders'
    elif 'gannon fremin' in artist_lower or 'ccrev' in artist_lower:
        return 'Gannon Fremin'
    elif 'maddox batson' in artist_lower:
        return 'Maddox Batson'
    elif 'gavin adcock' in artist_lower:
        return 'Gavin Adcock'
    elif 'wesko' in artist_lower:
        return 'Wesko'
    elif 'adrien nunez' in artist_lower:
        return 'Adrien Nunez'
    else:
        return 'Other'

def main():
    # Target accounts: beau, cody, gavin
    warner_accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']

    # Start date: December 15th, 2025
    start_date = datetime(2025, 12, 15).date()

    # Campaign end date: January 15th, 2026
    end_date = datetime(2026, 1, 15).date()
    today = datetime.now().date()

    # Calculate days elapsed and remaining
    total_days = (end_date - start_date).days
    days_elapsed = (today - start_date).days
    days_remaining = (end_date - today).days
    progress_pct = (days_elapsed / total_days) * 100

    print("=" * 80)
    print("WARNER ACCOUNTS - PROGRESS REPORT")
    print("=" * 80)
    print(f"\nScraping {len(warner_accounts)} accounts: {', '.join(['@' + a for a in warner_accounts])}")
    print(f"Campaign Period: Dec 15, 2025 - Jan 15, 2026")
    print(f"Current Progress: Dec 15 to {today}")
    print(f"Days Elapsed: {days_elapsed} / {total_days} days ({progress_pct:.1f}% of campaign)")
    print(f"Days Remaining: {days_remaining} days\n")

    all_videos = []

    # Scrape each account
    for account in warner_accounts:
        # Use higher limit for accounts that post frequently (like Cody)
        limit = 2000 if account in ['codyjames6.7'] else 500
        videos = scrape_account_videos(account, start_datetime=start_date, limit=limit)
        all_videos.extend(videos)

    print(f"\nTotal videos collected since {start_date}: {len(all_videos)}")

    # Group by artist
    artist_stats = defaultdict(lambda: {
        'views': 0,
        'likes': 0,
        'videos': 0,
        'songs': defaultdict(lambda: {'views': 0, 'likes': 0, 'count': 0})
    })

    for video in all_videos:
        artist_category = categorize_artist(video['song'], video['artist'])
        artist_stats[artist_category]['views'] += video['views']
        artist_stats[artist_category]['likes'] += video['likes']
        artist_stats[artist_category]['videos'] += 1

        song_key = f"{video['song']} - {video['artist']}"
        artist_stats[artist_category]['songs'][song_key]['views'] += video['views']
        artist_stats[artist_category]['songs'][song_key]['likes'] += video['likes']
        artist_stats[artist_category]['songs'][song_key]['count'] += 1

    # Define targets
    targets = {
        'Blake Whiten': 2_250_000,
        'Pecos': 2_000_000,
        'Warren Zeiders': 1_250_000,
        'Gannon Fremin': 500_000,
        'Maddox Batson': 500_000,
        'Gavin Adcock': 300_000,
        'Wesko': 100_000,
        'Adrien Nunez': 100_000,
    }

    total_target = sum(targets.values())
    total_actual = sum(stats['views'] for artist, stats in artist_stats.items() if artist in targets)

    # Print table format
    print("\n" + "=" * 80)
    print("ARTIST TOTALS - TABLE FORMAT")
    print("=" * 80)
    print(f"{'Artist':<20} {'Target':>12} {'Actual':>12} {'Progress':>10} {'Videos':>8} {'Likes':>10}")
    print("-" * 80)

    # Sort by target (descending)
    sorted_artists = sorted(targets.items(), key=lambda x: x[1], reverse=True)

    for artist, target in sorted_artists:
        actual_views = artist_stats[artist]['views']
        actual_videos = artist_stats[artist]['videos']
        actual_likes = artist_stats[artist]['likes']
        progress = (actual_views / target * 100) if target > 0 else 0

        print(f"{artist:<20} {target:>12,} {actual_views:>12,} {progress:>9.1f}% {actual_videos:>8} {actual_likes:>10,}")

    print("-" * 80)
    print(f"{'TOTAL':<20} {total_target:>12,} {total_actual:>12,} {(total_actual/total_target*100):>9.1f}% {len(all_videos):>8} {sum(v['likes'] for v in all_videos):>10,}")

    # Detailed breakdown
    print("\n" + "=" * 80)
    print("DETAILED ARTIST BREAKDOWN")
    print("=" * 80)

    for artist, target in sorted_artists:
        actual_views = artist_stats[artist]['views']
        actual_videos = artist_stats[artist]['videos']
        actual_likes = artist_stats[artist]['likes']
        progress = (actual_views / target * 100) if target > 0 else 0
        remaining = target - actual_views

        # Determine status
        if progress >= progress_pct:
            status = "ON TRACK"
        elif progress >= progress_pct * 0.75:
            status = "NEEDS ATTENTION"
        else:
            status = "CRITICAL"

        print(f"\n{artist}")
        print(f"  Target:      {target:,} views")
        print(f"  Actual:      {actual_views:,} views")
        print(f"  Videos:      {actual_videos}")
        print(f"  Likes:       {actual_likes:,}")
        print(f"  Progress:    {progress:.1f}%")
        print(f"  Remaining:   {remaining:,} views")
        print(f"  Status:      {status}")

        # Show top songs for this artist
        if artist_stats[artist]['songs']:
            print(f"  Top Songs:")
            sorted_songs = sorted(
                artist_stats[artist]['songs'].items(),
                key=lambda x: x[1]['views'],
                reverse=True
            )
            for song_key, song_data in sorted_songs[:5]:
                print(f"    - {song_key}")
                print(f"      {song_data['views']:,} views | {song_data['count']} uses | {song_data['views']//song_data['count']:,} avg")
        print("  " + "-" * 76)

    # Overall summary
    print("\n" + "=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print(f"Total Target:     {total_target:,} views")
    print(f"Total Actual:     {total_actual:,} views")
    print(f"Overall Progress: {(total_actual/total_target*100):.1f}%")
    print(f"Total Remaining:  {total_target - total_actual:,} views")
    print(f"Total Videos:     {len(all_videos)} videos")
    print(f"\nCampaign Timeline:")
    print(f"  Days Elapsed:   {days_elapsed} / {total_days} days ({progress_pct:.1f}%)")
    print(f"  Days Remaining: {days_remaining} days")
    print(f"\nDaily Pace Needed:")
    if days_remaining > 0:
        daily_pace_needed = (total_target - total_actual) / days_remaining
        print(f"  {daily_pace_needed:,.0f} views/day to hit target")
    else:
        print(f"  Campaign ended")

    # Save to file
    output_file = Path('output') / 'warner_progress_jan9.txt'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("PROGRESS VS TARGETS - BEAU, CODY & GAVIN\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Campaign Period: Dec 15, 2025 - Jan 15, 2026\n")
        f.write(f"Current Progress: Dec 15 to {today}\n")
        f.write(f"Days Elapsed: {days_elapsed} / {total_days} days ({progress_pct:.1f}% of campaign)\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("=" * 80 + "\n")
        f.write("ARTIST TOTALS - TABLE FORMAT\n")
        f.write("=" * 80 + "\n")
        f.write(f"{'Artist':<20} {'Target':>12} {'Actual':>12} {'Progress':>10} {'Videos':>8} {'Likes':>10}\n")
        f.write("-" * 80 + "\n")

        for artist, target in sorted_artists:
            actual_views = artist_stats[artist]['views']
            actual_videos = artist_stats[artist]['videos']
            actual_likes = artist_stats[artist]['likes']
            progress = (actual_views / target * 100) if target > 0 else 0

            f.write(f"{artist:<20} {target:>12,} {actual_views:>12,} {progress:>9.1f}% {actual_videos:>8} {actual_likes:>10,}\n")

        f.write("-" * 80 + "\n")
        f.write(f"{'TOTAL':<20} {total_target:>12,} {total_actual:>12,} {(total_actual/total_target*100):>9.1f}% {len(all_videos):>8} {sum(v['likes'] for v in all_videos):>10,}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("ARTIST PROGRESS BREAKDOWN\n")
        f.write("=" * 80 + "\n\n")

        for artist, target in sorted_artists:
            actual_views = artist_stats[artist]['views']
            actual_videos = artist_stats[artist]['videos']
            actual_likes = artist_stats[artist]['likes']
            progress = (actual_views / target * 100) if target > 0 else 0
            remaining = target - actual_views

            if progress >= progress_pct:
                status = "ON TRACK"
            elif progress >= progress_pct * 0.75:
                status = "NEEDS ATTENTION"
            else:
                status = "CRITICAL"

            f.write(f"{artist}\n")
            f.write(f"  Target:      {target:,} views\n")
            f.write(f"  Actual:      {actual_views:,} views\n")
            f.write(f"  Videos:      {actual_videos}\n")
            f.write(f"  Likes:       {actual_likes:,}\n")
            f.write(f"  Progress:    {progress:.1f}%\n")
            f.write(f"  Remaining:   {remaining:,} views\n")
            f.write(f"  Status:      {status}\n")
            f.write("  " + "-" * 76 + "\n\n")

        f.write("=" * 80 + "\n")
        f.write("OVERALL SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Target:     {total_target:,} views\n")
        f.write(f"Total Actual:     {total_actual:,} views\n")
        f.write(f"Overall Progress: {(total_actual/total_target*100):.1f}%\n")
        f.write(f"Total Remaining:  {total_target - total_actual:,} views\n")
        f.write(f"Total Videos:     {len(all_videos)} videos\n")

    print(f"\n{'=' * 80}")
    print(f"[SUCCESS] Results saved to: {output_file}")
    print(f"{'=' * 80}\n")

if __name__ == '__main__':
    main()
