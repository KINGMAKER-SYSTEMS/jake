#!/usr/bin/env python3
"""
Scrape beau, cody, and gavin for statistics between December 15 and now
Show all songs used grouped by song
"""
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.get_post_links_by_song import scrape_account_videos, normalize_song_key

def main():
    accounts = ['beaujenkins', 'codyjames6.7', 'gavin.wilder1']
    
    # Start date: December 15, 2025
    start_date = datetime(2025, 12, 15, 0, 0)
    end_date = datetime.now()
    
    print("=" * 80)
    print("STATISTICS FOR BEAU JENKINS, CODY JAMES & GAVIN WILDER")
    print("=" * 80)
    print(f"\nDate range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print(f"Accounts: {', '.join(accounts)}")
    print("=" * 80)
    
    all_videos = []
    
    # Scrape each account
    for account in accounts:
        print(f"\nScraping @{account}...")
        videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)
        all_videos.extend(videos)
        print(f"  Found {len(videos)} videos in date range")
    
    print(f"\nTotal videos collected: {len(all_videos)}")
    
    # Group by song
    songs_dict = defaultdict(lambda: {
        'song': '',
        'artist': '',
        'videos': [],
        'accounts': set(),
        'total_views': 0,
        'total_likes': 0,
        'by_account': defaultdict(lambda: {'count': 0, 'views': 0, 'likes': 0})
    })
    
    for video in all_videos:
        song_key = normalize_song_key(video['song'], video['artist'])
        songs_dict[song_key]['song'] = video['song']
        songs_dict[song_key]['artist'] = video['artist']
        songs_dict[song_key]['videos'].append(video)
        songs_dict[song_key]['accounts'].add(video['account'])
        songs_dict[song_key]['total_views'] += video['views']
        songs_dict[song_key]['total_likes'] += video['likes']
        
        # Track by account
        acc = video['account']
        songs_dict[song_key]['by_account'][acc]['count'] += 1
        songs_dict[song_key]['by_account'][acc]['views'] += video['views']
        songs_dict[song_key]['by_account'][acc]['likes'] += video['likes']
    
    # Sort songs by total views (descending)
    sorted_songs = sorted(songs_dict.items(), key=lambda x: x[1]['total_views'], reverse=True)
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS GROUPED BY SONG")
    print("=" * 80)
    
    total_all_views = 0
    total_all_likes = 0
    
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
        
        # Show breakdown by account
        print(f"\n  Breakdown by Account:")
        for acc in sorted(data['accounts']):
            stats = data['by_account'][acc]
            print(f"    {acc}: {stats['count']} videos, {stats['views']:,} views, {stats['likes']:,} likes")
        
        total_all_views += data['total_views']
        total_all_likes += data['total_likes']
    
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total Songs Used: {len(songs_dict)}")
    print(f"Total Videos: {len(all_videos)}")
    print(f"Total Views (All Songs): {total_all_views:,}")
    print(f"Total Likes (All Songs): {total_all_likes:,}")
    
    # Save to file
    output_file = Path(__file__).parent.parent.parent / 'output' / 'dec15_stats_all_three.txt'
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("STATISTICS - BEAU JENKINS, CODY JAMES & GAVIN WILDER\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Accounts: {', '.join(accounts)}\n")
        f.write(f"Total videos: {len(all_videos)}\n")
        f.write(f"Total songs: {len(songs_dict)}\n")
        f.write(f"Total views: {total_all_views:,}\n")
        f.write(f"Total likes: {total_all_likes:,}\n\n")
        
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
            
            f.write(f"\n  Breakdown by Account:\n")
            for acc in sorted(data['accounts']):
                stats = data['by_account'][acc]
                f.write(f"    {acc}: {stats['count']} videos, {stats['views']:,} views, {stats['likes']:,} likes\n")
            
            f.write(f"\n  Videos:\n")
            sorted_videos = sorted(data['videos'], key=lambda x: x['views'], reverse=True)
            for i, video in enumerate(sorted_videos, 1):
                f.write(f"    {i}. {video['url']}\n")
                f.write(f"       {video['account']} | Views: {video['views']:,} | Likes: {video['likes']:,}\n")
    
    print(f"\n[SUCCESS] Results saved to: {output_file}")
    print("=" * 80)

if __name__ == '__main__':
    main()

