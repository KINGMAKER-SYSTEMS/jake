#!/usr/bin/env python3
"""
Scrape accounts from CSV for "Home for the Holidays" by The Bean Tones
"""
import sys
import csv
import re
import subprocess
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.get_post_links_by_song import get_profile_username, build_profile_url

def scrape_account_videos_with_sound_id(account, target_sound_id, start_datetime=None, end_datetime=None, limit=2000):
    """Scrape videos from a TikTok account and filter by sound ID and datetime range"""
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
                
                video_url = video_data.get('webpage_url') or video_data.get('url', '')
                if not video_url:
                    continue
                
                # Determine posted datetime first to filter early
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
                
                # Filter by datetime range early
                if video_dt:
                    if start_datetime and video_dt < start_datetime:
                        skipped_old += 1
                        continue
                    if end_datetime and video_dt > end_datetime:
                        skipped_old += 1
                        continue
                elif start_datetime or end_datetime:
                    skipped_old += 1
                    continue
                
                # Now check sound ID - fetch individual video metadata
                sound_id_match = None
                try:
                    vid_result = subprocess.run(
                        [yt_dlp_cmd if isinstance(yt_dlp_cmd, str) else yt_dlp_cmd[0], '--dump-json', video_url],
                        capture_output=True, text=True, timeout=10
                    )
                    if vid_result.returncode == 0:
                        vid_data = json.loads(vid_result.stdout)
                        webpage_url = vid_data.get('webpage_url', '')
                        sound_match = re.search(r'/music/(?:original-sound-)?(\d+)', webpage_url)
                        if sound_match:
                            sound_id_match = sound_match.group(1)
                        
                        if not sound_id_match:
                            music_url = vid_data.get('music_url', '') or vid_data.get('audio_url', '') or vid_data.get('sound_url', '')
                            if music_url:
                                sound_match = re.search(r'/music/(?:original-sound-)?(\d+)', music_url)
                                if sound_match:
                                    sound_id_match = sound_match.group(1)
                        
                        if not sound_id_match:
                            for field in ['track_id', 'sound_id', 'music_id', 'audio_id', 'music_track_id']:
                                if field in vid_data:
                                    val = str(vid_data[field])
                                    if val.isdigit():
                                        sound_id_match = val
                                        break
                        
                        if not sound_id_match:
                            description = vid_data.get('description', '') or vid_data.get('title', '')
                            sound_match = re.search(r'/music/(?:original-sound-)?(\d+)', description)
                            if sound_match:
                                sound_id_match = sound_match.group(1)
                except Exception as e:
                    pass
                
                # Check if sound ID matches
                sound_matches = False
                if sound_id_match and sound_id_match == target_sound_id:
                    sound_matches = True
                
                # Fallback: Match by song/artist if sound ID not found
                if not sound_matches:
                    track = video_data.get('track', '').lower()
                    artist = video_data.get('artist', '').lower()
                    if 'home for the holidays' in track or 'home for the holidays' in artist:
                        if 'bean' in artist and 'tone' in artist:
                            sound_matches = True
                
                if not sound_matches:
                    continue
                
                track = video_data.get('track', '') or 'Unknown'
                artist = video_data.get('artist', '') or (video_data.get('artists', [])[0] if video_data.get('artists') else 'Unknown')
                
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
        
        date_info = ""
        if start_datetime and end_datetime:
            date_info = f" (window: {start_datetime.strftime('%Y-%m-%d %H:%M')} to {end_datetime.strftime('%Y-%m-%d %H:%M')})"
        elif start_datetime:
            date_info = f" (after {start_datetime.strftime('%Y-%m-%d %H:%M')})"
        print(f"    Fetched {total_fetched} posts | {len(videos)} matching sound ID{date_info} | {skipped_old} too old")
        return videos
        
    except subprocess.TimeoutExpired:
        print(f"    [ERROR] Timeout scraping @{username}")
        return []
    except Exception as e:
        print(f"    [ERROR] {e}")
        return []

def main():
    # Read accounts and sound ID from CSV
    csv_path = Path(r"C:\Users\jakeb\OneDrive\Desktop\Claude Sandbox\2025 Sound Campaigns - ☑️ The Bean Tones - Home for the Holidays.csv")
    
    accounts = []
    sound_id = None
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Extract sound ID from TikTok Sound ID URL
            sound_url = row['Tiktok Sound ID']
            sound_match = re.search(r'/music/(?:original-sound-)?(\d+)', sound_url)
            if sound_match and not sound_id:
                sound_id = sound_match.group(1)
            
            account_url = row['Creator Handles'].strip()
            if '@' in account_url:
                username = account_url.split('@')[1].split('/')[0]
                accounts.append(username)
    
    if not sound_id:
        print("ERROR: Could not extract sound ID from CSV")
        sys.exit(1)
    
    print("=" * 80)
    print("SCRAPING 'HOME FOR THE HOLIDAYS' CAMPAIGN")
    print("=" * 80)
    print(f"\nTarget Sound ID: {sound_id}")
    print(f"Accounts to scrape: {len(accounts)}")
    for acc in accounts:
        print(f"  - @{acc}")
    
    # Start date: December 15, 2025
    start_date = datetime(2025, 12, 15, 0, 0)
    end_date = datetime.now()
    
    print(f"\nDate range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    all_videos = []
    
    # Scrape each account with sound ID matching
    for account in accounts:
        print(f"\nScraping @{account}...")
        videos = scrape_account_videos_with_sound_id(account, sound_id, start_datetime=start_date, end_datetime=end_date, limit=2000)
        all_videos.extend(videos)
    
    matching_videos = all_videos  # Already filtered by sound ID
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total videos scraped: {len(all_videos)}")
    print(f"Matching videos: {len(matching_videos)}")
    
    if matching_videos:
        # Group by account
        from collections import defaultdict
        by_account = defaultdict(list)
        for video in matching_videos:
            by_account[video['account']].append(video)
        
        # Sort by total views per account
        account_totals = {acc: sum(v['views'] for v in videos) for acc, videos in by_account.items()}
        sorted_accounts = sorted(account_totals.items(), key=lambda x: x[1], reverse=True)
        
        total_views = sum(v['views'] for v in matching_videos)
        total_likes = sum(v['likes'] for v in matching_videos)
        
        print(f"\nTotal Views: {total_views:,}")
        print(f"Total Likes: {total_likes:,}")
        
        print(f"\nBreakdown by Account:")
        for account, _ in sorted_accounts:
            videos = by_account[account]
            account_views = sum(v['views'] for v in videos)
            account_likes = sum(v['likes'] for v in videos)
            print(f"  {account}: {len(videos)} videos, {account_views:,} views, {account_likes:,} likes")
        
        # Save results
        output_file = Path(__file__).parent.parent.parent / 'output' / 'Home_for_the_Holidays_scrape_results.txt'
        copy_paste_file = Path(__file__).parent.parent.parent / 'output' / 'Home_for_the_Holidays_copy_paste.txt'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"HOME FOR THE HOLIDAYS - SCRAPE RESULTS\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Total matching videos: {len(matching_videos)}\n")
            f.write(f"Total views: {total_views:,}\n")
            f.write(f"Total likes: {total_likes:,}\n\n")
            
            for account, _ in sorted_accounts:
                videos = sorted(by_account[account], key=lambda x: x['views'], reverse=True)
                f.write(f"\n{account}:\n")
                f.write("-" * 80 + "\n")
                for video in videos:
                    f.write(f"  {video['url']}\n")
                    f.write(f"    Views: {video['views']:,} | Likes: {video['likes']:,}\n")
        
        with open(copy_paste_file, 'w', encoding='utf-8') as f:
            f.write(f"HOME FOR THE HOLIDAYS - COPY/PASTE FORMAT\n")
            f.write("=" * 80 + "\n\n")
            for account, _ in sorted_accounts:
                videos = sorted(by_account[account], key=lambda x: x['views'], reverse=True)
                for video in videos:
                    f.write(f"{video['url']}\n")
        
        print(f"\n[SUCCESS] Results saved to:")
        print(f"  Detailed: {output_file}")
        print(f"  Copy/Paste: {copy_paste_file}")
    else:
        print("\n[X] No matching videos found")
    
    print("=" * 80)

if __name__ == '__main__':
    main()

