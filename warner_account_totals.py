#!/usr/bin/env python3
"""
Show total views by account for Warner accounts (Dec 15 - Now)
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

def main():
    # Target accounts: beau, cody, gavin
    warner_accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']

    # Start date: December 15th, 2025
    start_date = datetime(2025, 12, 15).date()

    print("=" * 80)
    print("WARNER ACCOUNTS - TOTAL VIEWS BY ACCOUNT")
    print("=" * 80)
    print(f"\nDate Range: Dec 15, 2025 to {datetime.now().date()}")
    print(f"Scraping {len(warner_accounts)} accounts...\n")

    all_videos = []
    account_totals = {}

    # Scrape each account
    for account in warner_accounts:
        # Use higher limit for accounts that post frequently (like Cody)
        limit = 2000 if account in ['codyjames6.7'] else 500
        videos = scrape_account_videos(account, start_datetime=start_date, limit=limit)
        all_videos.extend(videos)

        # Calculate totals for this account
        account_name = f"@{account}"
        total_views = sum(v['views'] for v in videos)
        total_likes = sum(v['likes'] for v in videos)

        account_totals[account_name] = {
            'videos': len(videos),
            'views': total_views,
            'likes': total_likes
        }

    print(f"\n{'=' * 80}")
    print("ACCOUNT TOTALS")
    print("=" * 80)
    print(f"{'Account':<20} {'Videos':>10} {'Total Views':>15} {'Total Likes':>15} {'Avg Views':>12}")
    print("-" * 80)

    # Sort by views (descending)
    sorted_accounts = sorted(account_totals.items(), key=lambda x: x[1]['views'], reverse=True)

    grand_total_videos = 0
    grand_total_views = 0
    grand_total_likes = 0

    for account, data in sorted_accounts:
        avg_views = data['views'] / data['videos'] if data['videos'] > 0 else 0
        print(f"{account:<20} {data['videos']:>10} {data['views']:>15,} {data['likes']:>15,} {avg_views:>12,.0f}")

        grand_total_videos += data['videos']
        grand_total_views += data['views']
        grand_total_likes += data['likes']

    print("-" * 80)
    grand_avg = grand_total_views / grand_total_videos if grand_total_videos > 0 else 0
    print(f"{'TOTAL':<20} {grand_total_videos:>10} {grand_total_views:>15,} {grand_total_likes:>15,} {grand_avg:>12,.0f}")

    print(f"\n{'=' * 80}\n")

if __name__ == '__main__':
    main()
