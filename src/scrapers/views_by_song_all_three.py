#!/usr/bin/env python3
"""
Scrape beau, cody, and gavin and show views grouped by song
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.get_post_links_by_song import scrape_account_videos

def normalize_song_key(song, artist):
    """Create normalized song key for grouping"""
    song_clean = (song or 'Unknown').strip()
    artist_clean = (artist or 'Unknown').strip()
    return f"{song_clean} - {artist_clean}"

def main():
    start_date = datetime(2025, 11, 15, 0, 0)
    end_date = datetime.now()
    
    accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']
    
    print("=" * 80)
    print("SCRAPING ALL THREE ACCOUNTS - GROUPING BY SONG")
    print("=" * 80)
    print(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"Accounts: {', '.join([f'@{acc}' for acc in accounts])}")
    print("=" * 80)
    
    # Scrape all accounts
    all_videos = []
    for account in accounts:
        print(f"\nScraping @{account}...")
        videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)
        all_videos.extend(videos)
        print(f"  Found {len(videos)} videos")
    
    print(f"\nTotal videos collected: {len(all_videos)}")
    
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
        song = video.get('song', 'Unknown')
        artist = video.get('artist', 'Unknown')
        song_key = normalize_song_key(song, artist)
        
        songs_dict[song_key]['song'] = song
        songs_dict[song_key]['artist'] = artist
        songs_dict[song_key]['videos'].append(video)
        songs_dict[song_key]['accounts'].add(video['account'])
        songs_dict[song_key]['total_views'] += video['views']
        songs_dict[song_key]['total_likes'] += video['likes']
    
    # Sort by total views descending
    sorted_songs = sorted(songs_dict.items(), key=lambda x: x[1]['total_views'], reverse=True)
    
    # Print results
    print("\n" + "=" * 80)
    print("VIEWS BY SONG (All Three Accounts Combined)")
    print("=" * 80)
    
    for song_key, data in sorted_songs:
        print(f"\n{'=' * 80}")
        print(f"SONG: {data['song']}")
        print(f"ARTIST: {data['artist']}")
        print(f"Total Videos: {len(data['videos'])}")
        print(f"Accounts: {', '.join(sorted(data['accounts']))}")
        print(f"Total Views: {data['total_views']:,}")
        print(f"Total Likes: {data['total_likes']:,}")
        print(f"Average Views per Video: {data['total_views'] // len(data['videos']) if data['videos'] else 0:,}")
    
    # Save to file
    output_file = Path('output') / 'views_by_song_all_three_accounts.txt'
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("VIEWS BY SONG - BEAU, CODY & GAVIN COMBINED\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total videos: {len(all_videos)}\n")
        f.write(f"Unique songs: {len(songs_dict)}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("VIEWS BY SONG (Sorted by Total Views)\n")
        f.write("=" * 80 + "\n\n")
        
        for song_key, data in sorted_songs:
            f.write(f"{'=' * 80}\n")
            f.write(f"SONG: {data['song']}\n")
            f.write(f"ARTIST: {data['artist']}\n")
            f.write(f"Total Videos: {len(data['videos'])}\n")
            f.write(f"Accounts: {', '.join(sorted(data['accounts']))}\n")
            f.write(f"Total Views: {data['total_views']:,}\n")
            f.write(f"Total Likes: {data['total_likes']:,}\n")
            f.write(f"Average Views per Video: {data['total_views'] // len(data['videos']) if data['videos'] else 0:,}\n\n")
    
    print(f"\n{'=' * 80}")
    print(f"[SUCCESS] Results saved to: {output_file}")
    print(f"{'=' * 80}\n")

if __name__ == '__main__':
    main()

