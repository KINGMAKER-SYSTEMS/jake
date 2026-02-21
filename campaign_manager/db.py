"""
campaign_manager/db.py
======================
PostgreSQL connection pool + schema + all helper functions.

Mirrors the pattern from services/database.py (raw SQL, context manager,
dict rows) but uses psycopg2 instead of sqlite3.

Key differences from sqlite3:
  - Placeholders: %s  (not ?)
  - Row factory:  RealDictCursor  (not sqlite3.Row)
  - Upserts:      INSERT ... ON CONFLICT DO ...
  - Auto IDs:     RETURNING id  (not cursor.lastrowid)
  - JSON fields:  psycopg2.extras.Json(dict)
"""

import os
import uuid
import json
from contextlib import contextmanager
from datetime import datetime

import psycopg2
import psycopg2.pool
import psycopg2.extras

# ---------------------------------------------------------------------------
# Connection pool
# ---------------------------------------------------------------------------

_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        dsn = os.environ.get("DATABASE_URL")
        if dsn:
            # Railway auto-injects DATABASE_URL; it already encodes SSL params
            # but we force sslmode=require as a safety net for non-Railway envs.
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dsn=dsn,
                sslmode="require",
            )
        else:
            # Local development fallback
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=5,
                host=os.environ.get("PGHOST", "localhost"),
                port=int(os.environ.get("PGPORT", "5432")),
                dbname=os.environ.get("PGDATABASE", "campaign_manager"),
                user=os.environ.get("PGUSER", "postgres"),
                password=os.environ.get("PGPASSWORD", ""),
            )
    return _pool


@contextmanager
def get_db():
    """Yield a psycopg2 connection. Commits on clean exit, rolls back on error."""
    pool = _get_pool()
    conn = pool.getconn()
    conn.autocommit = False
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def _cursor(conn):
    """Return a RealDictCursor (rows come back as dicts)."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_SCHEMA_DDL = """
-- ============================================================
-- Group 1: Campaigns
-- ============================================================
CREATE TABLE IF NOT EXISTS campaigns (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    artist          TEXT NOT NULL DEFAULT '',
    song            TEXT DEFAULT '',
    tiktok_sound_id TEXT,
    cobrand_link    TEXT DEFAULT '',
    round           TEXT DEFAULT '',
    label           TEXT DEFAULT '',
    pipeline_status TEXT DEFAULT 'active',
    budget          NUMERIC(10,2) NOT NULL DEFAULT 0,
    start_date      DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_campaigns_sound_id
    ON campaigns(tiktok_sound_id) WHERE tiktok_sound_id IS NOT NULL AND tiktok_sound_id != '';
CREATE INDEX IF NOT EXISTS idx_campaigns_pipeline_status ON campaigns(pipeline_status);

-- ============================================================
-- Group 2: Bookings
-- TEXT primary key preserves "username_timestamp" format from existing JSON.
-- ============================================================
CREATE TABLE IF NOT EXISTS bookings (
    id            TEXT PRIMARY KEY,
    campaign_id   INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    campaign_name TEXT NOT NULL,
    username      TEXT NOT NULL,
    price         NUMERIC(10,2) NOT NULL DEFAULT 0,
    paypal        TEXT DEFAULT '',
    status        TEXT NOT NULL DEFAULT 'booked'
                  CHECK (status IN ('booked', 'payment_needed', 'paid')),
    booked_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at  TIMESTAMPTZ,
    paid_at       TIMESTAMPTZ,
    notes         TEXT DEFAULT '',
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_bookings_campaign_id ON bookings(campaign_id);
CREATE INDEX IF NOT EXISTS idx_bookings_username    ON bookings(username);
CREATE INDEX IF NOT EXISTS idx_bookings_status      ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_booked_at   ON bookings(booked_at DESC);

-- ============================================================
-- Group 3: Creator PayPal registry
-- ============================================================
CREATE TABLE IF NOT EXISTS creator_paypal (
    username   TEXT PRIMARY KEY,
    paypal     TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Group 4: Inbox requests (Slack webhook items)
-- ============================================================
CREATE TABLE IF NOT EXISTS inbox_requests (
    id          TEXT PRIMARY KEY,
    username    TEXT NOT NULL,
    paypal      TEXT DEFAULT '',
    rate        NUMERIC(10,2),
    posts       INTEGER DEFAULT 0,
    source      TEXT DEFAULT 'slack',
    raw_payload JSONB,
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'approved', 'dismissed')),
    campaign_id INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    notes       TEXT DEFAULT '',
    received_at TIMESTAMPTZ DEFAULT NOW(),
    actioned_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_inbox_status      ON inbox_requests(status);
CREATE INDEX IF NOT EXISTS idx_inbox_received_at ON inbox_requests(received_at DESC);

-- ============================================================
-- Group 5: Pending bookings (ManyChat two-step flow)
-- ============================================================
CREATE TABLE IF NOT EXISTS pending_bookings (
    pending_key TEXT PRIMARY KEY,
    username    TEXT NOT NULL,
    price       NUMERIC(10,2),
    paypal      TEXT DEFAULT '',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- Group 6: TikTok analytics (ported from SQLite tracker.db)
-- BIGINT for views/counts — PG INTEGER overflows at ~2.1B
-- ============================================================
CREATE TABLE IF NOT EXISTS accounts (
    id                SERIAL PRIMARY KEY,
    username          TEXT NOT NULL UNIQUE,
    display_name      TEXT DEFAULT '',
    followers         BIGINT DEFAULT 0,
    following         INTEGER DEFAULT 0,
    total_videos      INTEGER DEFAULT 0,
    total_likes       BIGINT DEFAULT 0,
    bio               TEXT DEFAULT '',
    is_active         BOOLEAN DEFAULT TRUE,
    is_target_account BOOLEAN DEFAULT FALSE,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    last_scraped_at   TIMESTAMPTZ,
    scrape_count      INTEGER DEFAULT 0,
    notes             TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sounds (
    id                  SERIAL PRIMARY KEY,
    sound_key           TEXT NOT NULL UNIQUE,
    song_title          TEXT NOT NULL DEFAULT '',
    artist_name         TEXT DEFAULT '',
    is_exclusive        BOOLEAN DEFAULT FALSE,
    total_usage_count   INTEGER DEFAULT 0,
    total_views         BIGINT DEFAULT 0,
    total_likes         BIGINT DEFAULT 0,
    total_comments      BIGINT DEFAULT 0,
    total_shares        BIGINT DEFAULT 0,
    avg_engagement_rate NUMERIC(8,4) DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    notes               TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS videos (
    id              SERIAL PRIMARY KEY,
    video_id        TEXT NOT NULL UNIQUE,
    account_id      INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    tiktok_url      TEXT DEFAULT '',
    upload_date     TEXT DEFAULT '',
    views           BIGINT DEFAULT 0,
    likes           BIGINT DEFAULT 0,
    comments        INTEGER DEFAULT 0,
    shares          INTEGER DEFAULT 0,
    engagement_rate NUMERIC(8,4) DEFAULT 0,
    caption         TEXT DEFAULT '',
    hashtags        TEXT DEFAULT '',
    sound_id        INTEGER REFERENCES sounds(id) ON DELETE SET NULL,
    duration        INTEGER DEFAULT 0,
    is_deleted      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_videos_video_id    ON videos(video_id);
CREATE INDEX IF NOT EXISTS idx_videos_account_id  ON videos(account_id);
CREATE INDEX IF NOT EXISTS idx_videos_sound_id    ON videos(sound_id);
CREATE INDEX IF NOT EXISTS idx_videos_upload_date ON videos(upload_date DESC);
CREATE INDEX IF NOT EXISTS idx_videos_views       ON videos(views DESC);

CREATE TABLE IF NOT EXISTS scrape_sessions (
    id                   SERIAL PRIMARY KEY,
    session_id           TEXT NOT NULL UNIQUE,
    start_time           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time             TIMESTAMPTZ,
    status               TEXT DEFAULT 'running',
    total_accounts       INTEGER DEFAULT 0,
    successful_scrapes   INTEGER DEFAULT 0,
    failed_scrapes       INTEGER DEFAULT 0,
    total_videos_scraped INTEGER DEFAULT 0,
    total_new_videos     INTEGER DEFAULT 0,
    total_updated_videos INTEGER DEFAULT 0,
    error_log            TEXT DEFAULT '',
    configuration        JSONB,
    created_at           TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sessions_session_id ON scrape_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON scrape_sessions(start_time DESC);

CREATE TABLE IF NOT EXISTS scrape_logs (
    id                     SERIAL PRIMARY KEY,
    session_id             TEXT NOT NULL,
    account_id             INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    timestamp              TIMESTAMPTZ DEFAULT NOW(),
    status                 TEXT NOT NULL DEFAULT '',
    videos_found           INTEGER DEFAULT 0,
    new_videos             INTEGER DEFAULT 0,
    updated_videos         INTEGER DEFAULT 0,
    error_message          TEXT DEFAULT '',
    execution_time_seconds NUMERIC(8,3) DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_logs_session_id ON scrape_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_logs_account_id ON scrape_logs(account_id);

CREATE TABLE IF NOT EXISTS video_history (
    id              SERIAL PRIMARY KEY,
    video_id        TEXT NOT NULL,
    session_id      TEXT NOT NULL,
    views           BIGINT DEFAULT 0,
    likes           BIGINT DEFAULT 0,
    comments        INTEGER DEFAULT 0,
    shares          INTEGER DEFAULT 0,
    engagement_rate NUMERIC(8,4) DEFAULT 0,
    scraped_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_history_video_id   ON video_history(video_id);
CREATE INDEX IF NOT EXISTS idx_history_session_id ON video_history(session_id);
CREATE INDEX IF NOT EXISTS idx_history_scraped_at ON video_history(scraped_at DESC);
"""


def init_schema():
    """Create all tables and indexes. Idempotent (IF NOT EXISTS everywhere)."""
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(_SCHEMA_DDL)


# ---------------------------------------------------------------------------
# Allowlists for user-supplied sort columns (prevent SQL injection)
# ---------------------------------------------------------------------------

_VALID_CAMPAIGN_SORT = {
    "title", "artist", "budget", "created_at", "pipeline_status",
    "paid_amount", "booked_amount", "total_views", "live_posts",
}
_VALID_BOOKING_SORT = {
    "booked_at", "completed_at", "paid_at", "username",
    "campaign_name", "price", "status",
}
_VALID_INBOX_SORT = {"received_at", "username", "rate", "posts"}


def _safe_sort(col: str, valid: set, default: str) -> str:
    return col if col in valid else default


# ---------------------------------------------------------------------------
# Campaign helpers
# ---------------------------------------------------------------------------

def get_campaigns(
    sort_by: str = "created_at",
    sort_dir: str = "DESC",
    status: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """
    Returns campaigns with computed budget stats and view totals.
    Supports server-side sort/filter for TanStack Tables.
    """
    col = _safe_sort(sort_by, _VALID_CAMPAIGN_SORT, "created_at")
    direction = "DESC" if sort_dir.upper() == "DESC" else "ASC"

    where = "WHERE c.pipeline_status = %s" if status else ""
    params: list = []
    if status:
        params.append(status)

    sql = f"""
        SELECT
            c.*,
            COUNT(b.id) FILTER (WHERE b.status IN ('payment_needed','paid'))   AS live_posts,
            COALESCE(SUM(b.price) FILTER (WHERE b.status = 'paid'), 0)         AS paid_amount,
            COALESCE(SUM(b.price) FILTER (WHERE b.status != 'booked'), 0)      AS booked_amount,
            COALESCE(
                (SELECT SUM(v.views)
                 FROM videos v
                 JOIN sounds s ON v.sound_id = s.id
                 WHERE s.sound_key = c.tiktok_sound_id),
                0
            )                                                                   AS total_views
        FROM campaigns c
        LEFT JOIN bookings b ON b.campaign_id = c.id
        {where}
        GROUP BY c.id
        ORDER BY {col} {direction}
        LIMIT %s OFFSET %s
    """
    params += [limit, offset]

    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(sql, params)
        rows = cur.fetchall()

    result = []
    for row in rows:
        r = dict(row)
        budget = float(r.get("budget") or 0)
        paid = float(r.get("paid_amount") or 0)
        booked = float(r.get("booked_amount") or 0)
        views = int(r.get("total_views") or 0)
        r["budget"] = budget
        r["paid_amount"] = paid
        r["booked_amount"] = booked
        r["remaining"] = budget - booked
        r["total_views"] = views
        r["cpm"] = round((paid / views * 1000), 2) if views > 0 and paid > 0 else None
        result.append(r)
    return result


def get_campaign_by_id(campaign_id: int) -> dict | None:
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute("SELECT * FROM campaigns WHERE id = %s", (campaign_id,))
        row = cur.fetchone()
    return dict(row) if row else None


def create_campaign(
    title: str,
    artist: str = "",
    song: str = "",
    tiktok_sound_id: str | None = None,
    budget: float = 0.0,
    start_date: str | None = None,
    cobrand_link: str = "",
    round_: str = "",
    label: str = "",
) -> int:
    """Insert a new campaign, return its id."""
    sql = """
        INSERT INTO campaigns
            (title, artist, song, tiktok_sound_id, budget, start_date,
             cobrand_link, round, label)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(sql, (
            title, artist, song,
            tiktok_sound_id or None,
            budget, start_date or None,
            cobrand_link, round_, label,
        ))
        return cur.fetchone()["id"]


def update_campaign_status(campaign_id: int, pipeline_status: str):
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(
            "UPDATE campaigns SET pipeline_status=%s, updated_at=NOW() WHERE id=%s",
            (pipeline_status, campaign_id),
        )


# ---------------------------------------------------------------------------
# Booking helpers
# ---------------------------------------------------------------------------

def add_booking(
    username: str,
    campaign_id: int | None,
    campaign_name: str,
    price: float,
    paypal: str,
) -> str:
    booking_id = f"{username.lower().lstrip('@')}_{datetime.now().timestamp()}"
    sql = """
        INSERT INTO bookings
            (id, campaign_id, campaign_name, username, price, paypal, status, booked_at)
        VALUES (%s, %s, %s, %s, %s, %s, 'booked', NOW())
    """
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(sql, (booking_id, campaign_id, campaign_name, username, price, paypal))
        # Upsert PayPal registry
        _upsert_paypal(cur, username, paypal)
    return booking_id


def get_bookings(
    status_filter: str | None = None,
    campaign_id: int | None = None,
    sort_by: str = "booked_at",
    sort_dir: str = "DESC",
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    col = _safe_sort(sort_by, _VALID_BOOKING_SORT, "booked_at")
    direction = "DESC" if sort_dir.upper() == "DESC" else "ASC"

    conditions = []
    params: list = []
    if status_filter and status_filter != "all":
        conditions.append("status = %s")
        params.append(status_filter)
    if campaign_id:
        conditions.append("campaign_id = %s")
        params.append(campaign_id)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    sql = f"""
        SELECT * FROM bookings
        {where}
        ORDER BY {col} {direction}
        LIMIT %s OFFSET %s
    """
    params += [limit, offset]

    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def find_booking(username: str, campaign: str | None = None) -> dict | None:
    """Find the most recent active 'booked' booking for a creator."""
    username_lower = username.lower().lstrip("@")
    params: list = [username_lower, f"%{username_lower}%"]
    sql = """
        SELECT * FROM bookings
        WHERE LOWER(REPLACE(username, '@', '')) = %s
           OR LOWER(REPLACE(username, '@', '')) LIKE %s
        AND status = 'booked'
        ORDER BY booked_at DESC
        LIMIT 1
    """
    if campaign:
        sql = """
            SELECT * FROM bookings
            WHERE (LOWER(REPLACE(username, '@', '')) = %s
                OR LOWER(REPLACE(username, '@', '')) LIKE %s)
            AND status = 'booked'
            AND (LOWER(campaign_name) LIKE %s OR %s LIKE CONCAT('%%', LOWER(campaign_name), '%%'))
            ORDER BY booked_at DESC
            LIMIT 1
        """
        params += [f"%{campaign.lower()}%", campaign.lower()]

    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(sql, params)
        row = cur.fetchone()
    return dict(row) if row else None


def update_booking(
    booking_id: str,
    status: str | None = None,
    notes: str | None = None,
    paypal: str | None = None,
):
    parts = ["updated_at = NOW()"]
    params: list = []

    if status:
        parts.append("status = %s")
        params.append(status)
        if status == "payment_needed":
            parts.append("completed_at = NOW()")
        elif status == "paid":
            parts.append("paid_at = NOW()")
    if notes is not None:
        parts.append("notes = %s")
        params.append(notes)
    if paypal:
        parts.append("paypal = %s")
        params.append(paypal)

    params.append(booking_id)
    sql = f"UPDATE bookings SET {', '.join(parts)} WHERE id = %s"

    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(sql, params)
        if paypal:
            # Also update the registry — need username
            cur.execute("SELECT username FROM bookings WHERE id = %s", (booking_id,))
            row = cur.fetchone()
            if row:
                _upsert_paypal(cur, row["username"], paypal)


def delete_booking(booking_id: str):
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))


def get_paypal(username: str) -> str:
    key = username.lower().lstrip("@")
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute("SELECT paypal FROM creator_paypal WHERE username = %s", (key,))
        row = cur.fetchone()
    return row["paypal"] if row else ""


def _upsert_paypal(cur, username: str, paypal: str):
    key = username.lower().lstrip("@")
    cur.execute(
        """
        INSERT INTO creator_paypal (username, paypal, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (username) DO UPDATE SET paypal = EXCLUDED.paypal, updated_at = NOW()
        """,
        (key, paypal),
    )


# ---------------------------------------------------------------------------
# Inbox helpers
# ---------------------------------------------------------------------------

def get_inbox(
    status: str = "pending",
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    col = "received_at"
    params: list = []
    where = ""
    if status and status != "all":
        where = "WHERE i.status = %s"
        params.append(status)

    sql = f"""
        SELECT i.*, c.title AS campaign_title
        FROM inbox_requests i
        LEFT JOIN campaigns c ON c.id = i.campaign_id
        {where}
        ORDER BY {col} DESC
        LIMIT %s OFFSET %s
    """
    params += [limit, offset]

    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def add_inbox_request(
    username: str,
    paypal: str = "",
    rate: float | None = None,
    posts: int = 0,
    source: str = "slack",
    raw_payload: dict | None = None,
) -> str:
    req_id = f"{username.lower().lstrip('@')}_{datetime.now().timestamp()}"
    sql = """
        INSERT INTO inbox_requests
            (id, username, paypal, rate, posts, source, raw_payload)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(sql, (
            req_id, username, paypal or "", rate, posts, source,
            psycopg2.extras.Json(raw_payload) if raw_payload else None,
        ))
    return req_id


def approve_inbox(request_id: str, campaign_id: int) -> str:
    """Create a booking from an inbox request, mark it approved. Returns booking_id."""
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute("SELECT * FROM inbox_requests WHERE id = %s", (request_id,))
        req = cur.fetchone()
        if not req:
            raise ValueError(f"Inbox request {request_id} not found")

        cur.execute("SELECT title FROM campaigns WHERE id = %s", (campaign_id,))
        camp = cur.fetchone()
        campaign_name = camp["title"] if camp else ""

        booking_id = f"{req['username'].lower().lstrip('@')}_{datetime.now().timestamp()}"
        cur.execute(
            """
            INSERT INTO bookings
                (id, campaign_id, campaign_name, username, price, paypal, status, booked_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'booked', NOW())
            """,
            (
                booking_id,
                campaign_id,
                campaign_name,
                req["username"],
                req["rate"] or 0,
                req["paypal"] or "",
            ),
        )
        cur.execute(
            "UPDATE inbox_requests SET status='approved', campaign_id=%s, actioned_at=NOW() WHERE id=%s",
            (campaign_id, request_id),
        )
        if req.get("paypal"):
            _upsert_paypal(cur, req["username"], req["paypal"])
    return booking_id


def dismiss_inbox(request_id: str):
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(
            "UPDATE inbox_requests SET status='dismissed', actioned_at=NOW() WHERE id=%s",
            (request_id,),
        )


# ---------------------------------------------------------------------------
# Pending bookings (ManyChat two-step flow)
# ---------------------------------------------------------------------------

def set_pending_booking(username: str, price: float, paypal: str):
    key = f"pending_{username.lower().lstrip('@')}"
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(
            """
            INSERT INTO pending_bookings (pending_key, username, price, paypal, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (pending_key) DO UPDATE
                SET price = EXCLUDED.price,
                    paypal = EXCLUDED.paypal,
                    created_at = NOW()
            """,
            (key, username, price, paypal),
        )


def get_pending_booking(username: str) -> dict | None:
    key = f"pending_{username.lower().lstrip('@')}"
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute("SELECT * FROM pending_bookings WHERE pending_key = %s", (key,))
        row = cur.fetchone()
    return dict(row) if row else None


def clear_pending_booking(username: str):
    key = f"pending_{username.lower().lstrip('@')}"
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute("DELETE FROM pending_bookings WHERE pending_key = %s", (key,))


# ---------------------------------------------------------------------------
# TikTok analytics helpers (ported from services/database.py)
# Same function signatures — just uses get_db() and %s placeholders
# ---------------------------------------------------------------------------

def ensure_account_exists(username: str) -> int:
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(
            """
            INSERT INTO accounts (username, created_at, updated_at)
            VALUES (%s, NOW(), NOW())
            ON CONFLICT (username) DO UPDATE SET updated_at = NOW()
            RETURNING id
            """,
            (username,),
        )
        return cur.fetchone()["id"]


def ensure_sound_exists(
    song_title: str,
    artist_name: str = "",
    conn=None,
) -> int | None:
    if not song_title:
        return None
    sound_key = f"{artist_name}_{song_title}".lower().replace(" ", "_")

    def _run(c):
        cur = _cursor(c)
        cur.execute(
            """
            INSERT INTO sounds (sound_key, song_title, artist_name, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON CONFLICT (sound_key) DO UPDATE SET updated_at = NOW()
            RETURNING id
            """,
            (sound_key, song_title, artist_name or ""),
        )
        return cur.fetchone()["id"]

    if conn:
        return _run(conn)
    with get_db() as c:
        return _run(c)


def insert_or_update_video(
    video_data: dict,
    account_id: int,
    session_id: str,
) -> tuple[bool, bool]:
    """Returns (is_new, is_updated)."""
    video_id = str(video_data.get("video_id", ""))
    if not video_id:
        return False, False

    sql_check = "SELECT id, views FROM videos WHERE video_id = %s"
    sql_insert = """
        INSERT INTO videos
            (video_id, account_id, tiktok_url, upload_date, views, likes, comments,
             shares, engagement_rate, caption, hashtags, duration, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        ON CONFLICT (video_id) DO UPDATE SET
            views           = EXCLUDED.views,
            likes           = EXCLUDED.likes,
            comments        = EXCLUDED.comments,
            shares          = EXCLUDED.shares,
            engagement_rate = EXCLUDED.engagement_rate,
            updated_at      = NOW()
        RETURNING (xmax = 0) AS is_new
    """
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(sql_check, (video_id,))
        existing = cur.fetchone()
        old_views = existing["views"] if existing else None

        cur.execute(
            sql_insert,
            (
                video_id, account_id,
                video_data.get("tiktok_url", ""),
                video_data.get("upload_date", ""),
                int(video_data.get("views", 0)),
                int(video_data.get("likes", 0)),
                int(video_data.get("comments", 0)),
                int(video_data.get("shares", 0)),
                float(video_data.get("engagement_rate", 0)),
                video_data.get("caption", ""),
                video_data.get("hashtags", ""),
                int(video_data.get("duration", 0)),
            ),
        )
        row = cur.fetchone()
        is_new = bool(row["is_new"]) if row else (existing is None)
        is_updated = (not is_new) and (old_views != int(video_data.get("views", 0)))
    return is_new, is_updated


def create_scrape_session(
    session_id: str,
    settings: dict,
    total_accounts: int,
) -> bool:
    try:
        with get_db() as conn:
            cur = _cursor(conn)
            cur.execute(
                """
                INSERT INTO scrape_sessions
                    (session_id, start_time, status, total_accounts, configuration)
                VALUES (%s, NOW(), 'running', %s, %s)
                ON CONFLICT (session_id) DO NOTHING
                """,
                (session_id, total_accounts, psycopg2.extras.Json(settings)),
            )
        return True
    except Exception:
        return False


def update_scrape_session(
    session_id: str,
    status: str,
    successful_scrapes: int = 0,
    failed_scrapes: int = 0,
    total_videos_scraped: int = 0,
    total_new_videos: int = 0,
    total_updated_videos: int = 0,
    error_log: str = "",
):
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(
            """
            UPDATE scrape_sessions SET
                status               = %s,
                end_time             = CASE WHEN %s IN ('completed','failed') THEN NOW() ELSE end_time END,
                successful_scrapes   = %s,
                failed_scrapes       = %s,
                total_videos_scraped = %s,
                total_new_videos     = %s,
                total_updated_videos = %s,
                error_log            = %s
            WHERE session_id = %s
            """,
            (
                status, status,
                successful_scrapes, failed_scrapes,
                total_videos_scraped, total_new_videos, total_updated_videos,
                error_log, session_id,
            ),
        )


def get_all_sessions(limit: int = 50) -> list[dict]:
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(
            "SELECT * FROM scrape_sessions ORDER BY start_time DESC LIMIT %s",
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]


def get_session(session_id: str) -> dict | None:
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(
            "SELECT * FROM scrape_sessions WHERE session_id = %s",
            (session_id,),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def get_accounts() -> list[dict]:
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute(
            "SELECT * FROM accounts WHERE is_active = TRUE ORDER BY username ASC"
        )
        return [dict(r) for r in cur.fetchall()]


def get_internal_stats() -> dict:
    """Returns stat card data for the /internal page."""
    with get_db() as conn:
        cur = _cursor(conn)
        cur.execute("SELECT COUNT(*) AS cnt FROM accounts WHERE is_active = TRUE")
        account_count = cur.fetchone()["cnt"]

        cur.execute(
            "SELECT MAX(end_time) AS last FROM scrape_sessions WHERE status = 'completed'"
        )
        row = cur.fetchone()
        last_scrape = row["last"].isoformat() if row and row["last"] else None

        cur.execute("SELECT COUNT(*) AS cnt FROM videos WHERE is_deleted = FALSE")
        video_count = cur.fetchone()["cnt"]

        cur.execute("SELECT COUNT(DISTINCT sound_id) AS cnt FROM videos WHERE sound_id IS NOT NULL")
        unique_sounds = cur.fetchone()["cnt"]

    return {
        "account_count": account_count,
        "last_scrape_at": last_scrape,
        "video_count": video_count,
        "unique_sounds": unique_sounds,
    }
