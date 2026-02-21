#!/usr/bin/env python3
"""
campaign_manager/migrate_to_postgres.py
=========================================
One-time migration from JSON files + SQLite tracker.db -> PostgreSQL.

Usage:
  python campaign_manager/migrate_to_postgres.py           # dry run (default)
  python campaign_manager/migrate_to_postgres.py --execute # write to Postgres
  python campaign_manager/migrate_to_postgres.py --only campaigns --execute

Requires DATABASE_URL env var (or PGHOST/PGUSER/etc.) to be set.
Original JSON files are NOT modified — they remain as the implicit backup.
"""

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

# Ensure the repo root is importable
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import campaign_manager.db as db
import psycopg2.extras

# ---------------------------------------------------------------------------
# Source file paths
# ---------------------------------------------------------------------------

BOOKINGS_JSON      = REPO_ROOT / "campaign_automation" / "bookings.json"
TRACKER_DATA_JSON  = REPO_ROOT / "campaign_automation" / "tracker_data.json"
PAYMENT_DATA_JSON  = REPO_ROOT / "campaign_automation" / "payment_data.json"
CAMPAIGN_SOUNDS_JSON = REPO_ROOT / "config" / "campaign_sounds.json"
SQLITE_DB          = REPO_ROOT / "tracker.db"


def _load_json(path: Path) -> dict | list:
    if not path.exists():
        print(f"  [skip] {path} not found")
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Step 1: Campaigns (from config/campaign_sounds.json)
# ---------------------------------------------------------------------------

def migrate_campaigns(dry_run: bool = True) -> int:
    """
    Source: campaign_sounds.json
    Key   = tiktok_sound_id
    Value = list of campaign dicts (usually 1 per sound ID)
    """
    data = _load_json(CAMPAIGN_SOUNDS_JSON)
    if not data:
        return 0

    to_insert = []
    for sound_id, entries in data.items():
        if not isinstance(entries, list):
            entries = [entries]
        for entry in entries:
            to_insert.append({
                "title":           entry.get("campaign", "").strip(),
                "artist":          entry.get("artist", "").strip(),
                "song":            entry.get("song", "").strip(),
                "tiktok_sound_id": sound_id.strip() or None,
                "cobrand_link":    entry.get("cobrand_link", "").strip(),
                "round":           entry.get("round", "").strip(),
                "label":           entry.get("label", "").strip(),
                "pipeline_status": "active",
            })

    # Deduplicate by sound_id (take first entry per sound)
    seen_sounds = set()
    deduped = []
    for row in to_insert:
        key = row["tiktok_sound_id"] or row["title"]
        if key not in seen_sounds:
            seen_sounds.add(key)
            deduped.append(row)

    print(f"  Campaigns to insert: {len(deduped)}")

    if dry_run:
        for r in deduped[:5]:
            print(f"    - {r['title']} ({r['artist']}) sound={r['tiktok_sound_id']}")
        if len(deduped) > 5:
            print(f"    ... and {len(deduped) - 5} more")
        return len(deduped)

    inserted = 0
    with db.get_db() as conn:
        cur = db._cursor(conn)
        for row in deduped:
            # Each insert gets its own connection so one failure doesn't abort the batch
            try:
                with db.get_db() as _conn:
                    _cur = db._cursor(_conn)
                    if row["tiktok_sound_id"]:
                        # Use partial-index-aware ON CONFLICT
                        _cur.execute(
                            """
                            INSERT INTO campaigns
                                (title, artist, song, tiktok_sound_id, cobrand_link, round, label, pipeline_status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (tiktok_sound_id)
                                WHERE tiktok_sound_id IS NOT NULL AND tiktok_sound_id != ''
                            DO NOTHING
                            """,
                            (
                                row["title"], row["artist"], row["song"],
                                row["tiktok_sound_id"], row["cobrand_link"],
                                row["round"], row["label"], row["pipeline_status"],
                            ),
                        )
                    else:
                        _cur.execute(
                            """
                            INSERT INTO campaigns
                                (title, artist, song, tiktok_sound_id, cobrand_link, round, label, pipeline_status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                row["title"], row["artist"], row["song"],
                                None, row["cobrand_link"],
                                row["round"], row["label"], row["pipeline_status"],
                            ),
                        )
                    if _cur.rowcount > 0:
                        inserted += 1
            except Exception as e:
                print(f"    [warn] Skipped '{row['title']}': {e}")

    print(f"  Inserted: {inserted} campaigns")
    return inserted


# ---------------------------------------------------------------------------
# Step 2: Creator PayPal registry
# ---------------------------------------------------------------------------

def migrate_paypal_registry(dry_run: bool = True) -> int:
    bookings_data = _load_json(BOOKINGS_JSON)
    tracker_data  = _load_json(TRACKER_DATA_JSON)

    paypal_db: dict[str, str] = {}
    paypal_db.update(bookings_data.get("paypal_db", {}))
    paypal_db.update(tracker_data.get("paypal_db", {}))  # tracker takes precedence

    # Normalise keys: strip @, lowercase
    normalised = {
        k.lower().lstrip("@"): v
        for k, v in paypal_db.items()
        if v and "@" in v
    }
    print(f"  PayPal records to upsert: {len(normalised)}")

    if dry_run:
        for k, v in list(normalised.items())[:5]:
            print(f"    {k} -> {v}")
        return len(normalised)

    with db.get_db() as conn:
        cur = db._cursor(conn)
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO creator_paypal (username, paypal)
            VALUES %s
            ON CONFLICT (username) DO UPDATE
                SET paypal = EXCLUDED.paypal, updated_at = NOW()
            """,
            [(k, v) for k, v in normalised.items()],
        )
    print(f"  Upserted: {len(normalised)} PayPal records")
    return len(normalised)


# ---------------------------------------------------------------------------
# Step 3: Bookings (from campaign_automation/bookings.json)
# ---------------------------------------------------------------------------

def migrate_bookings(dry_run: bool = True) -> int:
    data = _load_json(BOOKINGS_JSON)
    bookings = data.get("bookings", [])
    print(f"  Bookings to migrate: {len(bookings)}")

    if dry_run:
        for b in bookings[:5]:
            print(f"    id={b.get('id')} username={b.get('username')} campaign={b.get('campaign')} status={b.get('status')}")
        if len(bookings) > 5:
            print(f"    ... and {len(bookings) - 5} more")
        return len(bookings)

    # Build campaign lookup: title -> id
    campaign_map = _build_campaign_map()

    inserted = 0
    skipped = 0
    unmatched_campaigns: list[str] = []

    with db.get_db() as conn:
        cur = db._cursor(conn)
        for b in bookings:
            booking_id = b.get("id")
            if not booking_id:
                continue

            campaign_name = b.get("campaign", "")
            campaign_id = _fuzzy_campaign_id(campaign_name, campaign_map)
            if not campaign_id:
                unmatched_campaigns.append(campaign_name)

            # For 'paid' records without paid_at, use completed_at as approximation
            status = b.get("status", "booked")
            paid_at = b.get("paid_at") or (b.get("completed_at") if status == "paid" else None)

            try:
                cur.execute(
                    """
                    INSERT INTO bookings
                        (id, campaign_id, campaign_name, username, price, paypal,
                         status, booked_at, completed_at, paid_at, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        booking_id,
                        campaign_id,
                        campaign_name,
                        b.get("username", ""),
                        float(b.get("price") or 0),
                        b.get("paypal", ""),
                        status,
                        b.get("booked_at") or "NOW()",
                        b.get("completed_at"),
                        paid_at,
                        b.get("notes", ""),
                    ),
                )
                if cur.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"    [warn] Skipped booking {booking_id}: {e}")
                skipped += 1

    print(f"  Inserted: {inserted}  Skipped (already existed): {skipped}")
    if unmatched_campaigns:
        unique_unmatched = sorted(set(unmatched_campaigns))
        print(f"  [warn] {len(unique_unmatched)} campaign names had no match (campaign_id=NULL):")
        for name in unique_unmatched[:10]:
            print(f"    - '{name}'")
    return inserted


# ---------------------------------------------------------------------------
# Step 4: Inbox requests (from tracker_data.json)
# ---------------------------------------------------------------------------

def migrate_inbox_requests(dry_run: bool = True) -> int:
    data = _load_json(TRACKER_DATA_JSON)
    requests = data.get("requests", [])
    print(f"  Inbox requests to migrate: {len(requests)}")

    if dry_run:
        for r in requests[:5]:
            print(f"    id={r.get('id')} username={r.get('username')} status={r.get('status')}")
        return len(requests)

    inserted = 0
    with db.get_db() as conn:
        cur = db._cursor(conn)
        for r in requests:
            req_id = r.get("id")
            if not req_id:
                continue
            # Map 'pending' status; invited/submitted become 'approved'
            raw_status = r.get("status", "pending")
            db_status = "pending" if raw_status == "pending" else "approved"
            try:
                cur.execute(
                    """
                    INSERT INTO inbox_requests
                        (id, username, paypal, source, status, notes, received_at)
                    VALUES (%s, %s, %s, 'manychat', %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        req_id,
                        r.get("username", ""),
                        r.get("paypal", ""),
                        db_status,
                        r.get("notes", ""),
                        r.get("timestamp"),
                    ),
                )
                if cur.rowcount > 0:
                    inserted += 1
            except Exception as e:
                print(f"    [warn] Skipped request {req_id}: {e}")
    print(f"  Inserted: {inserted} inbox requests")
    return inserted


# ---------------------------------------------------------------------------
# Step 5: Payment data (from payment_data.json)
# ---------------------------------------------------------------------------

def migrate_payment_data(dry_run: bool = True) -> int:
    data = _load_json(PAYMENT_DATA_JSON)
    if not data:
        return 0

    queue   = data.get("payment_queue", [])
    history = data.get("payment_history", [])
    creators = data.get("creators", {})

    print(f"  Payment queue:   {len(queue)}")
    print(f"  Payment history: {len(history)}")
    print(f"  Creator records: {len(creators)}")

    if dry_run:
        return len(queue) + len(history) + len(creators)

    campaign_map = _build_campaign_map()
    inserted = 0

    with db.get_db() as conn:
        cur = db._cursor(conn)

        # Creators -> creator_paypal
        for email, info in creators.items():
            username = info.get("tiktok_username", "").lstrip("@").lower()
            paypal = info.get("paypal", "")
            if username and paypal:
                cur.execute(
                    """
                    INSERT INTO creator_paypal (username, paypal, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO UPDATE SET paypal = EXCLUDED.paypal, updated_at = NOW()
                    """,
                    (username, paypal, info.get("last_updated")),
                )

        # Payment queue -> inbox_requests
        for item in queue:
            req_id = item.get("id")
            if not req_id:
                continue
            username = item.get("tiktok_username", item.get("email", ""))
            try:
                cur.execute(
                    """
                    INSERT INTO inbox_requests
                        (id, username, paypal, rate, source, status, received_at)
                    VALUES (%s, %s, %s, %s, 'payment_server', 'pending', %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        req_id, username, item.get("paypal", ""),
                        float(item.get("amount") or 0), item.get("added_at"),
                    ),
                )
                inserted += 1
            except Exception as e:
                print(f"    [warn] Skipped queue item {req_id}: {e}")

        # Payment history -> bookings (status=paid)
        for item in history:
            item_id = item.get("id")
            if not item_id:
                continue
            campaign_name = item.get("campaign", "")
            campaign_id = _fuzzy_campaign_id(campaign_name, campaign_map)
            username = item.get("tiktok_username", item.get("email", ""))
            raw_status = item.get("status", "paid")
            status = "paid" if raw_status in ("paid", "complete") else "booked"
            try:
                cur.execute(
                    """
                    INSERT INTO bookings
                        (id, campaign_id, campaign_name, username, price, paypal, status, booked_at, paid_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                    """,
                    (
                        item_id, campaign_id, campaign_name, username,
                        float(item.get("amount") or 0), item.get("paypal", ""),
                        status, item.get("added_at"), item.get("paid_at"),
                    ),
                )
                if cur.rowcount > 0:
                    inserted += 1
            except Exception as e:
                print(f"    [warn] Skipped history item {item_id}: {e}")

    print(f"  Inserted: {inserted} records from payment_data.json")
    return inserted


# ---------------------------------------------------------------------------
# Step 6: SQLite tracker.db -> PostgreSQL analytics tables
# ---------------------------------------------------------------------------

def migrate_sqlite(dry_run: bool = True) -> dict[str, int]:
    if not SQLITE_DB.exists():
        print(f"  [skip] {SQLITE_DB} not found")
        return {}

    sqlite_conn = sqlite3.connect(str(SQLITE_DB))
    sqlite_conn.row_factory = sqlite3.Row
    counts: dict[str, int] = {}

    print(f"  Source: {SQLITE_DB}")

    try:
        # Count rows in each table
        for table in ("accounts", "sounds", "videos", "scrape_sessions", "scrape_logs", "video_history"):
            try:
                row = sqlite_conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()
                counts[table] = row["cnt"] if row else 0
                print(f"  {table}: {counts[table]} rows")
            except Exception:
                counts[table] = 0
                print(f"  {table}: (table not found)")

        if dry_run:
            return counts

        # --- Migrate in FK-safe order ---

        # 1. Sounds (no deps)
        _migrate_sqlite_sounds(sqlite_conn)

        # 2. Accounts (no deps)
        sqlite_to_pg_account_id = _migrate_sqlite_accounts(sqlite_conn)

        # 3. Videos (deps: accounts + sounds)
        _migrate_sqlite_videos(sqlite_conn, sqlite_to_pg_account_id)

        # 4. Scrape sessions (no deps)
        _migrate_sqlite_sessions(sqlite_conn)

        # 5. Scrape logs (deps: accounts + sessions)
        _migrate_sqlite_logs(sqlite_conn, sqlite_to_pg_account_id)

        # 6. Video history (no FK enforced — stored as TEXT video_id)
        _migrate_sqlite_video_history(sqlite_conn)

        # Reset sequences so future INSERTs don't collide
        _reset_sequences()

    finally:
        sqlite_conn.close()

    return counts


def _migrate_sqlite_sounds(sqlite_conn):
    rows = sqlite_conn.execute(
        "SELECT sound_key, song_title, artist_name, is_exclusive, "
        "total_usage_count, total_views, total_likes, total_comments, "
        "total_shares, avg_engagement_rate, notes FROM sounds"
    ).fetchall()
    if not rows:
        return
    with db.get_db() as conn:
        cur = db._cursor(conn)
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO sounds
                (sound_key, song_title, artist_name, is_exclusive,
                 total_usage_count, total_views, total_likes, total_comments,
                 total_shares, avg_engagement_rate, notes)
            VALUES %s
            ON CONFLICT (sound_key) DO NOTHING
            """,
            [
                (
                    r["sound_key"], r["song_title"] or "", r["artist_name"] or "",
                    bool(r["is_exclusive"]),
                    r["total_usage_count"] or 0, r["total_views"] or 0,
                    r["total_likes"] or 0, r["total_comments"] or 0,
                    r["total_shares"] or 0, r["avg_engagement_rate"] or 0,
                    r["notes"] or "",
                )
                for r in rows
            ],
        )
    print(f"    sounds: {len(rows)} rows migrated")


def _migrate_sqlite_accounts(sqlite_conn) -> dict[int, int]:
    """Returns mapping {sqlite_id: pg_id}."""
    rows = sqlite_conn.execute(
        "SELECT id, username, display_name, followers, following, total_videos, "
        "total_likes, bio, is_active, is_target_account, last_scraped_at, scrape_count, notes "
        "FROM accounts"
    ).fetchall()
    if not rows:
        return {}

    with db.get_db() as conn:
        cur = db._cursor(conn)
        for r in rows:
            cur.execute(
                """
                INSERT INTO accounts
                    (username, display_name, followers, following, total_videos,
                     total_likes, bio, is_active, is_target_account,
                     last_scraped_at, scrape_count, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
                """,
                (
                    r["username"], r["display_name"] or "",
                    r["followers"] or 0, r["following"] or 0,
                    r["total_videos"] or 0, r["total_likes"] or 0,
                    r["bio"] or "", bool(r["is_active"]), bool(r["is_target_account"]),
                    r["last_scraped_at"], r["scrape_count"] or 0, r["notes"] or "",
                ),
            )

        # Build sqlite_id -> pg_id map
        id_map: dict[int, int] = {}
        for r in rows:
            cur.execute("SELECT id FROM accounts WHERE username = %s", (r["username"],))
            row = cur.fetchone()
            if row:
                id_map[r["id"]] = row["id"]

    print(f"    accounts: {len(rows)} rows migrated")
    return id_map


def _migrate_sqlite_videos(sqlite_conn, account_id_map: dict[int, int]):
    rows = sqlite_conn.execute(
        "SELECT video_id, account_id, tiktok_url, upload_date, views, likes, "
        "comments, shares, engagement_rate, caption, hashtags, duration, is_deleted "
        "FROM videos"
    ).fetchall()
    if not rows:
        return

    # Build sound_key lookup: sqlite sound_id -> PG sound_id via sound_key
    sound_rows = sqlite_conn.execute("SELECT id, sound_key FROM sounds").fetchall()
    sqlite_sound_to_key = {r["id"]: r["sound_key"] for r in sound_rows}

    with db.get_db() as conn:
        cur = db._cursor(conn)
        # Pre-fetch PG sound IDs by sound_key
        cur.execute("SELECT id, sound_key FROM sounds")
        pg_sound_map = {r["sound_key"]: r["id"] for r in cur.fetchall()}

        batch = []
        for r in rows:
            pg_account_id = account_id_map.get(r["account_id"])
            if not pg_account_id:
                continue  # orphaned video — skip
            sound_key = sqlite_sound_to_key.get(r["sound_id"]) if r["sound_id"] else None
            pg_sound_id = pg_sound_map.get(sound_key) if sound_key else None

            batch.append((
                r["video_id"], pg_account_id,
                r["tiktok_url"] or "", r["upload_date"] or "",
                r["views"] or 0, r["likes"] or 0,
                r["comments"] or 0, r["shares"] or 0,
                r["engagement_rate"] or 0,
                r["caption"] or "", r["hashtags"] or "",
                pg_sound_id, r["duration"] or 0, bool(r["is_deleted"]),
            ))

        if batch:
            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO videos
                    (video_id, account_id, tiktok_url, upload_date, views, likes,
                     comments, shares, engagement_rate, caption, hashtags,
                     sound_id, duration, is_deleted)
                VALUES %s
                ON CONFLICT (video_id) DO NOTHING
                """,
                batch,
            )
    print(f"    videos: {len(batch)} rows migrated")


def _migrate_sqlite_sessions(sqlite_conn):
    rows = sqlite_conn.execute(
        "SELECT session_id, start_time, end_time, status, total_accounts, "
        "successful_scrapes, failed_scrapes, total_videos_scraped, "
        "total_new_videos, total_updated_videos, error_log, configuration "
        "FROM scrape_sessions"
    ).fetchall()
    if not rows:
        return
    with db.get_db() as conn:
        cur = db._cursor(conn)
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO scrape_sessions
                (session_id, start_time, end_time, status, total_accounts,
                 successful_scrapes, failed_scrapes, total_videos_scraped,
                 total_new_videos, total_updated_videos, error_log, configuration)
            VALUES %s
            ON CONFLICT (session_id) DO NOTHING
            """,
            [
                (
                    r["session_id"], r["start_time"], r["end_time"],
                    r["status"] or "completed",
                    r["total_accounts"] or 0, r["successful_scrapes"] or 0,
                    r["failed_scrapes"] or 0, r["total_videos_scraped"] or 0,
                    r["total_new_videos"] or 0, r["total_updated_videos"] or 0,
                    r["error_log"] or "",
                    psycopg2.extras.Json(
                        json.loads(r["configuration"]) if r["configuration"] else {}
                    ),
                )
                for r in rows
            ],
        )
    print(f"    scrape_sessions: {len(rows)} rows migrated")


def _migrate_sqlite_logs(sqlite_conn, account_id_map: dict[int, int]):
    rows = sqlite_conn.execute(
        "SELECT session_id, account_id, timestamp, status, videos_found, "
        "new_videos, updated_videos, error_message, execution_time_seconds "
        "FROM scrape_logs"
    ).fetchall()
    if not rows:
        return
    batch = []
    for r in rows:
        pg_account_id = account_id_map.get(r["account_id"])
        if not pg_account_id:
            continue
        batch.append((
            r["session_id"], pg_account_id, r["timestamp"],
            r["status"] or "", r["videos_found"] or 0,
            r["new_videos"] or 0, r["updated_videos"] or 0,
            r["error_message"] or "", r["execution_time_seconds"] or 0,
        ))
    if not batch:
        return
    with db.get_db() as conn:
        cur = db._cursor(conn)
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO scrape_logs
                (session_id, account_id, timestamp, status, videos_found,
                 new_videos, updated_videos, error_message, execution_time_seconds)
            VALUES %s
            """,
            batch,
        )
    print(f"    scrape_logs: {len(batch)} rows migrated")


def _migrate_sqlite_video_history(sqlite_conn):
    rows = sqlite_conn.execute(
        "SELECT video_id, session_id, views, likes, comments, shares, "
        "engagement_rate, scraped_at FROM video_history"
    ).fetchall()
    if not rows:
        return
    with db.get_db() as conn:
        cur = db._cursor(conn)
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO video_history
                (video_id, session_id, views, likes, comments, shares, engagement_rate, scraped_at)
            VALUES %s
            """,
            [
                (
                    str(r["video_id"]), r["session_id"],
                    r["views"] or 0, r["likes"] or 0,
                    r["comments"] or 0, r["shares"] or 0,
                    r["engagement_rate"] or 0, r["scraped_at"],
                )
                for r in rows
            ],
        )
    print(f"    video_history: {len(rows)} rows migrated")


def _reset_sequences():
    """After bulk inserts, reset PG SERIAL sequences to max(id) so future inserts work."""
    tables = ["accounts", "sounds", "videos", "scrape_sessions", "scrape_logs", "video_history"]
    with db.get_db() as conn:
        cur = db._cursor(conn)
        for table in tables:
            cur.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table}"
            )
    print("    Sequences reset.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_campaign_map() -> dict[str, int]:
    """Returns {lower(title): id} for all campaigns in Postgres."""
    with db.get_db() as conn:
        cur = db._cursor(conn)
        cur.execute("SELECT id, title FROM campaigns")
        return {r["title"].lower(): r["id"] for r in cur.fetchall()}


def _fuzzy_campaign_id(name: str, campaign_map: dict[str, int]) -> int | None:
    if not name:
        return None
    name_lower = name.lower()
    # Exact match first
    if name_lower in campaign_map:
        return campaign_map[name_lower]
    # Substring match
    for title, cid in campaign_map.items():
        if name_lower in title or title in name_lower:
            return cid
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

STEPS = {
    "campaigns": migrate_campaigns,
    "paypal":    migrate_paypal_registry,
    "bookings":  migrate_bookings,
    "inbox":     migrate_inbox_requests,
    "payments":  migrate_payment_data,
    "sqlite":    migrate_sqlite,
}


def main():
    parser = argparse.ArgumentParser(description="Migrate JSON + SQLite data to PostgreSQL")
    parser.add_argument("--execute", action="store_true",
                        help="Write to Postgres (default: dry run)")
    parser.add_argument("--only", choices=list(STEPS.keys()),
                        help="Run only a specific migration step")
    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        print("=" * 60)
        print("DRY RUN — No data will be written to Postgres")
        print("Run with --execute to apply")
        print("=" * 60)
    else:
        print("=" * 60)
        print("LIVE MODE — Writing to Postgres")
        print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', '(not set)')[:40]}...")
        confirm = input("Continue? [y/N]: ")
        if confirm.lower() != "y":
            print("Cancelled.")
            return
        # Ensure schema exists
        db.init_schema()

    steps_to_run = {args.only: STEPS[args.only]} if args.only else STEPS

    total = 0
    for name, fn in steps_to_run.items():
        print(f"\n{'='*40}")
        print(f"Step: {name}")
        print("=" * 40)
        result = fn(dry_run=dry_run)
        if isinstance(result, dict):
            total += sum(result.values())
        elif isinstance(result, int):
            total += result

    print(f"\n{'='*60}")
    if dry_run:
        print("Dry run complete. Review above, then run with --execute.")
    else:
        print(f"Migration complete. ~{total} rows processed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
