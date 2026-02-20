"""
Simple Payment Tracker
======================

Two-stage flow:
1. BOOKED - Campaign manager books a creator (captures campaign, price, PayPal)
2. DONE - Creator marks posts complete, moves to payment needed

Run with: python simple_tracker.py
Expose with: ngrok http 5050
"""

from flask import Flask, request, jsonify, render_template_string
import json
import re
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# Data file
DATA_FILE = Path(__file__).parent / "tracker_data.json"


# =============================================================================
# DATA FUNCTIONS
# =============================================================================

def load_data():
    """Load data from file"""
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            if "bookings" not in data:
                data["bookings"] = []
            if "paypal_db" not in data:
                data["paypal_db"] = {}
            return data
    return {"bookings": [], "paypal_db": {}}


def save_data(data):
    """Save to file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def add_booking(username: str, campaign: str, price: float, paypal: str):
    """Add a new booking (creator is booked, waiting for posts)"""
    data = load_data()

    booking_id = f"{username}_{datetime.now().timestamp()}"

    data["bookings"].append({
        "id": booking_id,
        "username": username,
        "campaign": campaign,
        "price": price,
        "paypal": paypal,
        "booked_at": datetime.now().isoformat(),
        "status": "booked",  # booked -> payment_needed -> paid
        "completed_at": None,
        "notes": ""
    })

    # Also save PayPal to database for future reference
    data["paypal_db"][username.lower()] = paypal

    save_data(data)
    return booking_id


def find_booking(username: str, campaign: str = None):
    """Find a booking for a user, optionally by campaign"""
    data = load_data()
    username_lower = username.lower()

    for booking in reversed(data["bookings"]):  # Most recent first
        if booking["username"].lower() == username_lower:
            if booking["status"] == "booked":  # Only find active bookings
                if campaign:
                    # Check if campaign matches (fuzzy)
                    if campaign.lower() in booking["campaign"].lower() or \
                       booking["campaign"].lower() in campaign.lower():
                        return booking
                else:
                    return booking
    return None


def mark_done(booking_id: str):
    """Mark a booking as done (payment needed)"""
    data = load_data()
    for booking in data["bookings"]:
        if booking["id"] == booking_id:
            booking["status"] = "payment_needed"
            booking["completed_at"] = datetime.now().isoformat()
            break
    save_data(data)


def mark_paid(booking_id: str):
    """Mark a booking as paid"""
    data = load_data()
    for booking in data["bookings"]:
        if booking["id"] == booking_id:
            booking["status"] = "paid"
            booking["paid_at"] = datetime.now().isoformat()
            break
    save_data(data)


def update_booking(booking_id: str, status: str = None, notes: str = None, paypal: str = None):
    """Update a booking"""
    data = load_data()
    for booking in data["bookings"]:
        if booking["id"] == booking_id:
            if status:
                booking["status"] = status
                if status == "payment_needed":
                    booking["completed_at"] = datetime.now().isoformat()
                elif status == "paid":
                    booking["paid_at"] = datetime.now().isoformat()
            if notes is not None:
                booking["notes"] = notes
            if paypal:
                booking["paypal"] = paypal
                # Also update PayPal database
                data["paypal_db"][booking["username"].lower()] = paypal
            break
    save_data(data)


def delete_booking(booking_id: str):
    """Delete a booking"""
    data = load_data()
    data["bookings"] = [b for b in data["bookings"] if b["id"] != booking_id]
    save_data(data)


def get_bookings(status_filter: str = None):
    """Get bookings, optionally filtered by status"""
    data = load_data()
    bookings = data.get("bookings", [])

    if status_filter and status_filter != "all":
        bookings = [b for b in bookings if b["status"] == status_filter]

    # Sort by timestamp, newest first
    bookings.sort(key=lambda x: x.get("booked_at", ""), reverse=True)
    return bookings


def get_paypal(username: str) -> str:
    """Get stored PayPal for a username"""
    data = load_data()
    return data.get("paypal_db", {}).get(username.lower(), "")


def parse_price(price_str: str) -> float:
    """Parse price from string like '$50' or '50' or '$50.00'"""
    # Remove $ and any whitespace
    cleaned = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(cleaned)
    except:
        return 0.0


def extract_price_from_text(text: str) -> tuple[float, str]:
    """Extract price from text like 'BOOKED $50 email@test.com'
    Returns (price, remaining_text)"""
    # Look for $XX or $XX.XX pattern
    match = re.search(r'\$(\d+(?:\.\d{2})?)', text)
    if match:
        price = float(match.group(1))
        remaining = text.replace(match.group(0), '').strip()
        return price, remaining
    return 0.0, text


def extract_email_from_text(text: str) -> tuple[str, str]:
    """Extract email from text
    Returns (email, remaining_text)"""
    # Email pattern
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if match:
        email = match.group(0)
        remaining = text.replace(email, '').strip()
        return email, remaining
    return "", text


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@app.route('/webhook/booked', methods=['POST'])
def handle_booked():
    """
    Campaign manager books a creator.

    Option C Flow: Parse price and PayPal from message, ask for campaign separately.

    Expected payload (Option C - combined message):
    {
        "username": "@creator123",
        "message": "BOOKED $50 creator@paypal.com"  <-- parse price and paypal from this
    }

    OR full payload (all fields provided):
    {
        "username": "@creator123",
        "campaign": "Xavier Wulf Cross Cuttin",
        "price": "$50",
        "paypal": "creator@paypal.com"
    }
    """
    try:
        data = request.json
        username = data.get("username", "").strip()
        message = data.get("message", "").strip()

        # Check if full payload provided
        campaign = data.get("campaign", "").strip()
        price_str = data.get("price", "").strip()
        paypal = data.get("paypal", "").strip()

        if not username:
            return jsonify({"success": False, "error": "No username provided"})

        # If message provided, parse price and paypal from it
        if message and not (price_str and paypal):
            price, remaining = extract_price_from_text(message)
            extracted_email, _ = extract_email_from_text(remaining)

            if price > 0:
                price_str = str(price)
            if extracted_email:
                paypal = extracted_email

        # Parse price
        price = parse_price(price_str) if price_str else 0.0

        # Check if we have price and paypal
        if price <= 0:
            return jsonify({
                "success": False,
                "needs_info": True,
                "missing": "price",
                "message": "What's the price for this booking?"
            })

        if not paypal or "@" not in paypal:
            # Check if we have stored PayPal for this user
            stored_paypal = get_paypal(username)
            if stored_paypal:
                paypal = stored_paypal
            else:
                return jsonify({
                    "success": False,
                    "needs_info": True,
                    "missing": "paypal",
                    "message": "What's their PayPal email?"
                })

        # If no campaign yet, store temporarily and ask for campaign
        if not campaign:
            # Store the price/paypal temporarily and ask for campaign
            pending_key = f"pending_{username.lower()}"
            pending_data = load_data()
            if "pending_bookings" not in pending_data:
                pending_data["pending_bookings"] = {}
            pending_data["pending_bookings"][pending_key] = {
                "username": username,
                "price": price,
                "paypal": paypal,
                "created_at": datetime.now().isoformat()
            }
            save_data(pending_data)

            print(f"[{datetime.now().strftime('%H:%M:%S')}] BOOKED pending: {username} - ${price} - {paypal} (waiting for campaign)")

            return jsonify({
                "success": True,
                "needs_campaign": True,
                "price": price,
                "paypal": paypal,
                "message": f"Got ${price:.0f} to {paypal}. Which campaign is this for?"
            })

        # We have everything - create the booking
        booking_id = add_booking(username, campaign, price, paypal)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] BOOKED: {username} - {campaign} - ${price} - {paypal}")

        return jsonify({
            "success": True,
            "booking_id": booking_id,
            "message": f"✓ {username} booked for {campaign} at ${price:.0f}. PayPal: {paypal}"
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/webhook/booked/campaign', methods=['POST'])
def handle_booked_campaign():
    """
    Second step of Option C flow - receive campaign name after price/paypal.

    Expected payload:
    {
        "username": "@creator123",
        "campaign": "Xavier Wulf Cross Cuttin"
    }
    """
    try:
        data = request.json
        username = data.get("username", "").strip()
        campaign = data.get("campaign", "").strip()

        if not username:
            return jsonify({"success": False, "error": "No username provided"})

        if not campaign:
            return jsonify({"success": False, "error": "No campaign provided"})

        # Look up pending booking
        pending_key = f"pending_{username.lower()}"
        stored_data = load_data()
        pending = stored_data.get("pending_bookings", {}).get(pending_key)

        if not pending:
            return jsonify({
                "success": False,
                "error": "No pending booking found. Please start with BOOKED $amount email@paypal.com"
            })

        # Create the booking
        price = pending["price"]
        paypal = pending["paypal"]
        booking_id = add_booking(username, campaign, price, paypal)

        # Remove pending booking
        del stored_data["pending_bookings"][pending_key]
        save_data(stored_data)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] BOOKED complete: {username} - {campaign} - ${price} - {paypal}")

        return jsonify({
            "success": True,
            "booking_id": booking_id,
            "message": f"✓ {username} booked for {campaign} at ${price:.0f}. PayPal: {paypal}"
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/webhook/done', methods=['POST'])
def handle_done():
    """
    Creator marks their posts as done.

    Expected payload:
    {
        "username": "@creator123",
        "campaign": "xavier wulf" (optional - to match specific booking)
    }

    Returns:
    - found: true if we found their booking
    - booking info (campaign, price, paypal) for confirmation
    """
    try:
        data = request.json
        username = data.get("username", "").strip()
        campaign = data.get("campaign", "").strip()

        if not username:
            return jsonify({"success": False, "error": "No username provided"})

        # Find their booking
        booking = find_booking(username, campaign if campaign else None)

        if not booking:
            # No booking found
            return jsonify({
                "success": False,
                "found": False,
                "message": "I couldn't find an active booking for you. Please contact the campaign manager."
            })

        print(f"[{datetime.now().strftime('%H:%M:%S')}] DONE request: {username} - {booking['campaign']}")

        return jsonify({
            "success": True,
            "found": True,
            "booking_id": booking["id"],
            "campaign": booking["campaign"],
            "price": booking["price"],
            "paypal": booking["paypal"],
            "message": f"Found your booking for {booking['campaign']}! You'll receive ${booking['price']:.2f} to {booking['paypal']}. Is this PayPal still correct? Reply YES or send a different email."
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/webhook/confirm', methods=['POST'])
def handle_confirm():
    """
    Creator confirms their PayPal and we move to payment needed.

    Expected payload:
    {
        "username": "@creator123",
        "booking_id": "...",
        "paypal": "same" or "new@email.com" (if they want to change it)
    }
    """
    try:
        data = request.json
        username = data.get("username", "").strip()
        booking_id = data.get("booking_id", "").strip()
        paypal = data.get("paypal", "").strip()

        if not booking_id:
            return jsonify({"success": False, "error": "No booking ID provided"})

        # Update PayPal if they provided a new one
        if paypal and "@" in paypal and paypal.lower() != "same" and paypal.lower() != "yes":
            update_booking(booking_id, paypal=paypal)

        # Mark as payment needed
        update_booking(booking_id, status="payment_needed")

        # Get the updated booking
        data_store = load_data()
        booking = None
        for b in data_store["bookings"]:
            if b["id"] == booking_id:
                booking = b
                break

        print(f"[{datetime.now().strftime('%H:%M:%S')}] CONFIRMED: {username} - moving to payment needed")

        return jsonify({
            "success": True,
            "message": f"You're all set! ${booking['price']:.2f} will be sent to {booking['paypal']} within 2 business days.",
            "paypal": booking["paypal"],
            "price": booking["price"]
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


# =============================================================================
# DASHBOARD
# =============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Payment Tracker</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { margin: 0; padding: 20px; background: #f0f2f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 { color: #1a1a1a; margin-bottom: 5px; }
        .subtitle { color: #666; margin-bottom: 20px; }

        .stats { display: flex; gap: 15px; margin-bottom: 25px; flex-wrap: wrap; }
        .stat { background: white; padding: 15px 20px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); min-width: 120px; }
        .stat-value { font-size: 28px; font-weight: bold; color: #1a1a1a; }
        .stat-label { font-size: 12px; color: #666; text-transform: uppercase; }
        .stat.payment-needed { border-left: 4px solid #dc3545; }
        .stat.booked { border-left: 4px solid #ffc107; }
        .stat.paid { border-left: 4px solid #28a745; }

        .section { margin-bottom: 30px; }
        .section-title { font-size: 18px; font-weight: 600; margin-bottom: 15px; display: flex; align-items: center; gap: 10px; }
        .section-title .badge { background: #dc3545; color: white; padding: 2px 8px; border-radius: 10px; font-size: 14px; }
        .section-title.booked .badge { background: #ffc107; color: #000; }
        .section-title.paid .badge { background: #28a745; }

        .table-container { background: white; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden; }
        table { width: 100%; border-collapse: collapse; }
        th { background: #f8f9fa; padding: 12px 15px; text-align: left; font-size: 12px; text-transform: uppercase; color: #666; border-bottom: 1px solid #eee; }
        td { padding: 12px 15px; border-bottom: 1px solid #eee; }
        tr:hover { background: #f8f9fa; }

        .username { font-weight: 600; color: #0066cc; }
        .campaign { color: #333; }
        .price { font-weight: 600; color: #28a745; }
        .paypal { color: #0070ba; font-size: 13px; }
        .timestamp { color: #666; font-size: 13px; }

        .status { padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; display: inline-block; }
        .status.booked { background: #fff3cd; color: #856404; }
        .status.payment_needed { background: #f8d7da; color: #721c24; }
        .status.paid { background: #d4edda; color: #155724; }

        .actions { display: flex; gap: 5px; flex-wrap: wrap; }
        .btn { padding: 5px 10px; border: none; border-radius: 5px; cursor: pointer; font-size: 12px; white-space: nowrap; }
        .btn-paid { background: #28a745; color: white; }
        .btn-need-payment { background: #dc3545; color: white; }
        .btn-delete { background: #6c757d; color: white; }
        .btn:hover { opacity: 0.8; }

        .notes-input { width: 120px; padding: 5px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 13px; }
        .notes-input:focus { outline: none; border-color: #0066cc; }

        .empty { padding: 30px; text-align: center; color: #999; }

        .refresh-note { text-align: center; color: #999; font-size: 12px; margin-top: 20px; }

        .add-booking-form { background: white; padding: 15px 20px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 25px; }
        .form-title { font-weight: 600; margin-bottom: 10px; color: #333; }
        .form-row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
        .form-input { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }
        .form-input:focus { outline: none; border-color: #0066cc; }
        .form-input.wide { flex: 2; min-width: 200px; }
        .form-input.small { width: 70px; }
        .btn-add { background: #0066cc; color: white; padding: 8px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; }
        .btn-add:hover { background: #0052a3; }

        .tabs { display: flex; gap: 10px; margin-bottom: 20px; }
        .tab { padding: 10px 20px; background: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; }
        .tab.active { background: #0066cc; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Payment Tracker</h1>
        <p class="subtitle">Track creator bookings and payments</p>

        <div class="stats">
            <div class="stat payment-needed">
                <div class="stat-value">{{ payment_needed_count }}</div>
                <div class="stat-label">Payment Needed</div>
            </div>
            <div class="stat booked">
                <div class="stat-value">{{ booked_count }}</div>
                <div class="stat-label">Waiting for Posts</div>
            </div>
            <div class="stat paid">
                <div class="stat-value">{{ paid_count }}</div>
                <div class="stat-label">Paid</div>
            </div>
            <div class="stat">
                <div class="stat-value">${{ "%.2f"|format(total_owed) }}</div>
                <div class="stat-label">Total Owed</div>
            </div>
        </div>

        <!-- Quick Add Booking Form -->
        <div class="add-booking-form">
            <div class="form-title">+ Add Booking</div>
            <div class="form-row">
                <input type="text" id="new-username" placeholder="@username" class="form-input">
                <input type="text" id="new-campaign" placeholder="Campaign (Artist - Song)" class="form-input wide">
                <input type="text" id="new-price" placeholder="$50" class="form-input small">
                <input type="text" id="new-paypal" placeholder="paypal@email.com" class="form-input">
                <button class="btn btn-add" onclick="addBooking()">Add</button>
            </div>
        </div>

        <!-- Payment Needed Section -->
        <div class="section">
            <div class="section-title">
                Payment Needed <span class="badge">{{ payment_needed_count }}</span>
            </div>
            <div class="table-container">
                {% if payment_needed %}
                <table>
                    <thead>
                        <tr>
                            <th>Username</th>
                            <th>Campaign</th>
                            <th>Price</th>
                            <th>PayPal</th>
                            <th>Completed</th>
                            <th>Notes</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for b in payment_needed %}
                        <tr>
                            <td class="username">{{ b.username }}</td>
                            <td class="campaign">{{ b.campaign }}</td>
                            <td class="price">${{ "%.2f"|format(b.price) }}</td>
                            <td class="paypal">{{ b.paypal }}</td>
                            <td class="timestamp">{{ b.completed_at[:16].replace('T', ' ') if b.completed_at else '-' }}</td>
                            <td>
                                <input type="text" class="notes-input" value="{{ b.notes }}"
                                       onchange="updateNotes('{{ b.id }}', this.value)" placeholder="Add note...">
                            </td>
                            <td class="actions">
                                <button class="btn btn-paid" onclick="updateStatus('{{ b.id }}', 'paid')">Mark Paid</button>
                                <button class="btn btn-delete" onclick="deleteBooking('{{ b.id }}')">X</button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="empty">No payments needed right now</div>
                {% endif %}
            </div>
        </div>

        <!-- Booked Section -->
        <div class="section">
            <div class="section-title booked">
                Booked - Waiting for Posts <span class="badge">{{ booked_count }}</span>
            </div>
            <div class="table-container">
                {% if booked %}
                <table>
                    <thead>
                        <tr>
                            <th>Username</th>
                            <th>Campaign</th>
                            <th>Price</th>
                            <th>PayPal</th>
                            <th>Booked</th>
                            <th>Notes</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for b in booked %}
                        <tr>
                            <td class="username">{{ b.username }}</td>
                            <td class="campaign">{{ b.campaign }}</td>
                            <td class="price">${{ "%.2f"|format(b.price) }}</td>
                            <td class="paypal">{{ b.paypal }}</td>
                            <td class="timestamp">{{ b.booked_at[:16].replace('T', ' ') }}</td>
                            <td>
                                <input type="text" class="notes-input" value="{{ b.notes }}"
                                       onchange="updateNotes('{{ b.id }}', this.value)" placeholder="Add note...">
                            </td>
                            <td class="actions">
                                <button class="btn btn-need-payment" onclick="updateStatus('{{ b.id }}', 'payment_needed')">Posts Done</button>
                                <button class="btn btn-delete" onclick="deleteBooking('{{ b.id }}')">X</button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="empty">No active bookings</div>
                {% endif %}
            </div>
        </div>

        <!-- Paid Section (collapsed by default) -->
        <div class="section">
            <div class="section-title paid" style="cursor: pointer;" onclick="togglePaid()">
                Paid <span class="badge">{{ paid_count }}</span> <span id="paid-toggle" style="font-size: 12px; color: #666;">▼ Show</span>
            </div>
            <div class="table-container" id="paid-section" style="display: none;">
                {% if paid %}
                <table>
                    <thead>
                        <tr>
                            <th>Username</th>
                            <th>Campaign</th>
                            <th>Price</th>
                            <th>PayPal</th>
                            <th>Paid At</th>
                            <th>Notes</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for b in paid %}
                        <tr>
                            <td class="username">{{ b.username }}</td>
                            <td class="campaign">{{ b.campaign }}</td>
                            <td class="price">${{ "%.2f"|format(b.price) }}</td>
                            <td class="paypal">{{ b.paypal }}</td>
                            <td class="timestamp">{{ b.paid_at[:16].replace('T', ' ') if b.paid_at else '-' }}</td>
                            <td>{{ b.notes }}</td>
                            <td class="actions">
                                <button class="btn btn-delete" onclick="deleteBooking('{{ b.id }}')">X</button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="empty">No paid bookings yet</div>
                {% endif %}
            </div>
        </div>

        <p class="refresh-note">Page auto-refreshes every 30 seconds</p>
    </div>

    <script>
        setTimeout(() => location.reload(), 30000);

        function togglePaid() {
            const section = document.getElementById('paid-section');
            const toggle = document.getElementById('paid-toggle');
            if (section.style.display === 'none') {
                section.style.display = 'block';
                toggle.textContent = '▲ Hide';
            } else {
                section.style.display = 'none';
                toggle.textContent = '▼ Show';
            }
        }

        function updateStatus(id, status) {
            fetch('/api/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: id, status: status})
            }).then(() => location.reload());
        }

        function updateNotes(id, notes) {
            fetch('/api/update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: id, notes: notes})
            });
        }

        function deleteBooking(id) {
            if (confirm('Delete this booking?')) {
                fetch('/api/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id: id})
                }).then(() => location.reload());
            }
        }

        function addBooking() {
            const username = document.getElementById('new-username').value.trim();
            const campaign = document.getElementById('new-campaign').value.trim();
            const price = document.getElementById('new-price').value.trim();
            const paypal = document.getElementById('new-paypal').value.trim();

            if (!username || !campaign || !price || !paypal) {
                alert('Please fill in all fields');
                return;
            }

            fetch('/webhook/booked', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username, campaign, price, paypal})
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert(data.error || 'Error adding booking');
                }
            });
        }
    </script>
</body>
</html>
"""


@app.route('/', methods=['GET'])
@app.route('/dashboard', methods=['GET'])
def dashboard():
    """Main dashboard"""
    all_bookings = get_bookings()

    booked = [b for b in all_bookings if b["status"] == "booked"]
    payment_needed = [b for b in all_bookings if b["status"] == "payment_needed"]
    paid = [b for b in all_bookings if b["status"] == "paid"]

    # Calculate total owed (payment_needed)
    total_owed = sum(b["price"] for b in payment_needed)

    return render_template_string(
        DASHBOARD_HTML,
        booked=booked,
        payment_needed=payment_needed,
        paid=paid,
        booked_count=len(booked),
        payment_needed_count=len(payment_needed),
        paid_count=len(paid),
        total_owed=total_owed
    )


@app.route('/api/update', methods=['POST'])
def api_update():
    """Update a booking"""
    data = request.json
    booking_id = data.get("id")
    status = data.get("status")
    notes = data.get("notes")

    update_booking(booking_id, status=status, notes=notes)
    return jsonify({"success": True})


@app.route('/api/delete', methods=['POST'])
def api_delete():
    """Delete a booking"""
    data = request.json
    booking_id = data.get("id")
    delete_booking(booking_id)
    return jsonify({"success": True})


@app.route('/api/bookings', methods=['GET'])
def api_bookings():
    """Get all bookings as JSON"""
    return jsonify({"bookings": get_bookings()})


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 50)
    print("  PAYMENT TRACKER")
    print("=" * 50)
    print("""
    Dashboard: http://localhost:5050

    Webhooks for ManyChat:

    1. BOOKED (campaign manager types this):
       POST /webhook/booked
       Body: {
         "username": "@creator",
         "campaign": "Artist - Song",
         "price": "$50",
         "paypal": "creator@paypal.com"
       }

    2. DONE (creator types this):
       POST /webhook/done
       Body: {"username": "@creator", "campaign": "optional"}

    3. CONFIRM (creator confirms PayPal):
       POST /webhook/confirm
       Body: {"username": "@creator", "booking_id": "...", "paypal": "same or new@email.com"}

    To share dashboard:
      1. Run: ngrok http 5050
      2. Share the ngrok URL
    """)

    app.run(host='0.0.0.0', port=5050, debug=False)
