#!/usr/bin/env python3
"""
Scrape venald.b for Collapse sound (last 24 hours)
"""
import sys
import re
import subprocess
import json
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.get_post_links_by_song import get_profile_username, build_profile_url

def scrape_account_for_sound(account, target_sound_id, start_datetime=None, end_datetime=None, limit=2000):
    """Scrape videos from a TikTok account and filter by sound ID and datetime range"""
    username = get_profile_username(account)
    if not username:
        print(f"  [ERROR] Could not extract username from: {account}")
        return []
    
    profile_url = build_profile_url(username)
    print(f"Scraping @{username}...")
    
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
            print(f"  [ERROR] Failed to scrape: {result.stderr[:200]}")
            return []
        
        videos = []
        total_fetched = 0
        skipped_old = 0
        checked = 0
        
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
                checked += 1
                if checked % 10 == 0:
                    print(f"    Checking video {checked}...")
                
                sound_id_match = None
                try:
                    vid_result = subprocess.run(
                        [yt_dlp_cmd if isinstance(yt_dlp_cmd, str) else yt_dlp_cmd[0], '--dump-json', video_url],
                        capture_output=True, text=True, timeout=10
                    )
                    if vid_result.returncode == 0:
                        vid_data = json.loads(vid_result.stdout)
                        # Check for sound/music URL in various fields
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
                
                # Fallback: For "original sound" videos, match by artist if sound ID not found
                if not sound_matches:
                    track = video_data.get('track', '').lower()
                    artist = video_data.get('artist', '').lower()
                    # Check if it's an original sound by chance pena
                    if 'original sound' in track:
                        if 'chance' in artist and ('pena' in artist or 'peña' in artist):
                            # This is likely the right sound, accept it
                            sound_matches = True
                            print(f"    Matched by artist/track (original sound by chance pena)")
                
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
        print(f"  Fetched {total_fetched} posts | Checked {checked} in date range | {len(videos)} matching sound ID{date_info}")
        return videos
        
    except subprocess.TimeoutExpired:
        print(f"  [ERROR] Timeout scraping @{username}")
        return []
    except Exception as e:
        print(f"  [ERROR] {e}")
        return []

def main():
    target_sound_id = "7534110676248316686"  # Collapse sound ID
    account = "@venald.b"
    
    # Last 24 hours
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=24)
    
    print("=" * 80)
    print("SCRAPING @venald.b FOR COLLAPSE SOUND (LAST 24 HOURS)")
    print("=" * 80)
    print(f"\nTarget Sound ID: {target_sound_id}")
    print(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    videos = scrape_account_for_sound(account, target_sound_id, start_datetime=start_date, end_datetime=end_date, limit=2000)
    
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Matching videos: {len(videos)}")
    
    if videos:
        total_views = sum(v['views'] for v in videos)
        total_likes = sum(v['likes'] for v in videos)
        
        print(f"\nTotal Views: {total_views:,}")
        print(f"Total Likes: {total_likes:,}")
        
        print(f"\nVideos:")
        for i, video in enumerate(sorted(videos, key=lambda x: x['views'], reverse=True), 1):
            print(f"\n  {i}. {video['url']}")
            print(f"     Views: {video['views']:,} | Likes: {video['likes']:,}")
            if video['timestamp']:
                print(f"     Posted: {video['timestamp'].strftime('%Y-%m-%d %H:%M')}")
        
        # Save results
        output_file = Path(__file__).parent.parent.parent / 'output' / 'venald_collapse_24h.txt'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"VENALD.B - COLLAPSE SOUND (LAST 24 HOURS)\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Total matching videos: {len(videos)}\n")
            f.write(f"Total views: {total_views:,}\n")
            f.write(f"Total likes: {total_likes:,}\n\n")
            
            for i, video in enumerate(sorted(videos, key=lambda x: x['views'], reverse=True), 1):
                f.write(f"{i}. {video['url']}\n")
                f.write(f"   Views: {video['views']:,} | Likes: {video['likes']:,}\n")
                if video['timestamp']:
                    f.write(f"   Posted: {video['timestamp'].strftime('%Y-%m-%d %H:%M')}\n")
                f.write("\n")
        
        print(f"\n[SUCCESS] Results saved to: {output_file}")
    else:
        print("\n[X] No matching videos found")
    
    print("=" * 80)

if __name__ == '__main__':
    main()

