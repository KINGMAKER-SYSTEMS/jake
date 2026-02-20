#!/usr/bin/env python3
"""
Detailed analysis of @beaujenkins account
Extracts all sounds used with statistics
"""

import sys
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src" / "scrapers"))

try:
    from robust_campaign_scraper import (
        scrape_tiktok_account,
        extract_sound_ids_parallel,
        get_profile_username,
        log
    )
except ImportError:
    # Try alternative location
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "robust_campaign_scraper",
        Path(__file__).parent / "src" / "scrapers" / "robust_campaign_scraper.py"
    )
    robust_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(robust_module)
    scrape_tiktok_account = robust_module.scrape_tiktok_account
    extract_sound_ids_parallel = robust_module.extract_sound_ids_parallel
    get_profile_username = robust_module.get_profile_username
    log = robust_module.log

def analyze_account(account, start_date=None, limit=2000):
    """Analyze an account and extract all sounds with statistics"""
    
    log(f"=== ANALYZING @{get_profile_username(account)} ===")
    if start_date:
        log(f"Start date: {start_date.date()}")
    log(f"Scraping up to {limit} videos...")
    
    # Scrape account without date filter (we'll filter manually to avoid date comparison issues)
    videos = scrape_tiktok_account(account, None, limit=limit, use_cache=False)
    log(f"Scraped {len(videos)} videos")
    
    # Filter by date manually
    if start_date:
        filtered_videos = []
        for video in videos:
            video_dt = video.get('timestamp')
            if video_dt:
                if isinstance(video_dt, datetime):
                    if video_dt >= start_date:
                        filtered_videos.append(video)
                elif hasattr(video_dt, 'date'):
                    if video_dt.date() >= start_date.date():
                        filtered_videos.append(video)
            else:
                # If no timestamp, include it (better to include than exclude)
                filtered_videos.append(video)
        videos = filtered_videos
        log(f"Filtered to {len(videos)} videos after {start_date.date()}")
    
    if not videos:
        log("No videos found!", "ERROR")
        return None
    
    # Extract sound IDs in parallel
    log("Extracting sound IDs from all videos...")
    videos_with_sound = extract_sound_ids_parallel(videos, max_workers=10)
    
    # Build sound catalog
    sound_catalog = defaultdict(lambda: {
        'sound_id': '',
        'song_title': '',
        'total_uses': 0,
        'videos': [],
        'total_views': 0,
        'total_likes': 0,
        'total_comments': 0,
        'total_shares': 0,
        'first_seen': None,
        'last_seen': None
    })
    
    videos_without_sound = []
    
    for video in videos_with_sound:
        sound_id = video.get('extracted_sound_id')
        song_title = video.get('extracted_song_title', 'Unknown')
        
        if sound_id:
            sound_data = sound_catalog[sound_id]
            
            # Update song info (use first occurrence)
            if not sound_data['song_title'] or sound_data['song_title'] == 'Unknown':
                sound_data['song_title'] = song_title
                sound_data['sound_id'] = sound_id
            
            # Track dates
            video_dt = video.get('timestamp')
            if video_dt:
                if isinstance(video_dt, datetime):
                    if not sound_data['first_seen'] or video_dt < sound_data['first_seen']:
                        sound_data['first_seen'] = video_dt
                    if not sound_data['last_seen'] or video_dt > sound_data['last_seen']:
                        sound_data['last_seen'] = video_dt
            
            # Aggregate stats
            sound_data['total_uses'] += 1
            sound_data['total_views'] += video.get('views', 0)
            sound_data['total_likes'] += video.get('likes', 0)
            sound_data['total_comments'] += video.get('comments', 0) if 'comments' in video else 0
            sound_data['total_shares'] += video.get('shares', 0) if 'shares' in video else 0
            
            sound_data['videos'].append({
                'url': video['url'],
                'views': video.get('views', 0),
                'likes': video.get('likes', 0),
                'timestamp': video_dt,
                'upload_date': video.get('upload_date', '')
            })
        else:
            videos_without_sound.append(video)
    
    log(f"Found {len(sound_catalog)} unique sounds")
    log(f"{len(videos_without_sound)} videos without sound ID")
    
    return {
        'sound_catalog': sound_catalog,
        'videos_without_sound': videos_without_sound,
        'total_videos': len(videos)
    }

def generate_reports(analysis, account, output_dir):
    """Generate CSV reports"""
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    
    username = get_profile_username(account)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Aggregated report (sounds summary)
    aggregated_file = output_dir / f"{username}_sounds_aggregated_{timestamp}.csv"
    
    with open(aggregated_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Sound ID',
            'Song Title',
            'Total Uses',
            'Total Views',
            'Avg Views per Video',
            'Total Likes',
            'Total Comments',
            'Total Shares',
            'Avg Engagement Rate (%)',
            'First Used',
            'Last Used',
            'Top Video URL',
            'Top Video Views'
        ])
        
        # Sort by total views descending
        sorted_sounds = sorted(
            analysis['sound_catalog'].items(),
            key=lambda x: x[1]['total_views'],
            reverse=True
        )
        
        for sound_id, data in sorted_sounds:
            total_uses = data['total_uses']
            avg_views = data['total_views'] / total_uses if total_uses > 0 else 0
            
            # Calculate engagement rate
            total_engagement = data['total_likes'] + data['total_comments'] + data['total_shares']
            engagement_rate = (total_engagement / data['total_views'] * 100) if data['total_views'] > 0 else 0
            
            # Find top video
            top_video = max(data['videos'], key=lambda v: v['views']) if data['videos'] else {}
            
            writer.writerow([
                sound_id,
                data['song_title'],
                total_uses,
                data['total_views'],
                f"{avg_views:,.0f}",
                data['total_likes'],
                data['total_comments'],
                data['total_shares'],
                f"{engagement_rate:.2f}",
                data['first_seen'].strftime('%Y-%m-%d') if data['first_seen'] else '',
                data['last_seen'].strftime('%Y-%m-%d') if data['last_seen'] else '',
                top_video.get('url', ''),
                top_video.get('views', 0)
            ])
    
    log(f"Generated aggregated report: {aggregated_file}")
    
    # Detailed report (all videos)
    detailed_file = output_dir / f"{username}_sounds_detailed_{timestamp}.csv"
    
    with open(detailed_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Video URL',
            'Sound ID',
            'Song Title',
            'Views',
            'Likes',
            'Comments',
            'Shares',
            'Upload Date',
            'Timestamp'
        ])
        
        # Sort by views descending
        all_videos = []
        for sound_id, data in analysis['sound_catalog'].items():
            for video in data['videos']:
                all_videos.append({
                    **video,
                    'sound_id': sound_id,
                    'song_title': data['song_title']
                })
        
        all_videos.sort(key=lambda v: v['views'], reverse=True)
        
        for video in all_videos:
            writer.writerow([
                video['url'],
                video['sound_id'],
                video['song_title'],
                video['views'],
                video['likes'],
                video.get('comments', 0),
                video.get('shares', 0),
                video.get('upload_date', ''),
                video['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if video.get('timestamp') else ''
            ])
    
    log(f"Generated detailed report: {detailed_file}")
    
    return aggregated_file, detailed_file

def print_summary(analysis):
    """Print a summary to console"""
    catalog = analysis['sound_catalog']
    
    print("\n" + "="*80)
    print(f"ACCOUNT ANALYSIS SUMMARY: @{get_profile_username('https://www.tiktok.com/@beaujenkins')}")
    print("="*80)
    print(f"\nTotal Videos Analyzed: {analysis['total_videos']}")
    print(f"Unique Sounds Found: {len(catalog)}")
    print(f"Videos Without Sound ID: {len(analysis['videos_without_sound'])}")
    
    # Top 10 sounds by views
    sorted_sounds = sorted(
        catalog.items(),
        key=lambda x: x[1]['total_views'],
        reverse=True
    )[:10]
    
    print("\n" + "-"*80)
    print("TOP 10 SOUNDS BY TOTAL VIEWS:")
    print("-"*80)
    print(f"{'Rank':<6} {'Song Title':<40} {'Uses':<8} {'Total Views':<15} {'Avg Views':<12}")
    print("-"*80)
    
    for rank, (sound_id, data) in enumerate(sorted_sounds, 1):
        avg_views = data['total_views'] / data['total_uses'] if data['total_uses'] > 0 else 0
        song_title = data['song_title'][:38] if len(data['song_title']) > 38 else data['song_title']
        print(f"{rank:<6} {song_title:<40} {data['total_uses']:<8} {data['total_views']:<15,} {avg_views:<12,.0f}")
    
    # Top 10 sounds by usage count
    sorted_by_uses = sorted(
        catalog.items(),
        key=lambda x: x[1]['total_uses'],
        reverse=True
    )[:10]
    
    print("\n" + "-"*80)
    print("TOP 10 MOST USED SOUNDS:")
    print("-"*80)
    print(f"{'Rank':<6} {'Song Title':<40} {'Uses':<8} {'Total Views':<15}")
    print("-"*80)
    
    for rank, (sound_id, data) in enumerate(sorted_by_uses, 1):
        song_title = data['song_title'][:38] if len(data['song_title']) > 38 else data['song_title']
        print(f"{rank:<6} {song_title:<40} {data['total_uses']:<8} {data['total_views']:<15,}")
    
    print("\n" + "="*80)

def main():
    account = "https://www.tiktok.com/@beaujenkins"
    start_date = datetime(2025, 11, 15, 0, 0, 0)
    
    # Analyze account
    analysis = analyze_account(account, start_date=start_date, limit=2000)
    
    if not analysis:
        return
    
    # Print summary
    print_summary(analysis)
    
    # Generate reports
    aggregated_file, detailed_file = generate_reports(analysis, account, "output")
    
    print(f"\n✅ Analysis complete!")
    print(f"   Aggregated report: {aggregated_file}")
    print(f"   Detailed report: {detailed_file}")

if __name__ == "__main__":
    main()

