#!/usr/bin/env python3
"""
Show current progress vs target view counts for each artist
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.get_post_links_by_song import scrape_account_videos

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

def main():
    start_date = datetime(2025, 12, 15, 0, 0)
    end_date = datetime.now()
    campaign_end = datetime(2026, 1, 15, 23, 59)

    accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']

    print("=" * 80)
    print("PROGRESS VS TARGETS - BEAU, CODY & GAVIN")
    print("=" * 80)
    print(f"Campaign Period: Dec 15, 2025 - Jan 15, 2026")
    print(f"Current Progress: {start_date.strftime('%b %d')} to {end_date.strftime('%b %d, %Y')}")
    print(f"Days Elapsed: {(end_date - start_date).days} / 31 days")
    print("=" * 80)

    # Scrape all accounts
    all_videos = []
    for account in accounts:
        print(f"\nScraping @{account}...")
        videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)
        all_videos.extend(videos)
        print(f"  Found {len(videos)} videos")

    print(f"\nTotal videos collected: {len(all_videos)}")

    # Group by artist
    artist_stats = defaultdict(lambda: {
        'views': 0,
        'likes': 0,
        'videos': 0
    })

    for video in all_videos:
        artist = normalize_artist(video.get('artist', 'Unknown'))
        artist_stats[artist]['views'] += video['views']
        artist_stats[artist]['likes'] += video['likes']
        artist_stats[artist]['videos'] += 1

    # Calculate progress
    results = []
    total_actual = 0
    total_target = sum(TARGETS.values())

    for artist, target in TARGETS.items():
        actual = artist_stats.get(artist, {}).get('views', 0)
        videos = artist_stats.get(artist, {}).get('videos', 0)
        likes = artist_stats.get(artist, {}).get('likes', 0)
        percentage = (actual / target * 100) if target > 0 else 0
        remaining = target - actual

        total_actual += actual

        results.append({
            'artist': artist,
            'target': target,
            'actual': actual,
            'videos': videos,
            'likes': likes,
            'percentage': percentage,
            'remaining': remaining
        })

    # Sort by percentage descending
    results.sort(key=lambda x: x['percentage'], reverse=True)

    # Save to file
    output_file = Path('output') / 'progress_vs_targets.txt'
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("PROGRESS VS TARGETS - BEAU, CODY & GAVIN\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Campaign Period: Dec 15, 2025 - Jan 15, 2026\n")
        f.write(f"Current Progress: {start_date.strftime('%b %d')} to {end_date.strftime('%b %d, %Y')}\n")
        f.write(f"Days Elapsed: {(end_date - start_date).days} / 31 days\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("=" * 80 + "\n")
        f.write("ARTIST PROGRESS BREAKDOWN\n")
        f.write("=" * 80 + "\n\n")

        for r in results:
            status = "✓ ON TRACK" if r['percentage'] >= 60 else "⚠ NEEDS ATTENTION" if r['percentage'] >= 30 else "✗ CRITICAL"
            f.write(f"{r['artist']}\n")
            f.write(f"  Target:      {r['target']:,} views\n")
            f.write(f"  Actual:      {r['actual']:,} views\n")
            f.write(f"  Videos:      {r['videos']}\n")
            f.write(f"  Likes:       {r['likes']:,}\n")
            f.write(f"  Progress:    {r['percentage']:.1f}%\n")
            f.write(f"  Remaining:   {r['remaining']:,} views\n")
            f.write(f"  Status:      {status}\n")
            f.write(f"  {'-' * 76}\n\n")

        overall_percentage = (total_actual / total_target * 100) if total_target > 0 else 0

        f.write("=" * 80 + "\n")
        f.write("OVERALL SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Total Target:     {total_target:,} views\n")
        f.write(f"Total Actual:     {total_actual:,} views\n")
        f.write(f"Overall Progress: {overall_percentage:.1f}%\n")
        f.write(f"Total Remaining:  {total_target - total_actual:,} views\n")
        f.write(f"Total Videos:     {len(all_videos)}\n\n")

    # Print to console
    print("\n" + "=" * 80)
    print("ARTIST PROGRESS BREAKDOWN")
    print("=" * 80 + "\n")

    for r in results:
        status = "✓" if r['percentage'] >= 60 else "⚠" if r['percentage'] >= 30 else "✗"
        print(f"{status} {r['artist']}")
        print(f"   Target: {r['target']:,} | Actual: {r['actual']:,} | Progress: {r['percentage']:.1f}%")
        print(f"   Remaining: {r['remaining']:,} views | Videos: {r['videos']}")
        print()

    overall_percentage = (total_actual / total_target * 100) if total_target > 0 else 0

    print("=" * 80)
    print("OVERALL SUMMARY")
    print("=" * 80)
    print(f"Total Target:     {total_target:,} views")
    print(f"Total Actual:     {total_actual:,} views")
    print(f"Overall Progress: {overall_percentage:.1f}%")
    print(f"Total Remaining:  {total_target - total_actual:,} views")
    print(f"Days Remaining:   {(campaign_end - end_date).days} days")

    print("\n" + "=" * 80)
    print(f"Full report saved to: {output_file}")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    main()
