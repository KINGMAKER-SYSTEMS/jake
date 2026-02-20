#!/usr/bin/env python3
"""run_internal_tiktoks.py

Run internal TikTok accounts scrape.

Default behavior:
- If a prior run timestamp exists, scrape from that timestamp → now ("since last run").
- Otherwise, scrape the last 36 hours.

This is the main entry point for internal account tracking.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

def _state_path() -> Path:
    # Keep state alongside outputs so scheduled runs can pick it up consistently.
    return (Path(__file__).resolve().parents[2] / 'output' / 'internal_tiktoks_last_run.json')


def _load_last_run() -> str | None:
    p = _state_path()
    try:
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding='utf-8'))
        return data.get('last_end_datetime')
    except Exception:
        return None


def _save_last_run(end_dt_str: str) -> None:
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({'last_end_datetime': end_dt_str}, indent=2), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(
        description='Run internal TikTok accounts scrape',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: since last run (falls back to last 36 hours)
  python run_internal_tiktoks.py

  # Custom date range
  python run_internal_tiktoks.py --start-datetime "2024-11-26 05:00" --end-datetime "2024-11-27 12:00"

  # From specific date/time to now
  python run_internal_tiktoks.py --start-datetime "2024-11-26 05:00"
        """
    )
    parser.add_argument(
        '--start-datetime',
        help='Start datetime (YYYY-MM-DD HH:MM or YYYY-MM-DD HH:MM:SS). Default: last run end time, else 36 hours ago'
    )
    parser.add_argument(
        '--end-datetime',
        help='End datetime (YYYY-MM-DD HH:MM or YYYY-MM-DD HH:MM:SS). Default: now'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("RUNNING INTERNAL TIKTOKS REPORT")
    print("=" * 80)
    print()

    script_path = Path(__file__).parent.parent / 'utils' / 'get_post_links_by_song.py'
    
    if not script_path.exists():
        print(f"[ERROR] Script not found: {script_path}")
        sys.exit(1)

    # Resolve default time window.
    end_dt = args.end_datetime or datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    start_dt = args.start_datetime
    if not start_dt:
        last = _load_last_run()
        if last:
            start_dt = last
            print(f"Using last run timestamp: {start_dt} -> {end_dt}")
        else:
            start_dt = (datetime.now() - timedelta(hours=36)).strftime('%Y-%m-%d %H:%M:%S')
            print(f"No last run timestamp found. Using fallback window: {start_dt} -> {end_dt}")

    try:
        # Build command with datetime arguments
        cmd = [
            sys.executable,
            str(script_path),
            '--start-datetime',
            start_dt,
            '--end-datetime',
            end_dt,
        ]

        # Call the main scraping script
        subprocess.run(
            cmd,
            capture_output=False,  # Let the child script print to console
            text=True,
            check=True,  # Raise an exception for non-zero exit codes
        )

        # Only advance last-run marker if the scrape succeeded.
        _save_last_run(end_dt)

        print("\n" + "=" * 80)
        print("Internal TikToks report completed successfully!")
        print(f"Saved last run end time: {_state_path()}")
        print("=" * 80)

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Internal TikToks report failed: {e}")
        print(f"Stderr: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"\n[ERROR] Script not found: {script_path}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

