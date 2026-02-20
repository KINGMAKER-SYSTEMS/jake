"""
YouTube Video Clipper - Creates overlapping 7-second clips from YouTube videos.

Uses ffmpeg direct stream copy to avoid frozen frame issues.
Clips are saved to C:\\Users\\jakeb\\temp_videos\\ by default.
"""

import subprocess
import os
import sys
import argparse
from pathlib import Path


def check_dependencies():
    """Verify that yt-dlp and ffmpeg are installed and available."""
    print("Checking dependencies...")

    # Check yt-dlp (try both yt-dlp and python -m yt_dlp)
    yt_dlp_cmd = None
    for cmd in [["yt-dlp", "--version"], ["python", "-m", "yt_dlp", "--version"]]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            print(f"[OK] yt-dlp found: {result.stdout.strip()}")
            yt_dlp_cmd = cmd[:-1]  # Store the command without --version
            break
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue

    if not yt_dlp_cmd:
        print("[ERROR] yt-dlp not found!")
        print("\nPlease install yt-dlp:")
        print("  pip install yt-dlp")
        print("  OR")
        print("  Download from: https://github.com/yt-dlp/yt-dlp/releases")
        sys.exit(1)

    # Check ffmpeg
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            check=True
        )
        version_line = result.stdout.split('\n')[0]
        print(f"[OK] ffmpeg found: {version_line}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[ERROR] ffmpeg not found!")
        print("\nPlease install ffmpeg:")
        print("  Windows: Download from https://ffmpeg.org/download.html")
        print("  Mac: brew install ffmpeg")
        print("  Linux: sudo apt install ffmpeg")
        sys.exit(1)

    print()
    return yt_dlp_cmd


def validate_url(url):
    """Basic validation for YouTube URLs."""
    valid_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
    return any(domain in url for domain in valid_domains)


def download_video(url, output_path, yt_dlp_cmd, max_duration=None):
    """
    Download YouTube video using yt-dlp.

    Args:
        url: YouTube video URL
        output_path: Path where video should be saved
        yt_dlp_cmd: Command to run yt-dlp (e.g., ['yt-dlp'] or ['python', '-m', 'yt_dlp'])
        max_duration: Maximum duration to download in seconds (optional)

    Returns:
        Path to downloaded video file
    """
    print(f"Downloading video from: {url}")
    if max_duration:
        print(f"Limiting to first {max_duration} seconds ({max_duration/60:.1f} minutes)")
    print(f"Saving to: {output_path}")
    print("This may take a few minutes depending on video size...\n")

    try:
        # Build yt-dlp command
        cmd = yt_dlp_cmd + [
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
        ]

        # Add duration limit if specified
        if max_duration:
            cmd.extend(["--download-sections", f"*0-{max_duration}"])

        cmd.extend(["-o", output_path, url])

        # Download best quality MP4
        subprocess.run(cmd, check=True)
        print(f"\n[OK] Download complete: {output_path}\n")
        return output_path

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Download failed: {e}")
        print("\nPossible causes:")
        print("  - Invalid URL")
        print("  - Network connection issues")
        print("  - Age-restricted or private video")
        print("  - Video unavailable in your region")
        sys.exit(1)


def get_video_duration(video_path):
    """
    Get duration of video using ffprobe.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds (float)
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ],
            capture_output=True,
            text=True,
            check=True
        )
        duration = float(result.stdout.strip())
        return duration

    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"[ERROR] Failed to get video duration: {e}")
        sys.exit(1)


def create_clips(video_path, output_dir, clip_duration=7, overlap_offset=3):
    """
    Create overlapping clips from video using ffmpeg stream copy.

    Args:
        video_path: Path to source video
        output_dir: Directory to save clips
        clip_duration: Length of each clip in seconds (default: 7)
        overlap_offset: Seconds between clip start times (default: 3)

    Returns:
        List of created clip paths
    """
    # Get total video duration
    total_duration = get_video_duration(video_path)
    print(f"Video duration: {total_duration:.1f} seconds")

    # Check if video is too short
    if total_duration < clip_duration:
        print(f"\n[WARNING] Video is shorter than {clip_duration} seconds.")
        print(f"Creating single clip of full video duration ({total_duration:.1f}s)")
        clip_duration = total_duration

    # Calculate clip start times
    start_times = []
    current_time = 0.0
    while current_time + clip_duration <= total_duration:
        start_times.append(current_time)
        current_time += overlap_offset

    # If we haven't reached the end, add one more clip starting near the end
    if start_times and start_times[-1] + clip_duration < total_duration - 1:
        start_times.append(total_duration - clip_duration)

    print(f"Creating {len(start_times)} clips with {overlap_offset}s offset...\n")

    # Create each clip
    clip_paths = []
    for idx, start_time in enumerate(start_times, 1):
        end_time = min(start_time + clip_duration, total_duration)

        # Output filename with timestamps
        clip_filename = f"clip_{idx:03d}_{start_time:.1f}s-{end_time:.1f}s.mp4"
        clip_path = os.path.join(output_dir, clip_filename)

        print(f"Creating clip {idx}/{len(start_times)}: {start_time:.1f}s - {end_time:.1f}s")

        try:
            # Use ffmpeg with re-encoding to ensure proper frame handling
            # Seek in input first (fast but imprecise), then re-encode for accuracy
            subprocess.run(
                [
                    "ffmpeg",
                    "-ss", str(start_time),          # Seek to start time (fast seek)
                    "-i", video_path,                 # Input file
                    "-t", str(clip_duration),         # Duration
                    "-c:v", "libx264",               # Re-encode video with H.264 (ensures no frozen frames)
                    "-preset", "fast",                # Fast encoding preset
                    "-crf", "23",                     # Quality (23 is good quality)
                    "-c:a", "aac",                    # Re-encode audio to AAC
                    "-b:a", "128k",                   # Audio bitrate
                    "-avoid_negative_ts", "make_zero", # Handle timestamp edge cases
                    "-y",                             # Overwrite if exists
                    clip_path
                ],
                capture_output=True,
                check=True
            )

            clip_paths.append(clip_path)

        except subprocess.CalledProcessError as e:
            print(f"  [ERROR] Failed to create clip {idx}: {e}")
            continue

    print(f"\n[OK] Created {len(clip_paths)} clips successfully!")
    return clip_paths


def get_file_size_mb(file_path):
    """Get file size in MB."""
    size_bytes = os.path.getsize(file_path)
    return size_bytes / (1024 * 1024)


def main():
    """Main function to parse arguments and orchestrate clipping process."""
    parser = argparse.ArgumentParser(
        description="YouTube Video Clipper - Creates overlapping 7-second clips",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python youtube_clipper.py "https://www.youtube.com/watch?v=VIDEO_ID"
  python youtube_clipper.py "https://youtu.be/VIDEO_ID" --clip-duration 10
  python youtube_clipper.py URL --overlap 4 --keep-original
        """
    )

    parser.add_argument(
        "url",
        help="YouTube video URL"
    )
    parser.add_argument(
        "--clip-duration",
        type=int,
        default=7,
        help="Duration of each clip in seconds (default: 7)"
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=3,
        help="Seconds between clip start times (default: 3, for 4s overlap with 7s clips)"
    )
    parser.add_argument(
        "--output-dir",
        default=r"C:\Users\jakeb\temp_videos",
        help="Output directory for clips (default: C:\\Users\\jakeb\\temp_videos)"
    )
    parser.add_argument(
        "--keep-original",
        action="store_true",
        help="Keep the original downloaded video (default: delete after clipping)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Maximum duration to download in seconds (e.g., 600 for 10 minutes)"
    )

    args = parser.parse_args()

    # Validate URL
    if not validate_url(args.url):
        print(f"[ERROR] Invalid URL: {args.url}")
        print("Please provide a valid YouTube URL (youtube.com or youtu.be)")
        sys.exit(1)

    # Check dependencies
    yt_dlp_cmd = check_dependencies()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_dir}\n")

    # Download video
    video_filename = "downloaded_video.mp4"
    video_path = output_dir / video_filename
    download_video(args.url, str(video_path), yt_dlp_cmd, max_duration=args.duration)

    # Create clips
    clip_paths = create_clips(
        str(video_path),
        str(output_dir),
        clip_duration=args.clip_duration,
        overlap_offset=args.overlap
    )

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total clips created: {len(clip_paths)}")
    print(f"Output directory: {output_dir}")

    if clip_paths:
        avg_size = sum(get_file_size_mb(p) for p in clip_paths) / len(clip_paths)
        print(f"Average clip size: {avg_size:.2f} MB")
        print(f"\nFirst clip: {os.path.basename(clip_paths[0])}")
        print(f"Last clip: {os.path.basename(clip_paths[-1])}")

    # Clean up original video
    if not args.keep_original:
        try:
            os.remove(video_path)
            print(f"\n[OK] Removed original video: {video_filename}")
        except Exception as e:
            print(f"\n[WARNING] Could not remove original video: {e}")
    else:
        print(f"\n[OK] Kept original video: {video_path}")

    print("\n[OK] All done! Check the output directory for your clips.")
    print(f"\nTo view clips: {output_dir}")


if __name__ == "__main__":
    main()
