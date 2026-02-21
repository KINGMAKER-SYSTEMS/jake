"""
campaign_manager/web_dashboard.py
==================================
Flask app for the Warner Campaign Manager.

Routes:
  GET  /                              - Promotions table
  POST /campaigns                     - Create campaign
  GET  /internal                      - Internal TikTok scraper
  POST /internal/scrape               - Trigger scrape
  GET  /internal/scrape/status        - Poll scrape progress
  GET  /inbox                         - Slack creator inbox
  POST /api/inbox/<id>/approve        - Approve inbox item -> booking
  POST /api/inbox/<id>/dismiss        - Dismiss inbox item
  POST /webhook/slack                 - Slack webhook (creates inbox item)
  POST /webhook/booked                - ManyChat: book a creator
  POST /webhook/booked/campaign       - ManyChat: set campaign (step 2)
  POST /webhook/done                  - ManyChat: creator marks posts done
  POST /webhook/confirm               - ManyChat: creator confirms PayPal
  GET  /api/bookings                  - Bookings list (sort/filter/paginate)
  POST /api/bookings/update           - Update booking
  POST /api/bookings/delete           - Delete booking
  POST /api/migrate/campaign          - Bulk import from migration script
  GET  /health                        - Health check
"""

import os
import re
import threading
import uuid
from datetime import datetime

from flask import Flask, jsonify, redirect, render_template_string, request, url_for

import campaign_manager.db as db

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "campaign-dashboard-local-dev")


def ensure_dirs():
    """No-op for Postgres build — kept for compatibility with older deploy configs."""
    pass


# Initialise schema on startup (idempotent)
with app.app_context():
    try:
        db.init_schema()
    except Exception as e:
        print(f"[startup] Schema init failed (DB may not be ready yet): {e}")


# ---------------------------------------------------------------------------
# HTML Templates
# ---------------------------------------------------------------------------

_BASE_NAV = """
<style>
  * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; }
  body { background: #0f0f0f; color: #e8e8e8; display: flex; min-height: 100vh; }
  .sidebar { width: 200px; min-height: 100vh; background: #1a1a1a; border-right: 1px solid #2a2a2a; padding: 24px 0; flex-shrink: 0; }
  .sidebar .logo { padding: 0 20px 24px; font-size: 14px; font-weight: 700; color: #fff; letter-spacing: 0.5px; border-bottom: 1px solid #2a2a2a; margin-bottom: 12px; }
  .sidebar a { display: block; padding: 10px 20px; color: #999; text-decoration: none; font-size: 13px; border-left: 3px solid transparent; }
  .sidebar a:hover { color: #fff; background: #222; }
  .sidebar a.active { color: #fff; border-left-color: #4f8ef7; background: #222; }
  .main { flex: 1; padding: 32px; max-width: 1400px; }
  h1 { font-size: 22px; font-weight: 600; margin-bottom: 4px; color: #fff; }
  .subtitle { color: #666; font-size: 13px; margin-bottom: 24px; }

  .card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px; padding: 20px; }
  .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }
  .stat { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 8px; padding: 16px; }
  .stat-value { font-size: 26px; font-weight: 700; color: #fff; }
  .stat-label { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }

  .table-wrap { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 10px; overflow: hidden; }
  table { width: 100%; border-collapse: collapse; }
  th { background: #141414; padding: 10px 14px; text-align: left; font-size: 11px; text-transform: uppercase; color: #555; letter-spacing: 0.5px; border-bottom: 1px solid #2a2a2a; white-space: nowrap; }
  td { padding: 11px 14px; border-bottom: 1px solid #1f1f1f; font-size: 13px; color: #ccc; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #1f1f1f; }

  .badge { display: inline-block; padding: 3px 9px; border-radius: 20px; font-size: 11px; font-weight: 500; }
  .badge-active   { background: #1a3a1a; color: #4caf50; }
  .badge-paused   { background: #3a3a1a; color: #ffc107; }
  .badge-completed{ background: #1a1a3a; color: #4f8ef7; }
  .badge-booked   { background: #3a2a00; color: #ffa726; }
  .badge-payment-needed { background: #3a1a1a; color: #ef5350; }
  .badge-paid     { background: #1a3a1a; color: #4caf50; }
  .badge-pending  { background: #3a2a00; color: #ffa726; }

  .btn { padding: 6px 14px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 500; }
  .btn-primary  { background: #4f8ef7; color: #fff; }
  .btn-primary:hover { background: #3d7de8; }
  .btn-success  { background: #2e7d32; color: #fff; }
  .btn-success:hover { background: #1b5e20; }
  .btn-danger   { background: #3a1a1a; color: #ef5350; border: 1px solid #4a2a2a; }
  .btn-danger:hover { background: #4a1a1a; }
  .btn-sm { padding: 4px 10px; font-size: 11px; }

  input[type=text], input[type=number], input[type=date], input[type=email], select, textarea {
    background: #111; border: 1px solid #333; border-radius: 6px; color: #e8e8e8;
    padding: 7px 10px; font-size: 13px; outline: none; width: 100%;
  }
  input:focus, select:focus, textarea:focus { border-color: #4f8ef7; }

  .form-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }
  .form-group { display: flex; flex-direction: column; gap: 5px; }
  .form-group label { font-size: 11px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
  .form-group.flex1 { flex: 1; min-width: 160px; }
  .form-group.w120 { width: 120px; }
  .form-group.w80  { width: 80px; }

  .search-bar { display: flex; gap: 10px; margin-bottom: 16px; align-items: center; }
  .search-bar input { max-width: 300px; }
  .search-count { font-size: 12px; color: #555; }

  .empty { padding: 40px; text-align: center; color: #555; font-size: 13px; }
  .budget-bar { display: flex; height: 5px; border-radius: 3px; overflow: hidden; background: #2a2a2a; margin-top: 4px; min-width: 80px; }
  .budget-bar .paid-fill { background: #4caf50; }
  .budget-bar .booked-fill { background: #ffa726; }
</style>
"""

PROMOTIONS_HTML = (
    _BASE_NAV
    + """
<body>
  <div class="sidebar">
    <div class="logo">Warner CM</div>
    <a href="/" class="active">Promotions</a>
    <a href="/internal">Internal TikTok</a>
    <a href="/inbox">Slack Inbox</a>
  </div>
  <div class="main">
    <h1>Promotions</h1>
    <p class="subtitle">Active campaign performance overview</p>

    <!-- Create campaign form -->
    <div class="card" style="margin-bottom:24px;">
      <form method="POST" action="/campaigns">
        <div class="form-row">
          <div class="form-group flex1">
            <label>Title</label>
            <input type="text" name="title" placeholder="Artist - Song Promo" required>
          </div>
          <div class="form-group flex1">
            <label>Artist</label>
            <input type="text" name="artist" placeholder="Artist name">
          </div>
          <div class="form-group flex1">
            <label>Song</label>
            <input type="text" name="song" placeholder="Song title">
          </div>
          <div class="form-group flex1">
            <label>Sound ID or URL</label>
            <input type="text" name="sound_id" placeholder="TikTok sound ID">
          </div>
          <div class="form-group w120">
            <label>Start Date</label>
            <input type="date" name="start_date">
          </div>
          <div class="form-group w80">
            <label>Budget ($)</label>
            <input type="number" name="budget" placeholder="0" min="0" step="0.01">
          </div>
          <div class="form-group" style="justify-content:flex-end;">
            <button type="submit" class="btn btn-primary">+ New Campaign</button>
          </div>
        </div>
      </form>
    </div>

    <!-- Search bar -->
    <div class="search-bar">
      <input type="text" id="search" placeholder="Search {{ campaigns|length }} campaigns..." oninput="filterTable(this.value)">
      <span class="search-count" id="count">{{ campaigns|length }} campaigns</span>
    </div>

    <!-- Campaigns table -->
    <div class="table-wrap">
      {% if campaigns %}
      <table id="campaigns-table">
        <thead>
          <tr>
            <th>Promotion</th>
            <th>Artist</th>
            <th>Status</th>
            <th>Budget</th>
            <th>Total Views</th>
            <th>Live Posts</th>
            <th>CPM</th>
          </tr>
        </thead>
        <tbody>
          {% for c in campaigns %}
          <tr>
            <td style="font-weight:500;color:#fff;">{{ c.title }}</td>
            <td>{{ c.artist }}</td>
            <td>
              <span class="badge badge-{{ c.pipeline_status }}">{{ c.pipeline_status|title }}</span>
            </td>
            <td>
              <div style="font-size:12px;">
                <div style="display:flex;gap:8px;margin-bottom:4px;">
                  <span style="color:#4caf50;">${{ '%.0f'|format(c.paid_amount) }} paid</span>
                  <span style="color:#666;">·</span>
                  <span style="color:#ffa726;">${{ '%.0f'|format(c.booked_amount - c.paid_amount) }} booked</span>
                  <span style="color:#666;">·</span>
                  <span style="color:#555;">${{ '%.0f'|format(c.remaining) }} left</span>
                </div>
                <div class="budget-bar">
                  {% if c.budget > 0 %}
                  <div class="paid-fill" style="width:{{ [[(c.paid_amount / c.budget * 100)|int, 0]|max, 100]|min }}%;"></div>
                  <div class="booked-fill" style="width:{{ [[((c.booked_amount - c.paid_amount) / c.budget * 100)|int, 0]|max, 100]|min }}%;"></div>
                  {% endif %}
                </div>
              </div>
            </td>
            <td>{{ '{:,}'.format(c.total_views|int) }}</td>
            <td>{{ c.live_posts }}</td>
            <td>{% if c.cpm %}${{ '%.2f'|format(c.cpm) }}{% else %}-{% endif %}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
      <div class="empty">No campaigns yet. Create one above.</div>
      {% endif %}
    </div>
  </div>

  <script>
    function filterTable(q) {
      const rows = document.querySelectorAll('#campaigns-table tbody tr');
      let visible = 0;
      rows.forEach(r => {
        const match = r.textContent.toLowerCase().includes(q.toLowerCase());
        r.style.display = match ? '' : 'none';
        if (match) visible++;
      });
      document.getElementById('count').textContent = visible + ' campaigns';
    }
  </script>
</body>
"""
)

INTERNAL_HTML = (
    _BASE_NAV
    + """
<body>
  <div class="sidebar">
    <div class="logo">Warner CM</div>
    <a href="/">Promotions</a>
    <a href="/internal" class="active">Internal TikTok</a>
    <a href="/inbox">Slack Inbox</a>
  </div>
  <div class="main">
    <h1>Internal TikTok</h1>
    <p class="subtitle">Monitor internal creator accounts and audio usage</p>

    <div class="stat-grid">
      <div class="stat">
        <div class="stat-value">{{ stats.account_count }}</div>
        <div class="stat-label">Accounts</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ stats.last_scrape_at[:10] if stats.last_scrape_at else 'Never' }}</div>
        <div class="stat-label">Last Scrape</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ '{:,}'.format(stats.video_count) }}</div>
        <div class="stat-label">Videos Found</div>
      </div>
      <div class="stat">
        <div class="stat-value">{{ stats.unique_sounds }}</div>
        <div class="stat-label">Unique Songs</div>
      </div>
    </div>

    <!-- Scrape controls -->
    <div class="card" style="margin-bottom:24px;">
      <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
        <div class="form-group flex1">
          <label>Bulk add accounts (comma or newline separated)</label>
          <textarea id="bulk-accounts" rows="3" placeholder="@creator1, @creator2&#10;@creator3"></textarea>
        </div>
        <div class="form-group w80">
          <label>Last N hours</label>
          <input type="number" id="hours-back" value="24" min="1" max="720">
        </div>
        <div style="display:flex;flex-direction:column;gap:8px;margin-top:16px;">
          <button class="btn btn-primary" id="scrape-btn" onclick="runScrape()">Run Scrape</button>
        </div>
      </div>
      <div id="scrape-status" style="margin-top:12px;font-size:13px;color:#666;display:none;"></div>
    </div>

    <!-- Accounts table -->
    <div class="table-wrap">
      {% if accounts %}
      <table>
        <thead>
          <tr>
            <th>Username</th>
            <th>Followers</th>
            <th>Videos</th>
            <th>Last Scraped</th>
            <th>Scrapes</th>
            <th>Target</th>
          </tr>
        </thead>
        <tbody>
          {% for a in accounts %}
          <tr>
            <td style="color:#fff;font-weight:500;">{{ a.username }}</td>
            <td>{{ '{:,}'.format(a.followers|int) }}</td>
            <td>{{ a.total_videos }}</td>
            <td>{{ a.last_scraped_at[:10] if a.last_scraped_at else '-' }}</td>
            <td>{{ a.scrape_count }}</td>
            <td>{% if a.is_target_account %}<span class="badge badge-active">Yes</span>{% else %}-{% endif %}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
      <div class="empty">No accounts tracked yet. Add some above and run a scrape.</div>
      {% endif %}
    </div>
  </div>

  <script>
    let _currentSession = null;
    let _pollInterval = null;

    function runScrape() {
      const btn = document.getElementById('scrape-btn');
      const status = document.getElementById('scrape-status');
      btn.disabled = true;
      btn.textContent = 'Running...';
      status.style.display = 'block';
      status.textContent = 'Starting scrape...';

      fetch('/internal/scrape', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          accounts: document.getElementById('bulk-accounts').value,
          hours_back: parseInt(document.getElementById('hours-back').value) || 24
        })
      })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          _currentSession = data.session_id;
          _pollInterval = setInterval(pollStatus, 2000);
        } else {
          status.textContent = 'Error: ' + (data.error || 'Unknown error');
          btn.disabled = false;
          btn.textContent = 'Run Scrape';
        }
      });
    }

    function pollStatus() {
      if (!_currentSession) return;
      fetch('/internal/scrape/status?session_id=' + _currentSession)
      .then(r => r.json())
      .then(data => {
        const status = document.getElementById('scrape-status');
        if (!data || data.status === 'not_found') {
          status.textContent = 'Session not found.';
          _stopPolling();
          return;
        }
        const s = data.status || 'running';
        status.textContent = `Status: ${s} | Accounts: ${data.successful_scrapes||0}/${data.total_accounts||0} | Videos: ${data.total_videos_scraped||0}`;
        if (s === 'completed' || s === 'failed') {
          _stopPolling();
          document.getElementById('scrape-btn').disabled = false;
          document.getElementById('scrape-btn').textContent = 'Run Scrape';
          if (s === 'completed') setTimeout(() => location.reload(), 1000);
        }
      });
    }

    function _stopPolling() {
      if (_pollInterval) { clearInterval(_pollInterval); _pollInterval = null; }
    }
  </script>
</body>
"""
)

INBOX_HTML = (
    _BASE_NAV
    + """
<body>
  <div class="sidebar">
    <div class="logo">Warner CM</div>
    <a href="/">Promotions</a>
    <a href="/internal">Internal TikTok</a>
    <a href="/inbox" class="active">Slack Inbox</a>
  </div>
  <div class="main">
    <h1>Slack Inbox</h1>
    <p class="subtitle">Incoming creator partnership requests — assign to campaign and approve</p>

    <div class="table-wrap">
      {% if requests %}
      <table>
        <thead>
          <tr>
            <th>Creator</th>
            <th>Posts</th>
            <th>Rate</th>
            <th>PayPal</th>
            <th>Received</th>
            <th>Assign Campaign</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {% for r in requests %}
          <tr id="row-{{ r.id }}">
            <td style="color:#fff;font-weight:500;">{{ r.username }}</td>
            <td>{{ r.posts or '-' }}</td>
            <td>{% if r.rate %}${{ '%.0f'|format(r.rate) }}{% else %}-{% endif %}</td>
            <td style="color:#4f8ef7;font-size:12px;">{{ r.paypal or '-' }}</td>
            <td style="color:#555;font-size:12px;">{{ r.received_at[:16].replace('T',' ') if r.received_at else '-' }}</td>
            <td>
              <select class="inbox-campaign-select" id="camp-{{ r.id }}" style="width:220px;">
                <option value="">Select campaign...</option>
                {% for c in campaigns %}
                <option value="{{ c.id }}">{{ c.title }}</option>
                {% endfor %}
              </select>
            </td>
            <td style="display:flex;gap:6px;">
              <button class="btn btn-success btn-sm" onclick="approve('{{ r.id }}')">Approve</button>
              <button class="btn btn-danger btn-sm" onclick="dismiss('{{ r.id }}')">Dismiss</button>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
      <div class="empty">No pending inbox items.</div>
      {% endif %}
    </div>
  </div>

  <script>
    function approve(id) {
      const campId = document.getElementById('camp-' + id).value;
      if (!campId) { alert('Please select a campaign first.'); return; }
      fetch('/api/inbox/' + id + '/approve', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({campaign_id: parseInt(campId)})
      })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          document.getElementById('row-' + id).remove();
        } else {
          alert(data.error || 'Error approving request');
        }
      });
    }

    function dismiss(id) {
      fetch('/api/inbox/' + id + '/dismiss', {method: 'POST'})
      .then(r => r.json())
      .then(data => {
        if (data.success) document.getElementById('row-' + id).remove();
      });
    }
  </script>
</body>
"""
)


# ---------------------------------------------------------------------------
# Utility: parse price / email from freeform text (ported from simple_tracker.py)
# ---------------------------------------------------------------------------

def _parse_price(price_str: str) -> float:
    cleaned = re.sub(r"[^\d.]", "", price_str)
    try:
        return float(cleaned)
    except Exception:
        return 0.0


def _extract_price(text: str) -> tuple[float, str]:
    match = re.search(r"\$(\d+(?:\.\d{2})?)", text)
    if match:
        return float(match.group(1)), text.replace(match.group(0), "").strip()
    return 0.0, text


def _extract_email(text: str) -> tuple[str, str]:
    match = re.search(r"[\w\.\-]+@[\w\.\-]+\.\w+", text)
    if match:
        email = match.group(0)
        return email, text.replace(email, "").strip()
    return "", text


# ---------------------------------------------------------------------------
# Routes: pages
# ---------------------------------------------------------------------------

@app.route("/")
def promotions():
    sort_by = request.args.get("sort", "created_at")
    sort_dir = request.args.get("dir", "DESC")
    campaigns = db.get_campaigns(sort_by=sort_by, sort_dir=sort_dir)
    return render_template_string(PROMOTIONS_HTML, campaigns=campaigns)


@app.route("/campaigns", methods=["POST"])
def create_campaign_route():
    f = request.form
    sound_id = (f.get("sound_id") or "").strip()
    # Strip full URLs to just the numeric ID
    if "tiktok.com" in sound_id or "/" in sound_id:
        m = re.search(r"(\d{10,})", sound_id)
        sound_id = m.group(1) if m else sound_id
    db.create_campaign(
        title=f.get("title", "").strip(),
        artist=f.get("artist", "").strip(),
        song=f.get("song", "").strip(),
        tiktok_sound_id=sound_id or None,
        budget=float(f.get("budget") or 0),
        start_date=f.get("start_date") or None,
    )
    return redirect(url_for("promotions"))


@app.route("/internal")
def internal():
    stats = db.get_internal_stats()
    accounts = db.get_accounts()
    return render_template_string(INTERNAL_HTML, stats=stats, accounts=accounts)


@app.route("/internal/scrape", methods=["POST"])
def trigger_scrape():
    """Launch a background scrape. Returns session_id immediately."""
    data = request.json or {}
    session_id = str(uuid.uuid4())
    accounts_raw = data.get("accounts", "")
    hours_back = int(data.get("hours_back", 24))

    account_list = [
        a.strip().lstrip("@")
        for a in re.split(r"[,\n]+", accounts_raw)
        if a.strip()
    ]

    db.create_scrape_session(
        session_id,
        {"accounts": account_list, "hours_back": hours_back},
        len(account_list),
    )

    t = threading.Thread(
        target=_run_scrape,
        args=(session_id, account_list, hours_back),
        daemon=True,
    )
    t.start()
    return jsonify({"success": True, "session_id": session_id})


def _run_scrape(session_id: str, accounts: list[str], hours_back: int):
    """Background scrape worker. Imports master_tracker lazily to avoid circular deps."""
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from src.scrapers.master_tracker import MasterTracker  # type: ignore

        tracker = MasterTracker()
        successful = 0
        failed = 0
        total_videos = 0
        new_videos = 0
        updated_videos = 0

        for username in accounts:
            try:
                account_id = db.ensure_account_exists(username)
                results = tracker.scrape_account(username, hours_back=hours_back)
                for video in results.get("videos", []):
                    is_new, is_upd = db.insert_or_update_video(video, account_id, session_id)
                    total_videos += 1
                    new_videos += int(is_new)
                    updated_videos += int(is_upd)
                successful += 1
            except Exception as e:
                failed += 1
                print(f"[scrape] Error scraping {username}: {e}")

        db.update_scrape_session(
            session_id, "completed",
            successful_scrapes=successful,
            failed_scrapes=failed,
            total_videos_scraped=total_videos,
            total_new_videos=new_videos,
            total_updated_videos=updated_videos,
        )
    except Exception as e:
        db.update_scrape_session(session_id, "failed", error_log=str(e))


@app.route("/internal/scrape/status")
def scrape_status():
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"status": "idle"})
    session = db.get_session(session_id)
    if not session:
        return jsonify({"status": "not_found"})
    return jsonify(dict(session))


@app.route("/inbox")
def inbox():
    items = db.get_inbox(status="pending")
    campaigns = db.get_campaigns(sort_by="title", sort_dir="ASC")
    return render_template_string(INBOX_HTML, requests=items, campaigns=campaigns)


# ---------------------------------------------------------------------------
# Routes: inbox API
# ---------------------------------------------------------------------------

@app.route("/api/inbox/<request_id>/approve", methods=["POST"])
def approve_request(request_id):
    data = request.json or {}
    campaign_id = data.get("campaign_id")
    if not campaign_id:
        return jsonify({"success": False, "error": "campaign_id required"}), 400
    try:
        booking_id = db.approve_inbox(request_id, int(campaign_id))
        return jsonify({"success": True, "booking_id": booking_id})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/inbox/<request_id>/dismiss", methods=["POST"])
def dismiss_request(request_id):
    db.dismiss_inbox(request_id)
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Routes: Slack webhook
# ---------------------------------------------------------------------------

@app.route("/webhook/slack", methods=["POST"])
def handle_slack():
    """
    Slack sends a POST when a creator DMs requesting to be booked.
    Expected payload (flexible):
      { "username": "@creator", "paypal": "...", "rate": 50, "posts": 1, ... }
    Everything is stored as an inbox_request for manual review.
    """
    try:
        payload = request.json or {}
        username = payload.get("username", "").strip()
        if not username:
            return jsonify({"success": False, "error": "No username provided"})

        req_id = db.add_inbox_request(
            username=username,
            paypal=payload.get("paypal", ""),
            rate=float(payload["rate"]) if payload.get("rate") else None,
            posts=int(payload.get("posts", 0)),
            source="slack",
            raw_payload=payload,
        )
        return jsonify({"success": True, "id": req_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Routes: ManyChat webhooks (ported from simple_tracker.py)
# ---------------------------------------------------------------------------

@app.route("/webhook/booked", methods=["POST"])
def handle_booked():
    try:
        data = request.json or {}
        username = data.get("username", "").strip()
        message = data.get("message", "").strip()
        campaign = data.get("campaign", "").strip()
        price_str = data.get("price", "").strip()
        paypal = data.get("paypal", "").strip()

        if not username:
            return jsonify({"success": False, "error": "No username provided"})

        # Parse price/paypal from freeform message if not provided directly
        if message and not (price_str and paypal):
            price_val, remaining = _extract_price(message)
            extracted_email, _ = _extract_email(remaining)
            if price_val > 0:
                price_str = str(price_val)
            if extracted_email:
                paypal = extracted_email

        price = _parse_price(price_str) if price_str else 0.0

        if price <= 0:
            return jsonify({
                "success": False, "needs_info": True, "missing": "price",
                "message": "What's the price for this booking?",
            })

        if not paypal or "@" not in paypal:
            stored = db.get_paypal(username)
            if stored:
                paypal = stored
            else:
                return jsonify({
                    "success": False, "needs_info": True, "missing": "paypal",
                    "message": "What's their PayPal email?",
                })

        if not campaign:
            db.set_pending_booking(username, price, paypal)
            return jsonify({
                "success": True, "needs_campaign": True,
                "price": price, "paypal": paypal,
                "message": f"Got ${price:.0f} to {paypal}. Which campaign is this for?",
            })

        # Resolve campaign_id
        campaign_id = _resolve_campaign_id(campaign)
        booking_id = db.add_booking(username, campaign_id, campaign, price, paypal)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] BOOKED: {username} - {campaign} - ${price} - {paypal}")
        return jsonify({
            "success": True, "booking_id": booking_id,
            "message": f"✓ {username} booked for {campaign} at ${price:.0f}. PayPal: {paypal}",
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/webhook/booked/campaign", methods=["POST"])
def handle_booked_campaign():
    """Step 2 of ManyChat flow: receive campaign name after price/paypal were captured."""
    try:
        data = request.json or {}
        username = data.get("username", "").strip()
        campaign = data.get("campaign", "").strip()

        if not username:
            return jsonify({"success": False, "error": "No username provided"})
        if not campaign:
            return jsonify({"success": False, "error": "No campaign provided"})

        pending = db.get_pending_booking(username)
        if not pending:
            return jsonify({
                "success": False,
                "error": "No pending booking found. Start with BOOKED $amount email@paypal.com",
            })

        campaign_id = _resolve_campaign_id(campaign)
        booking_id = db.add_booking(
            username, campaign_id, campaign,
            float(pending["price"]), pending["paypal"],
        )
        db.clear_pending_booking(username)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] BOOKED complete: {username} - {campaign} - ${pending['price']} - {pending['paypal']}")
        return jsonify({
            "success": True, "booking_id": booking_id,
            "message": f"✓ {username} booked for {campaign} at ${float(pending['price']):.0f}. PayPal: {pending['paypal']}",
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/webhook/done", methods=["POST"])
def handle_done():
    """Creator marks their posts as done."""
    try:
        data = request.json or {}
        username = data.get("username", "").strip()
        campaign = data.get("campaign", "").strip()

        if not username:
            return jsonify({"success": False, "error": "No username provided"})

        booking = db.find_booking(username, campaign or None)
        if not booking:
            return jsonify({
                "success": False, "found": False,
                "message": "I couldn't find an active booking for you. Please contact the campaign manager.",
            })

        print(f"[{datetime.now().strftime('%H:%M:%S')}] DONE request: {username} - {booking['campaign_name']}")
        return jsonify({
            "success": True, "found": True,
            "booking_id": booking["id"],
            "campaign": booking["campaign_name"],
            "price": float(booking["price"]),
            "paypal": booking["paypal"],
            "message": (
                f"Found your booking for {booking['campaign_name']}! "
                f"You'll receive ${float(booking['price']):.2f} to {booking['paypal']}. "
                f"Is this PayPal still correct? Reply YES or send a different email."
            ),
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/webhook/confirm", methods=["POST"])
def handle_confirm():
    """Creator confirms PayPal — moves booking to payment_needed."""
    try:
        data = request.json or {}
        booking_id = data.get("booking_id", "").strip()
        paypal = data.get("paypal", "").strip()

        if not booking_id:
            return jsonify({"success": False, "error": "No booking ID provided"})

        new_paypal = None
        if paypal and "@" in paypal and paypal.lower() not in ("same", "yes"):
            new_paypal = paypal

        db.update_booking(booking_id, status="payment_needed", paypal=new_paypal)

        bookings = db.get_bookings()
        booking = next((b for b in bookings if b["id"] == booking_id), None)
        if not booking:
            return jsonify({"success": True, "message": "Confirmed! Payment will be processed soon."})

        return jsonify({
            "success": True,
            "message": (
                f"You're all set! ${float(booking['price']):.2f} will be sent to "
                f"{booking['paypal']} within 2 business days."
            ),
            "paypal": booking["paypal"],
            "price": float(booking["price"]),
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Routes: bookings API
# ---------------------------------------------------------------------------

@app.route("/api/bookings", methods=["GET"])
def api_bookings():
    """Server-side sort/filter/paginate — ready for TanStack Tables."""
    status = request.args.get("status")
    campaign_id = request.args.get("campaign_id", type=int)
    sort_by = request.args.get("sort_by", "booked_at")
    sort_dir = request.args.get("sort_dir", "DESC")
    limit = request.args.get("limit", 200, type=int)
    offset = request.args.get("offset", 0, type=int)

    rows = db.get_bookings(status, campaign_id, sort_by, sort_dir, limit, offset)
    # Serialize datetimes and decimals
    data = [_serialize(r) for r in rows]
    return jsonify({
        "data": data,
        "meta": {
            "total": len(data),
            "limit": limit,
            "offset": offset,
            "sort_by": sort_by,
            "sort_dir": sort_dir,
        },
    })


@app.route("/api/bookings/update", methods=["POST"])
def api_update_booking():
    data = request.json or {}
    db.update_booking(
        data["id"],
        status=data.get("status"),
        notes=data.get("notes"),
        paypal=data.get("paypal"),
    )
    return jsonify({"success": True})


@app.route("/api/bookings/delete", methods=["POST"])
def api_delete_booking():
    data = request.json or {}
    db.delete_booking(data["id"])
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Routes: migration API (used by migrate_campaigns_to_railway.py)
# ---------------------------------------------------------------------------

@app.route("/api/migrate/campaign", methods=["POST"])
def migrate_campaign_api():
    """
    Bulk import from local migration script.
    Payload: { slug, campaign: {...}, creators: [...], matched_videos: [...], scrape_log: {...} }
    """
    try:
        payload = request.json or {}
        meta = payload.get("campaign", {})
        creators = payload.get("creators", [])

        # Upsert campaign
        title = meta.get("title") or meta.get("name") or payload.get("slug", "Unknown")
        artist = meta.get("artist", "")
        song = meta.get("song", "")
        sound_id = str(meta.get("sound_id", "")) or None
        budget = float(meta.get("budget", 0) or 0)
        start_date = meta.get("start_date") or None

        campaign_id = db.create_campaign(
            title=title, artist=artist, song=song,
            tiktok_sound_id=sound_id, budget=budget, start_date=start_date,
        )

        return jsonify({
            "success": True,
            "campaign_id": campaign_id,
            "title": title,
            "creators_count": len(creators),
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Routes: health
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    try:
        with db.get_db() as conn:
            db._cursor(conn).execute("SELECT 1")
        return jsonify({"status": "ok", "db": "connected", "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return jsonify({"status": "error", "db": str(e)}), 500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_campaign_id(campaign_name: str) -> int | None:
    """Fuzzy-match a campaign name to a campaigns.id. Returns None if not found."""
    try:
        with db.get_db() as conn:
            cur = db._cursor(conn)
            cur.execute(
                "SELECT id FROM campaigns WHERE LOWER(title) LIKE %s LIMIT 1",
                (f"%{campaign_name.lower()}%",),
            )
            row = cur.fetchone()
        return row["id"] if row else None
    except Exception:
        return None


def _serialize(obj):
    """Recursively convert non-JSON-serializable types (datetime, Decimal)."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    try:
        from decimal import Decimal
        if isinstance(obj, Decimal):
            return float(obj)
    except ImportError:
        pass
    return obj


# ---------------------------------------------------------------------------
# Entry point (dev only — gunicorn is used in production)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Warner Campaign Manager — http://localhost:5055")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5055)), debug=False)
