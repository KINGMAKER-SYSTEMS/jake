#!/usr/bin/env python3
"""
Scrape Warner campaign accounts since November 12th, 2025.
Shows all videos grouped by song.
"""

import sys
import subprocess
import json
import re
import csv
import os
import pickle
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


# Cache functions for video data persistence
def load_account_cache(username, cache_dir='cache'):
    """Load cached videos for an account"""
    cache_path = os.path.join(cache_dir, f'warner_{username}_cache.pkl')
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
                return data.get('videos', []), data.get('last_scrape_date')
        except Exception as e:
            print(f"    [WARN] Could not load cache for {username}: {e}")
    return [], None


def save_account_cache(username, videos, scrape_date, cache_dir='cache'):
    """Save videos to cache for an account"""
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f'warner_{username}_cache.pkl')
    try:
        with open(cache_path, 'wb') as f:
            pickle.dump({'videos': videos, 'last_scrape_date': scrape_date}, f)
    except Exception as e:
        print(f"    [WARN] Could not save cache for {username}: {e}")


def merge_videos(cached_videos, new_videos, start_date=None, end_date=None):
    """Merge cached and new videos, keeping higher view counts and filtering by date"""
    # Use URL as unique key
    video_map = {}

    # Add cached videos first
    for v in cached_videos:
        video_map[v['url']] = v

    # Merge new videos, keeping higher view counts
    for v in new_videos:
        if v['url'] in video_map:
            # Update if new views are higher
            if v.get('views', 0) > video_map[v['url']].get('views', 0):
                video_map[v['url']] = v
        else:
            video_map[v['url']] = v

    # Filter by date range if specified
    result = []
    for v in video_map.values():
        # Try to get the video date
        video_date = None
        if v.get('timestamp'):
            video_date = v['timestamp'].date() if hasattr(v['timestamp'], 'date') else v['timestamp']
        elif v.get('upload_date'):
            try:
                video_date = datetime.strptime(v['upload_date'], '%Y%m%d').date()
            except:
                pass

        # Filter by date range
        if video_date:
            if start_date and video_date < start_date:
                continue
            if end_date and video_date > end_date:
                continue

        result.append(v)

    return result

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

def scrape_account_videos(account, start_datetime=None, end_datetime=None, limit=500):
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

        # Check if we got any output - warnings in stderr are OK as long as we have data
        if result.returncode != 0 and not result.stdout.strip():
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
                
                # Filter by date range if provided
                if video_dt:
                    if start_datetime and video_dt.date() < start_datetime:
                        skipped_old += 1
                        continue
                    if end_datetime and video_dt.date() > end_datetime:
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

def load_warner_accounts():
    """Load Warner accounts from CSV file"""
    csv_path = Path('warner_accounts.csv')
    if csv_path.exists():
        accounts = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get('URL', '').strip()
                if url:
                    username = get_profile_username(url)
                    if username:
                        accounts.append(username)
        return accounts if accounts else ['beaujenkins', 'codyjames6.7', 'gavin.wilder1', 'brew.pilled', 'drivetoclearmymind001']
    return ['beaujenkins', 'codyjames6.7', 'gavin.wilder1', 'brew.pilled', 'drivetoclearmymind001']

def main():
    # Load Warner accounts
    warner_accounts = load_warner_accounts()
    
    # Date range: February 15 - March 15, 2026
    start_date = datetime(2026, 2, 15).date()
    end_date = datetime(2026, 3, 15).date()

    # Target views per artist
    artist_targets = {
        'blake whiten': 3_000_000,
        'zach bryan': 2_000_000,
        'gannon fremin': 1_500_000,
        'amble': 1_500_000,
        'nessa barrett': 750_000,
        'adrien nunez': 500_000,
        'maddox batson': 500_000,
        'michael marcagi': 500_000,
        'sombr': 500_000,
        'jaymin': 500_000,
        'cassandra coleman': 500_000,
        'alex sucks': 500_000,
        'justine skye': 250_000,
    }

    print("=" * 80)
    print("WARNER CAMPAIGN ACCOUNTS SCRAPE - FEB 15 TO MAR 15, 2026")
    print("=" * 80)
    print(f"\nScraping {len(warner_accounts)} Warner accounts...")
    print(f"Date range: {start_date} to {end_date}\n")
    
    all_videos = []

    # Scrape each account with caching
    for account in warner_accounts:
        # Load cached videos for this account
        cached_videos, last_scrape = load_account_cache(account)
        if cached_videos:
            print(f"    [CACHE] Loaded {len(cached_videos)} cached videos for {account}")

        # Use higher limit for accounts that post frequently (like Cody)
        limit = 2000 if account in ['codyjames6.7'] else 500
        new_videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=limit)

        # Merge new videos with cached videos (keeps higher view counts)
        combined_videos = merge_videos(cached_videos, new_videos, start_date, end_date)

        # Save updated cache
        save_account_cache(account, combined_videos, datetime.now().date())

        # Log if cache helped
        if len(combined_videos) > len(new_videos):
            print(f"    [CACHE] Merged: {len(new_videos)} new + {len(cached_videos)} cached = {len(combined_videos)} total videos")

        all_videos.extend(combined_videos)
    
    print(f"\nTotal videos collected ({start_date} to {end_date}): {len(all_videos)}")
    
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

    # Aggregate views by artist (matching against targets)
    artist_views = defaultdict(int)
    artist_posts = defaultdict(int)
    for song_key, data in songs_dict.items():
        artist_lower = data['artist'].lower()
        for target_artist in artist_targets.keys():
            # Only match if target artist name is IN the video's artist field
            # (not the other way around - prevents 'h' matching 'zach bryan')
            if target_artist in artist_lower:
                artist_views[target_artist] += data['total_views']
                artist_posts[target_artist] += len(data['videos'])
                break

    # Print artist progress vs targets
    print("\n" + "=" * 80)
    print("ARTIST PROGRESS VS TARGETS")
    print("=" * 80)

    for artist, target in sorted(artist_targets.items(), key=lambda x: x[1], reverse=True):
        views = artist_views.get(artist, 0)
        posts = artist_posts.get(artist, 0)
        pct = (views / target * 100) if target > 0 else 0
        remaining = max(0, target - views)
        status = "COMPLETE!" if views >= target else f"{remaining:,} to go"
        print(f"\n{artist.title()} ({posts} posts)")
        print(f"  Target: {target:,} | Current: {views:,} | {pct:.1f}% | {status}")

    # Print account statistics
    print("\n" + "=" * 80)
    print("ACCOUNT STATISTICS (FEB 15 - MAR 15, 2026)")
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
    stats_file = Path('output') / 'warner_accounts_stats_nov15_now.txt'
    stats_file.parent.mkdir(exist_ok=True)
    
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("WARNER ACCOUNTS STATISTICS - DECEMBER 15 TO NOW\n")
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
    output_file = Path('output') / 'warner_accounts_since_nov15.txt'
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
    copy_paste_file = Path('output') / 'warner_accounts_since_nov15_copy_paste.txt'
    
    # Sort all videos by views (descending) for the flat list
    all_videos_sorted = sorted(all_videos, key=lambda x: x['views'], reverse=True)
    
    with open(copy_paste_file, 'w', encoding='utf-8') as f:
        f.write("WARNER CAMPAIGN ACCOUNTS - COPY/PASTE FORMAT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Start Date: {start_date}\n")
        f.write(f"Accounts: {', '.join(warner_accounts)}\n")
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

