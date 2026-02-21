#!/usr/bin/env python3
"""
Migrate local campaign data to Railway deployment
Uploads campaigns, creators, and matched videos via API
"""
import json
import csv
import sys
from pathlib import Path
import requests
from typing import Dict, List

# Railway deployment URL
RAILWAY_URL = "https://harmonious-joy-production-3f0f.up.railway.app"

# Local paths
BASE_DIR = Path(__file__).parent
CAMPAIGNS_DIR = BASE_DIR / "campaign_manager" / "campaigns"
ACTIVE_DIR = CAMPAIGNS_DIR / "active"

def load_json(path: Path) -> Dict:
    """Load JSON file"""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_creators(campaign_dir: Path) -> List[Dict]:
    """Load creators.csv"""
    csv_path = campaign_dir / "creators.csv"
    if not csv_path.exists():
        return []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def create_campaign_via_api(meta: Dict) -> bool:
    """Create campaign via Railway API"""
    # Use the campaign creation endpoint
    # Note: This doesn't exist yet, so we'll use a workaround
    print(f"  Campaign: {meta.get('title', meta.get('name', 'Unknown'))}")
    print(f"    Artist: {meta.get('artist', 'N/A')}")
    print(f"    Song: {meta.get('song', 'N/A')}")
    print(f"    Budget: ${meta.get('budget', 0)}")
    print(f"    Sound ID: {meta.get('sound_id', 'N/A')}")
    return True

def upload_campaign_data(slug: str, campaign_dir: Path, dry_run: bool = True):
    """Upload campaign data to Railway"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating: {slug}")
    print("-" * 60)

    # Load campaign metadata
    meta = load_json(campaign_dir / "campaign.json")
    if not meta:
        print(f"  [!]  No campaign.json found, skipping")
        return False

    # Load creators
    creators = load_creators(campaign_dir)
    print(f"  Creators: {len(creators)}")

    # Load matched videos
    matched_videos = load_json(campaign_dir / "matched_videos.json")
    if isinstance(matched_videos, list):
        print(f"  Matched videos: {len(matched_videos)}")
    else:
        print(f"  Matched videos: 0")

    # Load scrape log
    scrape_log = load_json(campaign_dir / "scrape_log.json")

    if dry_run:
        create_campaign_via_api(meta)
        print(f"  [OK] Would upload campaign metadata")
        print(f"  [OK] Would upload {len(creators)} creators")
        print(f"  [OK] Would upload matched videos and scrape log")
        return True

    # Actual upload via API
    payload = {
        "slug": slug,
        "campaign": meta,
        "creators": creators,
        "matched_videos": matched_videos if isinstance(matched_videos, list) else [],
        "scrape_log": scrape_log
    }

    try:
        response = requests.post(
            f"{RAILWAY_URL}/api/migrate/campaign",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        print(f"  [OK] Uploaded successfully")
        print(f"      Campaign dir: {result.get('campaign_dir', 'unknown')}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Upload failed: {e}")
        return False

def main():
    """Main migration script"""
    import argparse
    parser = argparse.ArgumentParser(description="Migrate campaigns to Railway")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview without uploading (default)")
    parser.add_argument("--upload", action="store_true",
                        help="Actually upload data to Railway")
    parser.add_argument("--campaign", type=str,
                        help="Migrate specific campaign slug")
    args = parser.parse_args()

    dry_run = not args.upload

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No data will be uploaded")
        print("Use --upload to actually migrate data")
        print("=" * 60)
    else:
        print("=" * 60)
        print("[WARNING]  LIVE MODE - Data will be uploaded to Railway")
        print(f"Target: {RAILWAY_URL}")
        print("=" * 60)
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled")
            return

    # Get campaigns to migrate
    if args.campaign:
        campaigns = [args.campaign]
    else:
        campaigns = [d.name for d in ACTIVE_DIR.iterdir() if d.is_dir()]

    print(f"\nFound {len(campaigns)} campaigns to migrate\n")

    # Migrate each campaign
    success_count = 0
    for slug in campaigns:
        campaign_dir = ACTIVE_DIR / slug
        if upload_campaign_data(slug, campaign_dir, dry_run=dry_run):
            success_count += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"Migration {'preview' if dry_run else 'complete'}: {success_count}/{len(campaigns)} campaigns")
    print("=" * 60)

    if dry_run:
        print("\nNext steps:")
        print("1. Review the data above")
        print("2. Run with --upload to actually migrate")
        print("3. Or manually recreate campaigns via web UI")
    else:
        print(f"\nCheck your campaigns at: {RAILWAY_URL}")

if __name__ == "__main__":
    main()
