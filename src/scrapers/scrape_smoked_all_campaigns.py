#!/usr/bin/env python3
"""
Scrape @smoked.999 for all campaign sounds we've been tracking
"""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.get_post_links_by_song import scrape_account_videos

# Define campaign sounds to search for
CAMPAIGN_SOUNDS = [
    {'song': 'Your Eyes', 'artist': 'Night Tales'},
    {'song': "Where's Your Head At", 'artist': 'Eurotrip'},
    {'song': 'Collapse', 'artist': 'Chance Peña'},
    {'song': 'Tongue Tied', 'artist': 'Chance Peña'},
    {'song': 'When I Get Back On My Feet', 'artist': 'The Halfway Kid'},
    {'song': 'Heavy Foot', 'artist': 'Mon Rovîa'},
    {'song': 'Home for the Holidays', 'artist': 'The Bean Tones'},
    {'song': 'Turner Classic Christmas', 'artist': 'The Bean Tones'},
]

def matches_campaign(video, campaign):
    """Check if video matches a campaign sound"""
    video_song = video.get('song', '').lower()
    video_artist = video.get('artist', '').lower()
    
    campaign_song = campaign['song'].lower()
    campaign_artist = campaign['artist'].lower()
    
    # Check for song match
    song_match = campaign_song in video_song or video_song in campaign_song
    
    # Check for artist match (more flexible)
    artist_match = False
    if campaign_artist:
        # Split artist name into words for flexible matching
        artist_words = campaign_artist.split()
        if len(artist_words) > 1:
            # Check if key words match
            if 'chance' in campaign_artist.lower() and 'peña' in campaign_artist.lower():
                artist_match = 'chance' in video_artist and ('peña' in video_artist or 'pena' in video_artist)
            elif 'night' in campaign_artist.lower() and 'tale' in campaign_artist.lower():
                artist_match = 'night' in video_artist and 'tale' in video_artist
            elif 'halfway' in campaign_artist.lower() and 'kid' in campaign_artist.lower():
                artist_match = 'halfway' in video_artist and 'kid' in video_artist
            elif 'bean' in campaign_artist.lower() and 'tone' in campaign_artist.lower():
                artist_match = 'bean' in video_artist and 'tone' in video_artist
            else:
                # Check if main words match
                main_word = artist_words[0].lower()
                artist_match = main_word in video_artist
        else:
            artist_match = campaign_artist in video_artist or video_artist in campaign_artist
    
    return song_match and artist_match

def main():
    account = 'smoked.999'
    start_date = datetime(2025, 12, 1, 0, 0)  # From 12/01/25
    end_date = datetime.now()
    
    print("=" * 80)
    print("SCRAPING @smoked.999 FOR ALL CAMPAIGN SOUNDS")
    print("=" * 80)
    print(f"\nAccount: @{account}")
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
    print("\nCampaign sounds to search for:")
    for i, campaign in enumerate(CAMPAIGN_SOUNDS, 1):
        print(f"  {i}. {campaign['song']} - {campaign['artist']}")
    print("=" * 80)
    
    # Scrape videos from start date to now
    print(f"\nScraping @{account}...")
    videos = scrape_account_videos(account, start_datetime=start_date, end_datetime=end_date, limit=2000)
    
    print(f"Total videos scraped: {len(videos)}")
    
    # Group matches by campaign
    campaign_matches = {campaign['song']: [] for campaign in CAMPAIGN_SOUNDS}
    
    for video in videos:
        for campaign in CAMPAIGN_SOUNDS:
            if matches_campaign(video, campaign):
                campaign_matches[campaign['song']].append(video)
                break  # Only count once per video
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS BY CAMPAIGN")
    print("=" * 80)
    
    total_videos = 0
    total_views = 0
    total_likes = 0
    
    for campaign in CAMPAIGN_SOUNDS:
        song_name = campaign['song']
        matches = campaign_matches[song_name]
        
        if matches:
            total_videos += len(matches)
            campaign_views = sum(v['views'] for v in matches)
            campaign_likes = sum(v['likes'] for v in matches)
            total_views += campaign_views
            total_likes += campaign_likes
            
            sorted_matches = sorted(matches, key=lambda x: x['views'], reverse=True)
            
            print(f"\n{'=' * 80}")
            print(f"{song_name} - {campaign['artist']}")
            print(f"  Videos: {len(matches)}")
            print(f"  Total Views: {campaign_views:,}")
            print(f"  Total Likes: {campaign_likes:,}")
            print(f"\n  Top Videos:")
            for i, video in enumerate(sorted_matches[:5], 1):
                print(f"    {i}. {video['url']}")
                print(f"       Views: {video['views']:,} | Likes: {video['likes']:,}")
    
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total Campaign Videos Found: {total_videos}")
    print(f"Total Views: {total_views:,}")
    print(f"Total Likes: {total_likes:,}")
    
    # Save results
    output_file = Path(__file__).parent.parent.parent / 'output' / 'smoked_all_campaigns_results.txt'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("SMOKED.999 - ALL CAMPAIGN SOUNDS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Account: @{account}\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Total campaign videos: {total_videos}\n")
        f.write(f"Total views: {total_views:,}\n")
        f.write(f"Total likes: {total_likes:,}\n\n")
        
        for campaign in CAMPAIGN_SOUNDS:
            song_name = campaign['song']
            matches = campaign_matches[song_name]
            
            if matches:
                sorted_matches = sorted(matches, key=lambda x: x['views'], reverse=True)
                f.write(f"\n{'=' * 80}\n")
                f.write(f"{song_name} - {campaign['artist']}\n")
                f.write(f"Videos: {len(matches)} | Views: {sum(v['views'] for v in matches):,}\n")
                f.write(f"{'=' * 80}\n\n")
                
                for i, video in enumerate(sorted_matches, 1):
                    f.write(f"{i}. {video['url']}\n")
                    f.write(f"   Views: {video['views']:,} | Likes: {video['likes']:,}\n")
                    if video.get('timestamp'):
                        f.write(f"   Posted: {video['timestamp'].strftime('%Y-%m-%d %H:%M')}\n")
                    f.write("\n")
    
    print(f"\n[SUCCESS] Results saved to: {output_file}")
    print("=" * 80)

if __name__ == '__main__':
    main()

