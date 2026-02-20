#!/usr/bin/env python3
"""
Fresh scrape of beau, cody, and gavin for latest view counts
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.get_post_links_by_song import scrape_account_videos, normalize_song_key

# Target view counts (Dec 15 - Jan 15)
TARGETS = {
    'Blake Whiten': 2_250_000,
    'Pecos': 2_000_000,
    'Warren Zeiders': 1_250_000,
    'Gannon Fremin': 500_000,
    'Maddox Batson': 500_000,
    'Gavin Adcock': 300_000,
    'Wesko': 100_000,
    'Adrien Nunez': 100_000,
}

ARTIST_ALIASES = {
    'Pecos, the Rooftops': 'Pecos',
    'the Rooftops': 'Pecos',
    'Gannon Fremin, CCREV': 'Gannon Fremin',
    'CCREV': 'Gannon Fremin',
}

def normalize_artist(artist):
    """Normalize artist name to match targets"""
    artist = (artist or 'Unknown').strip()
    return ARTIST_ALIASES.get(artist, artist)

def scrape_account(account, start_date, end_date):
    """Scrape an account and return statistics"""
    print(f"\nScraping @{account}...")
    videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)

    if not videos:
        return {
            'account': account,
            'videos': 0,
            'total_views': 0,
            'total_likes': 0,
            'avg_views': 0,
            'top_video_views': 0,
            'all_videos': []
        }

    videos_by_views = sorted(videos, key=lambda x: x['views'], reverse=True)
    total_views = sum(v['views'] for v in videos)
    total_likes = sum(v['likes'] for v in videos)
    avg_views = total_views // len(videos) if videos else 0

    return {
        'account': account,
        'videos': len(videos),
        'total_views': total_views,
        'total_likes': total_likes,
        'avg_views': avg_views,
        'top_video_views': videos_by_views[0]['views'] if videos_by_views else 0,
        'top_video_url': videos_by_views[0]['url'] if videos_by_views else '',
        'all_videos': videos
    }

def main():
    start_date = datetime(2025, 12, 15, 0, 0)
    end_date = datetime.now()
    
    accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']
    
    print("=" * 80)
    print("FRESH UPDATE - ALL THREE ACCOUNTS")
    print("=" * 80)
    print(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"Accounts: {', '.join([f'@{acc}' for acc in accounts])}")
    print("=" * 80)
    
    # Scrape all accounts
    results = {}
    for account in accounts:
        results[account] = scrape_account(account, start_date, end_date)
    
    # Print summary
    print("\n" + "=" * 80)
    print("FRESH STATISTICS SUMMARY")
    print("=" * 80)
    
    for account in accounts:
        stats = results[account]
        print(f"\n@{stats['account']}:")
        print(f"  Total Videos: {stats['videos']}")
        print(f"  Total Views: {stats['total_views']:,}")
        print(f"  Total Likes: {stats['total_likes']:,}")
        print(f"  Average Views per Video: {stats['avg_views']:,}")
        print(f"  Top Video Views: {stats['top_video_views']:,}")
    
    # Combined totals
    total_videos = sum(r['videos'] for r in results.values())
    total_views = sum(r['total_views'] for r in results.values())
    total_likes = sum(r['total_likes'] for r in results.values())
    combined_avg = total_views // total_videos if total_videos > 0 else 0
    
    print(f"\n{'=' * 80}")
    print("COMBINED TOTALS")
    print("=" * 80)
    print(f"Total Videos (All 3 Accounts): {total_videos}")
    print(f"Total Views (All 3 Accounts): {total_views:,}")
    print(f"Total Likes (All 3 Accounts): {total_likes:,}")
    print(f"Combined Average Views per Video: {combined_avg:,}")
    
    # Ranking
    print(f"\n{'=' * 80}")
    print("RANKING BY TOTAL VIEWS")
    print("=" * 80)
    sorted_by_views = sorted(results.items(), key=lambda x: x[1]['total_views'], reverse=True)
    for i, (account, stats) in enumerate(sorted_by_views, 1):
        print(f"{i}. @{stats['account']}: {stats['total_views']:,} views ({stats['videos']} videos)")

    # Aggregate by song
    print(f"\n{'=' * 80}")
    print("VIEWS BY SONG (ALL ACCOUNTS COMBINED)")
    print("=" * 80)

    songs_dict = defaultdict(lambda: {
        'song': '',
        'artist': '',
        'video_count': 0,
        'total_views': 0,
        'total_likes': 0,
        'accounts': set()
    })

    # Collect all videos from all accounts
    all_videos = []
    for account, stats in results.items():
        all_videos.extend(stats['all_videos'])

    # Group by song
    for video in all_videos:
        song_key = normalize_song_key(video['song'], video['artist'])
        songs_dict[song_key]['song'] = video['song']
        songs_dict[song_key]['artist'] = video['artist']
        songs_dict[song_key]['video_count'] += 1
        songs_dict[song_key]['total_views'] += video['views']
        songs_dict[song_key]['total_likes'] += video['likes']
        songs_dict[song_key]['accounts'].add(video['account'])

    # Sort by views
    sorted_songs = sorted(songs_dict.items(), key=lambda x: x[1]['total_views'], reverse=True)

    # Calculate progress vs targets for each song
    print(f"\n{'=' * 100}")
    print("SONGS WITH TARGET PROGRESS")
    print("=" * 100)
    print(f"\n{'Song':<40} {'Artist':<20} {'Videos':<8} {'Current Views':<15} {'Target':<15} {'Progress':<10}")
    print("-" * 100)

    # Group songs by artist for target matching
    artist_totals = defaultdict(lambda: {'views': 0, 'songs': []})

    for song_key, data in sorted_songs:
        normalized_artist = normalize_artist(data['artist'])
        artist_totals[normalized_artist]['views'] += data['total_views']
        artist_totals[normalized_artist]['songs'].append({
            'song': data['song'],
            'artist': data['artist'],
            'views': data['total_views'],
            'videos': data['video_count']
        })

    # Print songs grouped by artist with targets
    for artist in TARGETS.keys():
        if artist in artist_totals:
            target = TARGETS[artist]
            actual = artist_totals[artist]['views']
            progress = (actual / target * 100) if target > 0 else 0

            print(f"\n{artist.upper()} - Target: {target:,} | Actual: {actual:,} | Progress: {progress:.1f}%")
            print("-" * 100)

            for song_data in artist_totals[artist]['songs']:
                song_name = song_data['song'][:38] + '..' if len(song_data['song']) > 40 else song_data['song']
                artist_name = song_data['artist'][:18] + '..' if len(song_data['artist']) > 20 else song_data['artist']

                print(f"  {song_name:<40} {artist_name:<20} {song_data['videos']:<8} {song_data['views']:<15,} {'-':<15} {'-':<10}")

    # Print songs without targets (Other)
    other_songs = []
    for song_key, data in sorted_songs:
        normalized_artist = normalize_artist(data['artist'])
        if normalized_artist not in TARGETS:
            other_songs.append(data)

    if other_songs:
        print(f"\n{'OTHER (NO TARGET)'}")
        print("-" * 100)
        for song_data in other_songs:
            song_name = song_data['song'][:38] + '..' if len(song_data['song']) > 40 else song_data['song']
            artist_name = song_data['artist'][:18] + '..' if len(song_data['artist']) > 20 else song_data['artist']

            print(f"  {song_name:<40} {artist_name:<20} {song_data['video_count']:<8} {song_data['total_views']:<15,} {'-':<15} {'-':<10}")

    print(f"\n{'=' * 100}")
    print("OVERALL PROGRESS")
    print("=" * 100)

    total_target = sum(TARGETS.values())
    total_actual_targeted = sum(artist_totals[artist]['views'] for artist in TARGETS.keys() if artist in artist_totals)
    overall_progress = (total_actual_targeted / total_target * 100) if total_target > 0 else 0

    print(f"Total Target:     {total_target:,} views")
    print(f"Total Actual:     {total_actual_targeted:,} views")
    print(f"Overall Progress: {overall_progress:.1f}%")
    print(f"Remaining:        {total_target - total_actual_targeted:,} views")
    print()
    
    # Save to file
    output_file = Path('output') / 'fresh_update_beau_cody_gavin.txt'
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("FRESH UPDATE - BEAU, CODY & GAVIN STATISTICS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("STATISTICS SUMMARY\n")
        f.write("=" * 80 + "\n")
        
        for account in accounts:
            stats = results[account]
            f.write(f"\n@{stats['account']}:\n")
            f.write(f"  Total Videos: {stats['videos']}\n")
            f.write(f"  Total Views: {stats['total_views']:,}\n")
            f.write(f"  Total Likes: {stats['total_likes']:,}\n")
            f.write(f"  Average Views per Video: {stats['avg_views']:,}\n")
            f.write(f"  Top Video Views: {stats['top_video_views']:,}\n")
            if stats['top_video_url']:
                f.write(f"  Top Video: {stats['top_video_url']}\n")
        
        f.write(f"\n{'=' * 80}\n")
        f.write("COMBINED TOTALS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Videos (All 3 Accounts): {total_videos}\n")
        f.write(f"Total Views (All 3 Accounts): {total_views:,}\n")
        f.write(f"Total Likes (All 3 Accounts): {total_likes:,}\n")
        f.write(f"Combined Average Views per Video: {combined_avg:,}\n")
        
        f.write(f"\n{'=' * 80}\n")
        f.write("RANKING BY TOTAL VIEWS\n")
        f.write("=" * 80 + "\n")
        for i, (account, stats) in enumerate(sorted_by_views, 1):
            f.write(f"{i}. @{stats['account']}: {stats['total_views']:,} views ({stats['videos']} videos)\n")

        f.write(f"\n{'=' * 100}\n")
        f.write("SONGS WITH TARGET PROGRESS\n")
        f.write("=" * 100 + "\n\n")
        f.write(f"{'Song':<40} {'Artist':<20} {'Videos':<8} {'Current Views':<15} {'Target':<15} {'Progress':<10}\n")
        f.write("-" * 100 + "\n")

        # Print songs grouped by artist with targets
        for artist in TARGETS.keys():
            if artist in artist_totals:
                target = TARGETS[artist]
                actual = artist_totals[artist]['views']
                progress = (actual / target * 100) if target > 0 else 0

                f.write(f"\n{artist.upper()} - Target: {target:,} | Actual: {actual:,} | Progress: {progress:.1f}%\n")
                f.write("-" * 100 + "\n")

                for song_data in artist_totals[artist]['songs']:
                    song_name = song_data['song'][:38] + '..' if len(song_data['song']) > 40 else song_data['song']
                    artist_name = song_data['artist'][:18] + '..' if len(song_data['artist']) > 20 else song_data['artist']

                    f.write(f"  {song_name:<40} {artist_name:<20} {song_data['videos']:<8} {song_data['views']:<15,} {'-':<15} {'-':<10}\n")

        # Print songs without targets (Other)
        if other_songs:
            f.write(f"\n{'OTHER (NO TARGET)'}\n")
            f.write("-" * 100 + "\n")
            for song_data in other_songs:
                song_name = song_data['song'][:38] + '..' if len(song_data['song']) > 40 else song_data['song']
                artist_name = song_data['artist'][:18] + '..' if len(song_data['artist']) > 20 else song_data['artist']

                f.write(f"  {song_name:<40} {artist_name:<20} {song_data['video_count']:<8} {song_data['total_views']:<15,} {'-':<15} {'-':<10}\n")

        f.write(f"\n{'=' * 100}\n")
        f.write("OVERALL PROGRESS\n")
        f.write("=" * 100 + "\n")
        f.write(f"Total Target:     {total_target:,} views\n")
        f.write(f"Total Actual:     {total_actual_targeted:,} views\n")
        f.write(f"Overall Progress: {overall_progress:.1f}%\n")
        f.write(f"Remaining:        {total_target - total_actual_targeted:,} views\n\n")

    print(f"\n{'=' * 80}")
    print(f"[SUCCESS] Results saved to: {output_file}")
    print(f"{'=' * 80}\n")

if __name__ == '__main__':
    main()

