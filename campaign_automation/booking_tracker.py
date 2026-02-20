"""
Booking Tracker - Simple dashboard with Add Booking form
Run with: python booking_tracker.py
"""

from flask import Flask, request, jsonify, render_template_string
import json
import requests
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)
DATA_FILE = Path(__file__).parent / "bookings.json"

# ManyChat API config - set your API key here or as environment variable
MANYCHAT_API_KEY = os.environ.get("MANYCHAT_API_KEY", "3376594:052694c218a1a411d36dadd915799adc")


def send_manychat_message(subscriber_id: str, message: str) -> bool:
    """Send a message to a user via ManyChat API"""
    if not MANYCHAT_API_KEY:
        print("[WARNING] MANYCHAT_API_KEY not set - cannot send message")
        return False

    url = "https://api.manychat.com/fb/sending/sendContent"
    headers = {
        "Authorization": f"Bearer {MANYCHAT_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "subscriber_id": subscriber_id,
        "data": {
            "version": "v2",
            "content": {
                "messages": [
                    {"type": "text", "text": message}
                ]
            }
        },
        "message_tag": "POST_PURCHASE_UPDATE"  # Required for messages outside 24h window
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            print(f"[ManyChat] Sent message to {subscriber_id}")
            return True
        else:
            print(f"[ManyChat] Error: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"[ManyChat] Exception: {e}")
        return False


def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"bookings": [], "paypal_db": {}}


def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def add_booking(username, campaign, price, paypal):
    data = load_data()
    booking_id = f"{username}_{datetime.now().timestamp()}"
    data["bookings"].append({
        "id": booking_id,
        "username": username,
        "campaign": campaign,
        "price": float(str(price).replace('$', '').replace(',', '')),
        "paypal": paypal,
        "booked_at": datetime.now().isoformat(),
        "status": "booked",
        "completed_at": None,
        "notes": ""
    })
    data["paypal_db"][username.lower()] = paypal
    save_data(data)
    return booking_id


DASHBOARD = """
<!DOCTYPE html>
<html>
<head>
    <title>Booking Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, sans-serif; }
        body { margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { margin-bottom: 20px; }

        .form-box { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .form-title { font-weight: 600; margin-bottom: 15px; font-size: 16px; }
        .form-row { display: flex; gap: 10px; flex-wrap: wrap; }
        .form-row input { padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
        .form-row input:focus { outline: none; border-color: #007bff; }
        #username { width: 120px; }
        #campaign { flex: 1; min-width: 200px; }
        #price { width: 80px; }
        #paypal { width: 180px; }
        .btn-add { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: 500; }
        .btn-add:hover { background: #0056b3; }

        .stats { display: flex; gap: 15px; margin-bottom: 20px; }
        .stat { background: white; padding: 15px 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .stat-val { font-size: 24px; font-weight: bold; }
        .stat-label { font-size: 12px; color: #666; }

        .section { margin-bottom: 25px; }
        .section-title { font-size: 16px; font-weight: 600; margin-bottom: 10px; }
        .badge { background: #dc3545; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; margin-left: 8px; }
        .badge.yellow { background: #ffc107; color: #000; }
        .badge.green { background: #28a745; }
        .badge.blue { background: #17a2b8; }

        .paid-date { font-size: 11px; color: #666; }

        table { width: 100%; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-collapse: collapse; }
        th { background: #f8f9fa; padding: 12px; text-align: left; font-size: 12px; color: #666; border-bottom: 1px solid #eee; }
        td { padding: 12px; border-bottom: 1px solid #eee; }
        .username { font-weight: 600; color: #007bff; }
        .price { font-weight: 600; color: #28a745; }
        .paypal { color: #0070ba; font-size: 13px; }

        .btn { padding: 5px 10px; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; margin-right: 5px; }
        .btn-green { background: #28a745; color: white; }
        .btn-red { background: #dc3545; color: white; }
        .btn-gray { background: #6c757d; color: white; }

        .notes { width: 100px; padding: 5px; border: 1px solid #ddd; border-radius: 4px; font-size: 12px; }
        .empty { padding: 30px; text-align: center; color: #999; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Booking Tracker</h1>

        <div class="form-box">
            <div class="form-title">+ Add Booking</div>
            <div class="form-row">
                <input type="text" id="username" placeholder="@username">
                <input type="text" id="campaign" placeholder="Campaign (Artist - Song)">
                <input type="text" id="price" placeholder="$50">
                <input type="text" id="paypal" placeholder="paypal@email.com">
                <button class="btn-add" onclick="addBooking()">Add</button>
            </div>
        </div>

        <div class="stats">
            <div class="stat"><div class="stat-val">{{ payment_needed|length }}</div><div class="stat-label">PAYMENT NEEDED</div></div>
            <div class="stat"><div class="stat-val">{{ booked|length }}</div><div class="stat-label">WAITING FOR POSTS</div></div>
            <div class="stat"><div class="stat-val">${{ "%.0f"|format(total_owed) }}</div><div class="stat-label">TOTAL OWED</div></div>
        </div>

        <div class="section">
            <div class="section-title">Payment Needed <span class="badge">{{ payment_needed|length }}</span></div>
            {% if payment_needed %}
            <table>
                <tr><th>Username</th><th>Campaign</th><th>Price</th><th>PayPal</th><th>Notes</th><th>Actions</th></tr>
                {% for b in payment_needed %}
                <tr>
                    <td class="username">{{ b.username }}</td>
                    <td>{{ b.campaign }}</td>
                    <td class="price">${{ "%.0f"|format(b.price) }}</td>
                    <td class="paypal">{{ b.paypal }}</td>
                    <td><input class="notes" value="{{ b.notes }}" onchange="updateNotes('{{ b.id }}', this.value)"></td>
                    <td>
                        <button class="btn btn-green" onclick="setStatus('{{ b.id }}', 'paid')">Paid</button>
                        <button class="btn btn-gray" onclick="deleteb('{{ b.id }}')">X</button>
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% else %}<div class="empty">No payments needed</div>{% endif %}
        </div>

        <div class="section">
            <div class="section-title">Booked - Waiting for Posts <span class="badge yellow">{{ booked|length }}</span></div>
            {% if booked %}
            <table>
                <tr><th>Username</th><th>Campaign</th><th>Price</th><th>PayPal</th><th>Notes</th><th>Actions</th></tr>
                {% for b in booked %}
                <tr>
                    <td class="username">{{ b.username }}</td>
                    <td>{{ b.campaign }}</td>
                    <td class="price">${{ "%.0f"|format(b.price) }}</td>
                    <td class="paypal">{{ b.paypal }}</td>
                    <td><input class="notes" value="{{ b.notes }}" onchange="updateNotes('{{ b.id }}', this.value)"></td>
                    <td>
                        <button class="btn btn-red" onclick="setStatus('{{ b.id }}', 'payment_needed')">Done</button>
                        <button class="btn btn-gray" onclick="deleteb('{{ b.id }}')">X</button>
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% else %}<div class="empty">No active bookings</div>{% endif %}
        </div>

        <div class="section">
            <div class="section-title">Recently Paid <span class="badge blue">{{ paid|length }}</span></div>
            {% if paid %}
            <table>
                <tr><th>Username</th><th>Campaign</th><th>Price</th><th>PayPal</th><th>Paid</th><th>Actions</th></tr>
                {% for b in paid %}
                <tr>
                    <td class="username">{{ b.username }}</td>
                    <td>{{ b.campaign }}</td>
                    <td class="price">${{ "%.0f"|format(b.price) }}</td>
                    <td class="paypal">{{ b.paypal }}</td>
                    <td class="paid-date">{{ b.paid_at_display }}</td>
                    <td>
                        <button class="btn btn-gray" onclick="deleteb('{{ b.id }}')">X</button>
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% else %}<div class="empty">No recently paid bookings</div>{% endif %}
        </div>
    </div>

    <script>
        // Auto-fill PayPal when username is entered
        document.getElementById('username').addEventListener('blur', function() {
            const username = this.value.trim();
            const paypalField = document.getElementById('paypal');
            if (username && !paypalField.value) {
                fetch('/api/lookup_paypal', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username: username})
                })
                .then(r => r.json())
                .then(data => {
                    if (data.paypal) {
                        paypalField.value = data.paypal;
                        paypalField.style.backgroundColor = '#e8f5e9';  // Light green to show auto-filled
                    }
                });
            }
        });

        function addBooking() {
            const data = {
                username: document.getElementById('username').value,
                campaign: document.getElementById('campaign').value,
                price: document.getElementById('price').value,
                paypal: document.getElementById('paypal').value
            };
            if (!data.username || !data.campaign || !data.price || !data.paypal) {
                alert('Fill all fields'); return;
            }
            fetch('/api/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            }).then(() => location.reload());
        }

        function setStatus(id, status) {
            fetch('/api/status', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id, status})
            }).then(() => location.reload());
        }

        function updateNotes(id, notes) {
            fetch('/api/notes', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id, notes})
            });
        }

        function deleteb(id) {
            if (confirm('Delete?')) {
                fetch('/api/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id})
                }).then(() => location.reload());
            }
        }

        // Auto-refresh every 2 minutes (only if not typing)
        let lastActivity = Date.now();
        document.addEventListener('keydown', () => lastActivity = Date.now());
        document.addEventListener('click', () => lastActivity = Date.now());
        setInterval(() => {
            if (Date.now() - lastActivity > 120000) location.reload();
        }, 120000);
    </script>
</body>
</html>
"""


@app.route('/')
def dashboard():
    data = load_data()
    bookings = data.get("bookings", [])
    booked = [b for b in bookings if b["status"] == "booked"]
    payment_needed = [b for b in bookings if b["status"] == "payment_needed"]
    paid = [b for b in bookings if b["status"] == "paid"]

    # Add friendly date display for paid bookings
    for b in paid:
        if b.get("paid_at"):
            try:
                paid_dt = datetime.fromisoformat(b["paid_at"])
                b["paid_at_display"] = paid_dt.strftime("%b %d, %I:%M %p")
            except:
                b["paid_at_display"] = ""
        else:
            b["paid_at_display"] = ""

    # Sort paid by most recent first
    paid.sort(key=lambda x: x.get("paid_at", ""), reverse=True)

    total_owed = sum(b["price"] for b in payment_needed)
    return render_template_string(DASHBOARD, booked=booked, payment_needed=payment_needed, paid=paid, total_owed=total_owed)


@app.route('/api/add', methods=['POST'])
def api_add():
    d = request.json
    add_booking(d['username'], d['campaign'], d['price'], d['paypal'])
    return jsonify({"ok": True})


@app.route('/api/status', methods=['POST'])
def api_status():
    d = request.json
    data = load_data()
    for b in data["bookings"]:
        if b["id"] == d["id"]:
            b["status"] = d["status"]
            if d["status"] == "payment_needed":
                b["completed_at"] = datetime.now().isoformat()
            if d["status"] == "paid":
                b["paid_at"] = datetime.now().isoformat()
    save_data(data)
    return jsonify({"ok": True})


@app.route('/api/notes', methods=['POST'])
def api_notes():
    d = request.json
    data = load_data()
    for b in data["bookings"]:
        if b["id"] == d["id"]:
            b["notes"] = d["notes"]
    save_data(data)
    return jsonify({"ok": True})


@app.route('/api/delete', methods=['POST'])
def api_delete():
    d = request.json
    data = load_data()
    data["bookings"] = [b for b in data["bookings"] if b["id"] != d["id"]]
    save_data(data)
    return jsonify({"ok": True})


@app.route('/api/lookup_paypal', methods=['POST'])
def api_lookup_paypal():
    """Look up saved PayPal for a username"""
    d = request.json
    username = d.get("username", "").strip().lower()
    data = load_data()
    paypal = data.get("paypal_db", {}).get(username, "")
    return jsonify({"paypal": paypal})


@app.route('/webhook/done', methods=['GET', 'POST'])
def webhook_done():
    """
    ManyChat calls this when creator says DONE.

    Expected payload (POST JSON body or GET query params):
    {
        "username": "creatorname",
        "subscriber_id": "123456789"  // ManyChat subscriber ID for sending reply
    }

    Returns:
    - If 1 active booking: marks it done, returns success
    - If multiple active bookings: returns list for creator to choose
    - If no bookings: returns error message
    """
    # Handle both GET (query params) and POST (JSON body)
    if request.method == 'GET':
        username = request.args.get("username", "").strip()
        subscriber_id = request.args.get("subscriber_id", "")
        print(f"[WEBHOOK] GET request - username: '{username}', subscriber_id: '{subscriber_id}'", flush=True)
        print(f"[WEBHOOK] All query params: {dict(request.args)}", flush=True)
    else:
        d = request.json or {}
        username = d.get("username", "").strip()
        subscriber_id = d.get("subscriber_id", "")
        print(f"[WEBHOOK] POST request - username: '{username}', subscriber_id: '{subscriber_id}'", flush=True)
        print(f"[WEBHOOK] Full JSON body: {d}", flush=True)

    data = load_data()

    # Find ALL active bookings for this user
    active_bookings = [
        b for b in data["bookings"]
        if b["username"].lower() == username.lower() and b["status"] == "booked"
    ]

    print(f"[WEBHOOK] Found {len(active_bookings)} active bookings for {username}", flush=True)

    # No active bookings
    if len(active_bookings) == 0:
        message = "No active booking found for your account. Please contact us if you think this is an error."
        if subscriber_id and MANYCHAT_API_KEY:
            send_manychat_message(subscriber_id, message)
        return jsonify({
            "success": False,
            "multiple": False,
            "message": message
        })

    # Exactly 1 booking - mark it done immediately
    if len(active_bookings) == 1:
        b = active_bookings[0]
        b["status"] = "payment_needed"
        b["completed_at"] = datetime.now().isoformat()
        save_data(data)

        message = f"Got it! ${b['price']:.0f} will be sent to {b['paypal']} within 1 business day."
        print(f"[WEBHOOK] Marked single booking done: {b['campaign']}", flush=True)

        if subscriber_id and MANYCHAT_API_KEY:
            send_manychat_message(subscriber_id, message)

        return jsonify({
            "success": True,
            "multiple": False,
            "message": message
        })

    # Multiple bookings - return list for creator to choose
    campaigns = []
    for i, b in enumerate(active_bookings, 1):
        campaigns.append({
            "number": i,
            "id": b["id"],
            "campaign": b["campaign"],
            "price": b["price"]
        })

    # Build a message listing the campaigns
    campaign_list = "\n".join([f"{c['number']}. {c['campaign']} (${c['price']:.0f})" for c in campaigns])
    message = f"You have {len(campaigns)} active bookings:\n{campaign_list}\n\nReply with the number of the campaign you finished."

    print(f"[WEBHOOK] Multiple bookings found, asking creator to choose", flush=True)

    return jsonify({
        "success": True,
        "multiple": True,
        "count": len(campaigns),
        "message": message,
        "campaigns": campaigns
    })


@app.route('/webhook/done/select', methods=['GET', 'POST'])
def webhook_done_select():
    """
    Called when creator selects which campaign they finished (for multiple bookings).

    Expected payload:
    {
        "username": "creatorname",
        "subscriber_id": "123456789",
        "selection": "1"  // The number they replied with, or campaign ID
    }
    """
    # Handle both GET and POST
    if request.method == 'GET':
        username = request.args.get("username", "").strip()
        subscriber_id = request.args.get("subscriber_id", "")
        selection = request.args.get("selection", "").strip()
        print(f"[SELECT] GET - username: '{username}', selection: '{selection}'", flush=True)
    else:
        d = request.json or {}
        username = d.get("username", "").strip()
        subscriber_id = d.get("subscriber_id", "")
        selection = str(d.get("selection", "")).strip()
        print(f"[SELECT] POST - username: '{username}', selection: '{selection}'", flush=True)

    data = load_data()

    # Find active bookings for this user
    active_bookings = [
        b for b in data["bookings"]
        if b["username"].lower() == username.lower() and b["status"] == "booked"
    ]

    if not active_bookings:
        return jsonify({
            "success": False,
            "message": "No active bookings found."
        })

    # Try to match selection - could be a number (1, 2, 3) or booking ID
    selected_booking = None

    # First try as a number
    try:
        idx = int(selection) - 1
        if 0 <= idx < len(active_bookings):
            selected_booking = active_bookings[idx]
    except ValueError:
        pass

    # If not found, try matching by booking ID
    if not selected_booking:
        for b in active_bookings:
            if b["id"] == selection:
                selected_booking = b
                break

    # If still not found, try partial campaign name match
    if not selected_booking:
        selection_lower = selection.lower()
        for b in active_bookings:
            if selection_lower in b["campaign"].lower():
                selected_booking = b
                break

    if not selected_booking:
        campaign_list = "\n".join([f"{i}. {b['campaign']}" for i, b in enumerate(active_bookings, 1)])
        message = f"I didn't understand that. Please reply with a number:\n{campaign_list}"
        return jsonify({
            "success": False,
            "message": message
        })

    # Mark the selected booking as done
    for b in data["bookings"]:
        if b["id"] == selected_booking["id"]:
            b["status"] = "payment_needed"
            b["completed_at"] = datetime.now().isoformat()
            save_data(data)
            break

    message = f"Got it! ${selected_booking['price']:.0f} for {selected_booking['campaign']} will be sent to {selected_booking['paypal']} within 1 business day."
    print(f"[SELECT] Marked booking done: {selected_booking['campaign']}", flush=True)

    if subscriber_id and MANYCHAT_API_KEY:
        send_manychat_message(subscriber_id, message)

    return jsonify({
        "success": True,
        "message": message,
        "campaign": selected_booking["campaign"],
        "price": selected_booking["price"]
    })


if __name__ == '__main__':
    print("\n  BOOKING TRACKER")
    print("  Dashboard: http://localhost:5055")
    print("  ManyChat webhook: POST /webhook/done")
    print(f"  ManyChat API: {'Configured' if MANYCHAT_API_KEY else 'NOT SET (set MANYCHAT_API_KEY env var)'}\n")
    app.run(host='0.0.0.0', port=5055, debug=False)
