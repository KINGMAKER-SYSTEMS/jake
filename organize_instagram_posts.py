#!/usr/bin/env python3
"""
Organize Instagram posts by song - will work once rate limits reset
"""

import sys
from pathlib import Path
from datetime import datetime
import instaloader
import re
import time

# Target songs to match
TARGET_SONGS = {
    'rarest hour': {'song': 'The Rarest Hour', 'artist': 'Amble', 'keywords': ['rarest hour', 'raresthour', 'amble']},
    'moonbeam': {'song': 'Moonbeam', 'artist': 'Cassandra Coleman', 'keywords': ['moonbeam', 'cassandra coleman']},
    'feel it coming my way': {'song': 'Feel It Coming My Way', 'artist': 'Penelope Road', 'keywords': ['feel it coming', 'feelitcoming', 'penelope road']},
    'chance encounter': {'song': 'Chance Encounter', 'artist': 'Penelope Road', 'keywords': ['chance encounter', 'chanceencounter', 'penelope road']},
    'my defender': {'song': 'My Defender', 'artist': 'Tate Butts', 'keywords': ['my defender', 'mydefender', 'tate butts']},
    'matches & gasoline': {'song': 'Matches & Gasoline', 'artist': 'Noah Rinker', 'keywords': ['matches', 'gasoline', 'noah rinker', 'matchesandgasoline']},
    'drift away': {'song': 'Drift Away', 'artist': 'Orville Peck', 'keywords': ['drift away', 'driftaway', 'orville peck']},
}

def normalize_text(text):
    """Normalize text for matching"""
    if not text:
        return ''
    # Remove special characters and normalize
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def match_post_to_song(caption, audio_title=None, hashtags=None):
    """Match a post to one of the target songs"""
    if not caption:
        caption = ''
    if not audio_title:
        audio_title = ''
    if not hashtags:
        hashtags = []
    
    # Combine all text
    all_text = normalize_text(caption + ' ' + audio_title + ' ' + ' '.join(hashtags))
    
    matches = []
    
    for key, song_info in TARGET_SONGS.items():
        # Check each keyword
        for keyword in song_info['keywords']:
            keyword_norm = normalize_text(keyword)
            if keyword_norm in all_text:
                matches.append(song_info)
                break
    
    return matches[0] if matches else None

def scrape_and_organize(username, start_date):
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
        return {}, []
    except Exception as e:
        print(f"Error accessing profile: {e}")
        print("Instagram may be rate-limiting. Please wait a few minutes and try again.")
        return {}, []
    
    posts_by_song = {}
    unmatched_posts = []
    total_posts = 0
    
    print(f"Fetching posts since {start_date}...")
    
    try:
        for post in profile.get_posts():
            # Check date
            post_date = post.date_utc.date()
            if post_date < start_date:
                break
            
            total_posts += 1
            if total_posts % 10 == 0:
                print(f"  Processed {total_posts} posts...")
            
            post_url = f"https://www.instagram.com/p/{post.shortcode}/"
            caption = post.caption or ''
            hashtags = post.caption_hashtags if hasattr(post, 'caption_hashtags') else []
            
            # Try to get audio title
            audio_title = None
            try:
                if hasattr(post, 'audio_title') and post.audio_title:
                    audio_title = post.audio_title
                elif hasattr(post, '_node') and post._node:
                    audio_info = post._node.get('audio', {})
                    if audio_info:
                        audio_title = audio_info.get('title')
            except:
                pass
            
            # Match to song
            matched_song = match_post_to_song(caption, audio_title, hashtags)
            
            if matched_song:
                song_key = f"{matched_song['song']} - {matched_song['artist']}"
                if song_key not in posts_by_song:
                    posts_by_song[song_key] = []
                posts_by_song[song_key].append({
                    'url': post_url,
                    'date': post_date,
                    'caption': caption[:300],
                    'audio_title': audio_title or 'Original Audio',
                    'likes': post.likes,
                    'comments': post.comments,
                })
            else:
                unmatched_posts.append({
                    'url': post_url,
                    'date': post_date,
                    'caption': caption[:100],
                    'audio_title': audio_title or 'Original Audio',
                })
            
            # Longer delay to avoid rate limiting
            time.sleep(2)
    
    except Exception as e:
        print(f"Error during scraping: {e}")
        print(f"Processed {total_posts} posts before error")
    
    print(f"\nTotal posts scraped: {total_posts}")
    print(f"Matched posts: {sum(len(posts) for posts in posts_by_song.values())}")
    print(f"Unmatched posts: {len(unmatched_posts)}")
    print()
    
    return posts_by_song, unmatched_posts

def main():
    username = 'coffeesentiments_'
    start_date = datetime(2025, 10, 15).date()
    
    posts_by_song, unmatched = scrape_and_organize(username, start_date)
    
    if not posts_by_song and not unmatched:
        print("No posts were scraped. Instagram may be rate-limiting.")
        print("Please wait a few minutes and try again.")
        return
    
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
                    f.write(f"   Audio: {post['audio_title']}\n")
                    f.write(f"   Likes: {post['likes']:,} | Comments: {post['comments']:,}\n")
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
            for post in unmatched[:10]:  # Show first 10
                f.write(f"{post['url']}\n")
                f.write(f"  Audio: {post['audio_title']}\n")
                if post['caption']:
                    f.write(f"  Caption: {post['caption']}...\n")
                f.write("\n")
            if len(unmatched) > 10:
                f.write(f"... and {len(unmatched) - 10} more unmatched posts\n")
    
    # Write copy/paste file (only matched posts, organized by song)
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
    if posts_by_song:
        print(f"\n{'=' * 80}")
        print("SUMMARY BY SONG:")
        print("=" * 80)
        for song_key, posts in sorted(posts_by_song.items()):
            print(f"{song_key}: {len(posts)} posts")

if __name__ == '__main__':
    main()

