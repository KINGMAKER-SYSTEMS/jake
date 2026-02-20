#!/usr/bin/env python3
"""
Scrape Instagram posts and match them to specific songs by checking captions/audio
"""

import sys
from pathlib import Path
from datetime import datetime
import instaloader
import re

# Add scrapers to path
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'scrapers'))

# Target songs to match
TARGET_SONGS = {
    'rarest hour': {'song': 'The Rarest Hour', 'artist': 'Amble'},
    'moonbeam': {'song': 'Moonbeam', 'artist': 'Cassandra Coleman'},
    'feel it coming my way': {'song': 'Feel It Coming My Way', 'artist': 'Penelope Road'},
    'chance encounter': {'song': 'Chance Encounter', 'artist': 'Penelope Road'},
    'my defender': {'song': 'My Defender', 'artist': 'Tate Butts'},
    'matches & gasoline': {'song': 'Matches & Gasoline', 'artist': 'Noah Rinker'},
    'matches and gasoline': {'song': 'Matches & Gasoline', 'artist': 'Noah Rinker'},
    'drift away': {'song': 'Drift Away', 'artist': 'Orville Peck'},
}

def normalize_text(text):
    """Normalize text for matching"""
    if not text:
        return ''
    return re.sub(r'[^\w\s]', '', text.lower())

def match_post_to_song(caption, audio_title=None):
    """Match a post to one of the target songs"""
    if not caption:
        caption = ''
    
    caption_normalized = normalize_text(caption)
    audio_normalized = normalize_text(audio_title) if audio_title else ''
    combined_text = caption_normalized + ' ' + audio_normalized
    
    matches = []
    
    for key, song_info in TARGET_SONGS.items():
        key_normalized = normalize_text(key)
        song_normalized = normalize_text(song_info['song'])
        artist_normalized = normalize_text(song_info['artist'])
        
        # Check if key words appear
        if key_normalized in combined_text:
            matches.append(song_info)
        elif song_normalized in combined_text and artist_normalized in combined_text:
            matches.append(song_info)
        elif song_normalized in combined_text:
            # Check if it's a partial match (e.g., "rarest hour" matches "the rarest hour")
            song_words = song_normalized.split()
            if len(song_words) >= 2 and all(word in combined_text for word in song_words if len(word) > 2):
                matches.append(song_info)
    
    return matches[0] if matches else None

def scrape_instagram_account(username, start_date):
    """Scrape Instagram account and organize by song"""
    print(f"Scraping Instagram @{username}...")
    print(f"Start date: {start_date}")
    print()
    
    L = instaloader.Instaloader(
        quiet=True,
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False
    )
    
    try:
        profile = instaloader.Profile.from_username(L.context, username)
    except instaloader.exceptions.ProfileNotExistsException:
        print(f"Profile @{username} not found")
        return {}
    
    posts_by_song = {}
    unmatched_posts = []
    total_posts = 0
    
    print(f"Fetching posts since {start_date}...")
    
    for post in profile.get_posts():
        # Check date
        post_date = post.date_utc.date()
        if post_date < start_date:
            break
        
        total_posts += 1
        post_url = f"https://www.instagram.com/p/{post.shortcode}/"
        caption = post.caption or ''
        
        # Try to get audio title (if available)
        audio_title = None
        if hasattr(post, 'audio_title') and post.audio_title:
            audio_title = post.audio_title
        
        # Match to song
        matched_song = match_post_to_song(caption, audio_title)
        
        if matched_song:
            song_key = f"{matched_song['song']} - {matched_song['artist']}"
            if song_key not in posts_by_song:
                posts_by_song[song_key] = []
            posts_by_song[song_key].append({
                'url': post_url,
                'date': post_date,
                'caption': caption[:200],  # First 200 chars
                'likes': post.likes,
                'comments': post.comments,
                'audio_title': audio_title
            })
        else:
            unmatched_posts.append({
                'url': post_url,
                'date': post_date,
                'caption': caption[:200],
                'audio_title': audio_title
            })
    
    print(f"\nTotal posts scraped: {total_posts}")
    print(f"Matched posts: {sum(len(posts) for posts in posts_by_song.values())}")
    print(f"Unmatched posts: {len(unmatched_posts)}")
    print()
    
    return posts_by_song, unmatched_posts

def main():
    username = 'coffeesentiments_'
    start_date = datetime(2025, 12, 7).date()
    
    posts_by_song, unmatched = scrape_instagram_account(username, start_date)
    
    # Write organized output
    output_file = Path('output') / 'coffeesentiments_instagram_organized.txt'
    copy_paste_file = Path('output') / 'coffeesentiments_instagram_copy_paste.txt'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("INSTAGRAM POSTS - COFFEESENTIMENTS (ORGANIZED BY SONG)\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date Range: {start_date} to {datetime.now().date()}\n")
        f.write(f"Account: @{username}\n\n")
        
        if posts_by_song:
            f.write("MATCHED POSTS BY SONG:\n")
            f.write("=" * 80 + "\n\n")
            
            for song_key, posts in sorted(posts_by_song.items()):
                f.write(f"\n{'=' * 80}\n")
                f.write(f"SONG: {song_key}\n")
                f.write(f"Total Posts: {len(posts)}\n")
                f.write("-" * 80 + "\n\n")
                
                for i, post in enumerate(posts, 1):
                    f.write(f"{i}. {post['url']}\n")
                    f.write(f"   Date: {post['date']}\n")
                    f.write(f"   Likes: {post['likes']:,} | Comments: {post['comments']:,}\n")
                    if post.get('audio_title'):
                        f.write(f"   Audio: {post['audio_title']}\n")
                    if post['caption']:
                        f.write(f"   Caption: {post['caption']}...\n")
                    f.write("\n")
        else:
            f.write("No posts matched the target songs.\n\n")
        
        if unmatched:
            f.write(f"\n{'=' * 80}\n")
            f.write(f"UNMATCHED POSTS ({len(unmatched)} posts)\n")
            f.write("=" * 80 + "\n\n")
            f.write("These posts didn't match any of the target songs:\n\n")
            for post in unmatched[:20]:  # Show first 20
                f.write(f"{post['url']}\n")
                if post.get('audio_title'):
                    f.write(f"  Audio: {post['audio_title']}\n")
                if post['caption']:
                    f.write(f"  Caption: {post['caption']}...\n")
                f.write("\n")
            if len(unmatched) > 20:
                f.write(f"... and {len(unmatched) - 20} more unmatched posts\n")
    
    # Write copy/paste file (only matched posts)
    with open(copy_paste_file, 'w', encoding='utf-8') as f:
        f.write("INSTAGRAM POSTS - COFFEESENTIMENTS (MATCHED SONGS ONLY)\n")
        f.write("=" * 80 + "\n\n")
        
        for song_key, posts in sorted(posts_by_song.items()):
            f.write(f"\n{song_key}\n")
            f.write("-" * 80 + "\n")
            for post in posts:
                f.write(f"{post['url']}\n")
    
    print(f"\nResults saved to:")
    print(f"  Organized: {output_file}")
    print(f"  Copy/Paste: {copy_paste_file}")
    
    # Print summary
    print(f"\n{'=' * 80}")
    print("SUMMARY BY SONG:")
    print("=" * 80)
    for song_key, posts in sorted(posts_by_song.items()):
        print(f"{song_key}: {len(posts)} posts")

if __name__ == '__main__':
    main()

