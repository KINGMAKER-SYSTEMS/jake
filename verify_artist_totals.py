#!/usr/bin/env python3
"""
Verify actual artist totals to fix the discrepancy
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.get_post_links_by_song import scrape_account_videos

def main():
    start_date = datetime(2025, 12, 15, 0, 0)
    end_date = datetime.now()

    accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']

    print("=" * 80)
    print("VERIFYING ARTIST TOTALS - RAW DATA")
    print("=" * 80)

    # Scrape all accounts
    all_videos = []
    for account in accounts:
        print(f"\nScraping @{account}...")
        videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)
        all_videos.extend(videos)
        print(f"  Found {len(videos)} videos")

    print(f"\nTotal videos collected: {len(all_videos)}")

    # Group by raw artist name (no normalization)
    raw_artist_stats = defaultdict(lambda: {'views': 0, 'videos': 0, 'songs': set()})

    for video in all_videos:
        artist = video.get('artist', 'Unknown')
        song = video.get('song', 'Unknown')
        raw_artist_stats[artist]['views'] += video['views']
        raw_artist_stats[artist]['videos'] += 1
        raw_artist_stats[artist]['songs'].add(song)

    # Print all unique artist names
    print("\n" + "=" * 80)
    print("ALL UNIQUE ARTIST NAMES (RAW):")
    print("=" * 80)
    sorted_artists = sorted(raw_artist_stats.items(), key=lambda x: x[1]['views'], reverse=True)

    for artist, stats in sorted_artists:
        print(f"\nArtist: '{artist}'")
        print(f"  Total Views: {stats['views']:,}")
        print(f"  Total Videos: {stats['videos']}")
        print(f"  Unique Songs: {len(stats['songs'])}")
        if len(stats['songs']) <= 5:
            for song in stats['songs']:
                print(f"    - {song}")

    # Now group with proper normalization
    print("\n" + "=" * 80)
    print("GROUPED BY NORMALIZED ARTIST:")
    print("=" * 80)

    ARTIST_ALIASES = {
        'Pecos, the Rooftops': 'Pecos',
        'the Rooftops': 'Pecos',
        'Gannon Fremin, CCREV': 'Gannon Fremin',
        'CCREV': 'Gannon Fremin',
        'Gannon Fremin &CCREV': 'Gannon Fremin',
    }

    normalized_stats = defaultdict(lambda: {'views': 0, 'videos': 0})

    for video in all_videos:
        artist = video.get('artist', 'Unknown')
        normalized_artist = ARTIST_ALIASES.get(artist, artist)
        normalized_stats[normalized_artist]['views'] += video['views']
        normalized_stats[normalized_artist]['videos'] += 1

    sorted_normalized = sorted(normalized_stats.items(), key=lambda x: x[1]['views'], reverse=True)

    for artist, stats in sorted_normalized:
        print(f"\n{artist}:")
        print(f"  Total Views: {stats['views']:,}")
        print(f"  Total Videos: {stats['videos']}")

if __name__ == '__main__':
    main()
