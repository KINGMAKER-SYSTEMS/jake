#!/usr/bin/env python3
"""
Scrape Instagram account and match posts to specific audio tracks by caption keywords
"""

import sys
import instaloader
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

# ============================================================================
# AUDIO TRACKS TO MATCH
# Add your audio tracks here with keywords to search for in captions
# Format: "Display Name": ["keyword1", "keyword2", "artist name", etc.]
# ============================================================================

AUDIO_TRACKS = {
    "The Rarest Hour - Amble": ["rarest hour", "amble"],
    "Moonbeam - Cassandra Coleman": ["moonbeam", "cassandra coleman"],
    "Feel It Coming My Way - Penelope Road": ["feel it coming", "penelope road"],
    "Chance Encounter - Penelope Road": ["chance encounter", "penelope road"],
    "My Defender - Tate Butts": ["my defender", "tate butts"],
    "Matches & Gasoline - Noah Rinker": ["matches", "gasoline", "noah rinker"],
    "Drift Away - Orville Peck": ["drift away", "orville peck"],
}

def match_audio(caption, audio_tracks):
    """
    Match a caption to an audio track based on keywords
    Returns the audio name if matched, otherwise None
    """
    if not caption:
        return None

    caption_lower = caption.lower()

    # Check each audio track's keywords
    for audio_name, keywords in audio_tracks.items():
        for keyword in keywords:
            if keyword.lower() in caption_lower:
                return audio_name

    return None

def scrape_instagram_match_audios(username, start_date, audio_tracks):
    """Scrape Instagram account and match posts to audio tracks"""

    print("=" * 80)
    print(f"SCRAPING INSTAGRAM @{username}")
    print("=" * 80)
    print(f"Start date: {start_date.strftime('%Y-%m-%d')}")
    print(f"Tracking {len(audio_tracks)} audio tracks")
    print()

    # Initialize Instaloader
    L = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=True
    )

    try:
        profile = instaloader.Profile.from_username(L.context, username)
    except Exception as e:
        print(f"Error: Could not load profile @{username}: {e}")
        return

    print(f"Profile: @{profile.username}")
    print(f"Full name: {profile.full_name}")
    print(f"Followers: {profile.followers:,}")
    print(f"Total posts: {profile.mediacount:,}")
    print()

    # Group posts by audio
    posts_by_audio = defaultdict(list)
    total_posts = 0
    posts_in_range = 0
    matched_count = 0
    unmatched_count = 0

    print("Fetching posts...")

    for post in profile.get_posts():
        post_date = post.date_local

        # Stop if we've gone past the start date
        if post_date < start_date:
            break

        total_posts += 1
        posts_in_range += 1

        # Get post info
        post_url = f"https://www.instagram.com/p/{post.shortcode}/"
        likes = post.likes
        views = post.video_view_count if post.is_video else None
        caption = post.caption or ""

        # Try to match audio
        audio_name = match_audio(caption, audio_tracks)

        if audio_name:
            matched_count += 1
        else:
            audio_name = "Unknown Audio"
            unmatched_count += 1

        # Create post entry
        post_info = {
            'url': post_url,
            'date': post_date.strftime('%Y-%m-%d %H:%M'),
            'likes': likes,
            'views': views if views else 'N/A',
            'caption': caption[:150] + '...' if len(caption) > 150 else caption
        }

        posts_by_audio[audio_name].append(post_info)

        if total_posts % 10 == 0:
            print(f"  Processed {total_posts} posts... (Matched: {matched_count}, Unknown: {unmatched_count})")

    print(f"\nTotal posts processed: {posts_in_range}")
    print(f"Matched to audio tracks: {matched_count}")
    print(f"Unknown audio: {unmatched_count}")
    print(f"Unique audios found: {len(posts_by_audio)}")
    print()

    # Save results
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    detailed_file = output_dir / f'{username}_matched_audios_{timestamp}.txt'
    copy_paste_file = output_dir / f'{username}_matched_audios_{timestamp}_copy_paste.txt'

    # Write detailed file
    with open(detailed_file, 'w', encoding='utf-8') as f:
        f.write(f"INSTAGRAM @{username} - POSTS MATCHED TO AUDIO TRACKS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Date range: {start_date.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"Total posts: {posts_in_range}\n")
        f.write(f"Matched: {matched_count} | Unknown: {unmatched_count}\n")
        f.write(f"Unique audios: {len(posts_by_audio)}\n\n")

        # Sort by number of posts per audio (descending), but put Unknown last
        sorted_audios = sorted(
            [(name, posts) for name, posts in posts_by_audio.items() if name != "Unknown Audio"],
            key=lambda x: len(x[1]),
            reverse=True
        )

        # Add Unknown at the end if it exists
        if "Unknown Audio" in posts_by_audio:
            sorted_audios.append(("Unknown Audio", posts_by_audio["Unknown Audio"]))

        for audio_name, posts in sorted_audios:
            total_likes = sum(p['likes'] for p in posts)
            total_views = sum(p['views'] for p in posts if isinstance(p['views'], int))

            f.write("=" * 80 + "\n")
            f.write(f"AUDIO: {audio_name}\n")
            f.write(f"Posts: {len(posts)} | Total Likes: {total_likes:,}")
            if total_views > 0:
                f.write(f" | Total Views: {total_views:,}")
            f.write("\n")
            f.write("=" * 80 + "\n\n")

            for post in sorted(posts, key=lambda x: x['likes'], reverse=True):
                f.write(f"{post['url']}\n")
                f.write(f"  Date: {post['date']} | Likes: {post['likes']:,}")
                if isinstance(post['views'], int):
                    f.write(f" | Views: {post['views']:,}")
                f.write("\n")
                if post['caption']:
                    f.write(f"  Caption: {post['caption']}\n")
                f.write("\n")

    # Write copy/paste file
    with open(copy_paste_file, 'w', encoding='utf-8') as f:
        f.write(f"@{username} - POSTS BY AUDIO\n")
        f.write("=" * 80 + "\n\n")

        # Same sorting as above
        sorted_audios = sorted(
            [(name, posts) for name, posts in posts_by_audio.items() if name != "Unknown Audio"],
            key=lambda x: len(x[1]),
            reverse=True
        )
        if "Unknown Audio" in posts_by_audio:
            sorted_audios.append(("Unknown Audio", posts_by_audio["Unknown Audio"]))

        for audio_name, posts in sorted_audios:
            f.write(f"\n{audio_name} ({len(posts)} posts)\n")
            f.write("-" * 80 + "\n")
            for post in posts:
                f.write(f"{post['url']}\n")

    print(f"{'=' * 80}")
    print("[SUCCESS] Results saved to:")
    print(f"  Detailed: {detailed_file}")
    print(f"  Copy/Paste: {copy_paste_file}")
    print(f"{'=' * 80}\n")

    # Print summary
    print("SUMMARY BY AUDIO:")
    print("-" * 80)

    # Sort for display (known audios first, then unknown)
    display_audios = sorted(
        [(name, posts) for name, posts in posts_by_audio.items() if name != "Unknown Audio"],
        key=lambda x: len(x[1]),
        reverse=True
    )
    if "Unknown Audio" in posts_by_audio:
        display_audios.append(("Unknown Audio", posts_by_audio["Unknown Audio"]))

    for audio_name, posts in display_audios:
        total_likes = sum(p['likes'] for p in posts)
        print(f"{audio_name}: {len(posts)} posts, {total_likes:,} likes")

if __name__ == '__main__':
    username = 'coffeesentiments_'
    start_date = datetime(2025, 12, 15, 0, 0, tzinfo=timezone.utc)

    print("\nTracking these audio tracks:")
    for i, audio_name in enumerate(AUDIO_TRACKS.keys(), 1):
        print(f"  {i}. {audio_name}")
    print()

    scrape_instagram_match_audios(username, start_date, AUDIO_TRACKS)
