#!/usr/bin/env python3
"""run_cobrand_campaigns_since_last_run.py

Efficient Cobrand campaign runner:
- Reads tracker-format campaign CSVs from output/campaigns/
- Dedupes creators across campaigns
- Scrapes each creator ONCE (cached)
- Extracts a single TikTok sound_id per post
- Matches posts to at most one campaign (sound_id -> campaign is enforced unique)
- Writes per-campaign results + links files
- Tracks a since-last-run window via output/cobrand_campaigns_last_run.json

This is designed to replace run_all_campaigns_with_cache_check.py for Cobrand-synced campaigns.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path so we can import sibling modules when executed directly.
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Reuse proven scraping + caching utilities from master_tracker
from src.scrapers.master_tracker import (
    scrape_tiktok_account,
    extract_sound_ids_parallel,
    get_profile_username,
)

CAMPAIGNS_DIR = PROJECT_ROOT / "output" / "campaigns"
OUTPUT_DIR = PROJECT_ROOT / "output"
STATE_PATH = OUTPUT_DIR / "cobrand_campaigns_last_run.json"
CAMPAIGN_STATE_PATH = OUTPUT_DIR / "cobrand_campaign_last_run.json"


@dataclass
class Campaign:
    key: str
    artist: str
    song: str
    sound_ids: list[str]
    csv_path: Path


def _load_state() -> str | None:
    try:
        if not STATE_PATH.exists():
            return None
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return data.get("last_end_datetime")
    except Exception:
        return None


def _save_state(end_dt_str: str) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps({"last_end_datetime": end_dt_str}, indent=2), encoding="utf-8")


def _load_campaign_state() -> dict[str, str]:
    try:
        if not CAMPAIGN_STATE_PATH.exists():
            return {}
        return json.loads(CAMPAIGN_STATE_PATH.read_text(encoding='utf-8')) or {}
    except Exception:
        return {}


def _save_campaign_state(state: dict[str, str]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CAMPAIGN_STATE_PATH.write_text(json.dumps(state, indent=2), encoding='utf-8')


def _parse_dt(s: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    raise ValueError(f"Invalid datetime: {s}")


def load_campaign_csvs() -> tuple[list[Campaign], dict[str, str], set[str]]:
    """Return (campaigns, sound_id_to_campaign_key, all_accounts)

    Enforces: each sound_id belongs to only one campaign. If duplicates exist, raises.
    """
    if not CAMPAIGNS_DIR.exists():
        raise FileNotFoundError(f"Missing campaigns dir: {CAMPAIGNS_DIR}")

    campaigns_by_key: dict[str, Campaign] = {}
    sound_to_campaign: dict[str, str] = {}
    all_accounts: set[str] = set()

    csv_files = sorted(CAMPAIGNS_DIR.glob("*.csv"))
    if not csv_files:
        raise RuntimeError(f"No campaign CSVs found in {CAMPAIGNS_DIR}")

    for p in csv_files:
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            rows = list(r)

        for row in rows:
            account = (row.get("Account") or "").strip()
            song = (row.get("Song") or "").strip()
            artist = (row.get("Artist") or "").strip()
            sid = (row.get("Tiktok Sound ID") or "").strip()

            if not account or not artist or not song or not sid:
                continue

            all_accounts.add(account)
            key = f"{artist} - {song}"

            if key not in campaigns_by_key:
                campaigns_by_key[key] = Campaign(key=key, artist=artist, song=song, sound_ids=[], csv_path=p)

            if sid not in campaigns_by_key[key].sound_ids:
                campaigns_by_key[key].sound_ids.append(sid)

            if sid in sound_to_campaign and sound_to_campaign[sid] != key:
                raise RuntimeError(
                    f"Sound ID {sid} maps to multiple campaigns: '{sound_to_campaign[sid]}' and '{key}'."
                )
            sound_to_campaign[sid] = key

    return list(campaigns_by_key.values()), sound_to_campaign, all_accounts


def write_campaign_outputs(campaign: Campaign, matched: list[dict[str, Any]], run_tag: str) -> tuple[Path, Path]:
    out_dir = PROJECT_ROOT / "src" / "scrapers" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    safe = (campaign.key.replace("/", "-").replace("\\", "-")
            .replace(":", "-").replace("  ", " "))
    safe = "_".join(safe.split())

    results_csv = out_dir / f"{safe}_results_{run_tag}.csv"
    links_txt = out_dir / f"{safe}_links_{run_tag}.txt"

    # Results CSV
    fieldnames = [
        "campaign",
        "artist",
        "song",
        "account",
        "url",
        "upload_date",
        "views",
        "likes",
        "sound_id",
        "sound_title",
    ]
    with results_csv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for v in matched:
            w.writerow({
                "campaign": campaign.key,
                "artist": campaign.artist,
                "song": campaign.song,
                "account": v.get("account"),
                "url": v.get("url"),
                "upload_date": v.get("upload_date"),
                "views": v.get("views"),
                "likes": v.get("likes"),
                "sound_id": v.get("extracted_sound_id"),
                "sound_title": v.get("extracted_sound_title"),
            })

    # Links file
    with links_txt.open("w", encoding="utf-8") as f:
        for v in matched:
            f.write(f"{v.get('url')}\n")

    return results_csv, links_txt


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all Cobrand campaign scrapes since last run")
    parser.add_argument("--start-datetime", help="Override start datetime (YYYY-MM-DD HH:MM[:SS])")
    parser.add_argument("--end-datetime", help="Override end datetime (YYYY-MM-DD HH:MM[:SS])")
    parser.add_argument("--fallback-hours", type=int, default=48,
                        help="If no last-run state exists, scrape this many hours back (default 48)")
    parser.add_argument("--max-account-workers", type=int, default=3,
                        help="Parallelism for account scraping")
    parser.add_argument("--max-sound-workers", type=int, default=10,
                        help="Parallelism for sound-id extraction")
    args = parser.parse_args()

    # Ensure UTF-8 output on Windows so emoji/diacritics never crash the run.
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        import sys as _sys
        if hasattr(_sys.stdout, "reconfigure"):
            _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(_sys.stderr, "reconfigure"):
            _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    end_dt = _parse_dt(args.end_datetime) if args.end_datetime else datetime.now()
    end_dt_str = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    start_dt_str = args.start_datetime or _load_state()
    if start_dt_str:
        start_dt = _parse_dt(start_dt_str)
        print(f"Using since-last-run window: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} -> {end_dt_str}")
    else:
        start_dt = end_dt - timedelta(hours=args.fallback_hours)
        print(f"No last-run state found. Using fallback window: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} -> {end_dt_str}")

    campaigns, sound_to_campaign, accounts = load_campaign_csvs()
    print(f"Loaded {len(campaigns)} campaigns from {CAMPAIGNS_DIR}")
    print(f"Deduped creators: {len(accounts)}")

    # Scrape creators once
    all_videos: list[dict[str, Any]] = []
    for i, acct in enumerate(sorted(accounts), 1):
        username = get_profile_username(acct) or acct
        print(f"[{i}/{len(accounts)}] Scraping @{username}...")
        # master_tracker.scrape_tiktok_account mixes date + datetime internally; pass date for compatibility.
        vids = scrape_tiktok_account(acct, start_date=start_dt.date(), limit=500, use_cache=True)
        all_videos.extend(vids)

    print(f"Collected {len(all_videos)} videos (pre-sound extraction)")

    # Extract sound ids for the collected videos
    # Monkey-patch master_tracker worker settings by temporarily overriding globals via function defaults isn’t easy;
    # instead we rely on its internal MAX_WORKERS but keep input size bounded by time window.
    enhanced = extract_sound_ids_parallel(all_videos, max_workers=args.max_sound_workers)

    # Match to campaigns
    by_campaign: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for v in enhanced:
        sid = v.get("extracted_sound_id")
        if not sid:
            continue
        key = sound_to_campaign.get(str(sid))
        if not key:
            continue
        by_campaign[key].append(v)

    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    total_matches = 0
    campaign_state = _load_campaign_state()

    for c in campaigns:
        matched = by_campaign.get(c.key, [])
        total_matches += len(matched)
        if not matched:
            # Still update per-campaign timestamp so you know it ran
            campaign_state[c.key] = end_dt_str
            continue
        results_csv, links_txt = write_campaign_outputs(c, matched, run_tag)
        campaign_state[c.key] = end_dt_str
        print(f"[MATCHES] {c.key}: {len(matched)} -> {results_csv.name}, {links_txt.name}")

    _save_campaign_state(campaign_state)
    _save_state(end_dt_str)
    print(f"Saved last run state: {STATE_PATH}")
    print(f"Saved per-campaign state: {CAMPAIGN_STATE_PATH}")
    print(f"Total matches across campaigns: {total_matches}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
