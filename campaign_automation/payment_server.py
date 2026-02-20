"""
Payment Automation Server
=========================

Handles:
- Creator completion verification ("DONE" messages)
- PayPal email collection and storage
- Payment queue management
- Dashboard for batch payments

Run with: python payment_server.py
"""

from flask import Flask, request, jsonify, render_template_string
from cobrand_client import CobrandClient
import json
import os
import re
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

# Initialize Cobrand client
client = CobrandClient()

# Data storage file (simple JSON for now)
DATA_FILE = Path(__file__).parent / "payment_data.json"


# =============================================================================
# DATA STORAGE
# =============================================================================

def load_data():
    """Load stored data (creators, payments, etc.)"""
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        "creators": {},  # email -> {paypal, tiktok_username, last_updated}
        "payment_queue": [],  # List of pending payments
        "payment_history": []  # Completed payments
    }


def save_data(data):
    """Save data to file"""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def get_creator(email: str) -> dict | None:
    """Get stored creator info by email"""
    data = load_data()
    return data["creators"].get(email.lower())


def save_creator(email: str, paypal: str = None, tiktok: str = None):
    """Save or update creator info"""
    data = load_data()
    email_lower = email.lower()

    if email_lower not in data["creators"]:
        data["creators"][email_lower] = {}

    if paypal:
        data["creators"][email_lower]["paypal"] = paypal
    if tiktok:
        data["creators"][email_lower]["tiktok_username"] = tiktok

    data["creators"][email_lower]["last_updated"] = datetime.now().isoformat()
    save_data(data)


def add_to_payment_queue(email: str, campaign: str, amount: float, paypal: str, tiktok: str = ""):
    """Add a creator to the payment queue"""
    data = load_data()

    # Check if already in queue
    for item in data["payment_queue"]:
        if item["email"] == email.lower() and item["campaign"] == campaign:
            return False  # Already queued

    data["payment_queue"].append({
        "id": f"{email.lower()}_{campaign}_{datetime.now().timestamp()}",
        "email": email.lower(),
        "campaign": campaign,
        "amount": amount,
        "paypal": paypal,
        "tiktok_username": tiktok,
        "added_at": datetime.now().isoformat(),
        "status": "pending"
    })
    save_data(data)
    return True


def get_payment_queue():
    """Get all pending payments"""
    data = load_data()
    return [p for p in data["payment_queue"] if p["status"] == "pending"]


def mark_as_paid(payment_ids: list):
    """Mark payments as completed"""
    data = load_data()

    for payment in data["payment_queue"]:
        if payment["id"] in payment_ids:
            payment["status"] = "paid"
            payment["paid_at"] = datetime.now().isoformat()
            data["payment_history"].append(payment)

    # Remove paid items from queue
    data["payment_queue"] = [p for p in data["payment_queue"] if p["status"] == "pending"]
    save_data(data)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_email(text: str) -> str | None:
    """Extract email from text"""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(pattern, text)
    return match.group(0) if match else None


def extract_campaign_keyword(text: str) -> str | None:
    """Try to extract campaign keyword from text"""
    # Get all campaigns
    campaigns = client.list_all_campaigns()
    text_lower = text.lower().replace('"', '').replace("'", "")
    text_no_spaces = text_lower.replace(" ", "")

    # Try to match against known campaigns
    # Use a scoring approach - longer matches are better
    best_match = None
    best_score = 0

    for name, activation in campaigns.items():
        keyword = activation.keyword.lower()
        artist = activation.artist_name.lower()

        # Check keyword match (require at least 4 chars)
        if len(keyword) >= 4 and keyword in text_no_spaces:
            score = len(keyword)
            if score > best_score:
                best_score = score
                best_match = activation.name

        # Check artist name match (require at least 4 chars and word boundary)
        if len(artist) >= 4:
            # Check if artist name appears as a whole word (with word boundaries)
            pattern = r'\b' + re.escape(artist) + r'\b'
            if re.search(pattern, text_lower):
                score = len(artist) + 10  # Boost artist matches
                if score > best_score:
                    best_score = score
                    best_match = activation.name

    return best_match


def find_creator_in_campaign(email: str, campaign_name: str) -> dict | None:
    """
    Check if a creator is in a specific campaign and get their status.
    Returns invite info if found.
    """
    campaign = client.find_campaign(campaign_name)
    if not campaign:
        return None

    invites = client.list_invites(campaign.id)
    for invite in invites:
        if invite.email.lower() == email.lower():
            return {
                "found": True,
                "email": invite.email,
                "campaign": campaign.name,
                "activation_id": campaign.id,
                "submissions": invite.submission_count,
                "budget": campaign.budget,
                "artist": campaign.artist_name
            }

    return None


def log(message: str):
    """Simple logging"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


@app.route('/webhook/done', methods=['POST'])
def handle_done():
    """
    Handle "DONE" messages from creators.

    Expected payload:
    {
        "message": "DONE CrossCuttin",
        "email": "creator@email.com",  // Their Cobrand email
        "subscriber_id": "12345",
        "tiktok_username": "@creator"
    }

    Response:
    {
        "success": true,
        "needs_campaign": false,  // True if we need to ask which campaign
        "needs_paypal": false,    // True if we need PayPal
        "stored_paypal": "xxx@paypal.com",  // If we have it stored
        "message": "Response to send to creator",
        "amount_owed": 50.00,
        "campaign": "CrossCuttin"
    }
    """
    try:
        data = request.json
        log(f"Received DONE webhook: {data}")

        message = data.get("message", "")
        creator_email = data.get("email", "")
        tiktok_username = data.get("tiktok_username", "")
        subscriber_id = data.get("subscriber_id", "")

        # Try to extract campaign from message
        campaign_name = extract_campaign_keyword(message)

        # If no campaign found, ask which one
        if not campaign_name:
            return jsonify({
                "success": True,
                "needs_campaign": True,
                "message": "Which campaign are you done with? Please include the campaign or artist name."
            })

        # If no email provided, we need it
        if not creator_email:
            return jsonify({
                "success": True,
                "needs_email": True,
                "message": f"Got it! Please send your email address (the one you used to sign up for {campaign_name})."
            })

        # Find creator in campaign
        creator_info = find_creator_in_campaign(creator_email, campaign_name)

        if not creator_info:
            return jsonify({
                "success": False,
                "error": "not_found",
                "message": f"I couldn't find {creator_email} in the {campaign_name} campaign. Make sure you're using the same email you signed up with."
            })

        # Check if they've actually submitted posts
        submissions = creator_info["submissions"]
        if submissions == 0:
            return jsonify({
                "success": False,
                "error": "no_submissions",
                "message": f"It looks like you haven't uploaded any posts for {campaign_name} yet. Please upload your content through the Cobrand link first!"
            })

        # Calculate payment (this might need adjustment based on your payment structure)
        # For now, assuming fixed amount per campaign
        amount_owed = 50.00  # Default - you'll want to configure this per campaign

        # Check if we have their PayPal stored
        stored_creator = get_creator(creator_email)
        stored_paypal = stored_creator.get("paypal") if stored_creator else None

        # Save/update creator info
        save_creator(creator_email, tiktok=tiktok_username)

        if stored_paypal:
            return jsonify({
                "success": True,
                "needs_campaign": False,
                "needs_paypal": False,
                "confirm_paypal": True,
                "stored_paypal": stored_paypal,
                "amount_owed": amount_owed,
                "submissions": submissions,
                "campaign": campaign_name,
                "message": f"You completed {submissions} post(s) for {campaign_name}. You're owed ${amount_owed:.2f}.\n\nIs your PayPal still {stored_paypal}?\n\nReply YES to confirm or send your new PayPal email."
            })
        else:
            return jsonify({
                "success": True,
                "needs_campaign": False,
                "needs_paypal": True,
                "amount_owed": amount_owed,
                "submissions": submissions,
                "campaign": campaign_name,
                "message": f"You completed {submissions} post(s) for {campaign_name}. You're owed ${amount_owed:.2f}.\n\nPlease send your PayPal email to receive payment."
            })

    except Exception as e:
        log(f"ERROR in /webhook/done: {str(e)}")
        return jsonify({
            "success": False,
            "error": "server_error",
            "message": "Something went wrong. Please try again."
        }), 500


@app.route('/webhook/paypal', methods=['POST'])
def handle_paypal():
    """
    Handle PayPal email submission.

    Expected payload:
    {
        "message": "yes" or "myemail@paypal.com",
        "email": "creator@cobrand.com",
        "campaign": "CrossCuttin",
        "amount": 50.00,
        "stored_paypal": "old@paypal.com"  // If confirming existing
    }
    """
    try:
        data = request.json
        log(f"Received PayPal webhook: {data}")

        message = data.get("message", "").strip().lower()
        creator_email = data.get("email", "")
        campaign = data.get("campaign", "")
        amount = data.get("amount", 50.00)
        stored_paypal = data.get("stored_paypal", "")
        tiktok_username = data.get("tiktok_username", "")

        # Check if confirming existing PayPal
        if message in ["yes", "y", "yeah", "yep", "correct", "confirmed"]:
            paypal_email = stored_paypal
        else:
            # Try to extract email from message
            paypal_email = extract_email(message)
            if not paypal_email:
                return jsonify({
                    "success": False,
                    "error": "invalid_email",
                    "message": "That doesn't look like a valid email. Please send your PayPal email address."
                })

        # Save PayPal for future use
        save_creator(creator_email, paypal=paypal_email, tiktok=tiktok_username)

        # Add to payment queue
        added = add_to_payment_queue(
            email=creator_email,
            campaign=campaign,
            amount=amount,
            paypal=paypal_email,
            tiktok=tiktok_username
        )

        if added:
            return jsonify({
                "success": True,
                "message": f"Got it! ${amount:.2f} will be sent to {paypal_email}.\n\nPayments are processed weekly. You'll receive a notification when it's sent.\n\nThanks for being part of {campaign}! 🎉",
                "paypal": paypal_email,
                "amount": amount,
                "campaign": campaign
            })
        else:
            return jsonify({
                "success": True,
                "message": f"You're already in the payment queue for {campaign}. Payment will be processed soon!",
                "already_queued": True
            })

    except Exception as e:
        log(f"ERROR in /webhook/paypal: {str(e)}")
        return jsonify({
            "success": False,
            "error": "server_error",
            "message": "Something went wrong. Please try again."
        }), 500


# =============================================================================
# DASHBOARD
# =============================================================================

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Payment Dashboard</title>
    <style>
        * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        body { margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1000px; margin: 0 auto; }
        h1 { color: #333; }
        .stats { display: flex; gap: 20px; margin-bottom: 20px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; }
        .stat-card h3 { margin: 0 0 10px 0; color: #666; font-size: 14px; }
        .stat-card .value { font-size: 32px; font-weight: bold; color: #333; }
        .payment-list { background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .payment-header { padding: 15px 20px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .payment-item { padding: 15px 20px; border-bottom: 1px solid #eee; display: flex; align-items: center; gap: 15px; }
        .payment-item:last-child { border-bottom: none; }
        .payment-item input[type="checkbox"] { width: 20px; height: 20px; }
        .payment-item .info { flex: 1; }
        .payment-item .campaign { font-weight: bold; color: #333; }
        .payment-item .email { color: #666; font-size: 14px; }
        .payment-item .paypal { color: #0070ba; font-size: 14px; }
        .payment-item .amount { font-weight: bold; font-size: 18px; color: #22c55e; }
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: bold; }
        .btn-primary { background: #0070ba; color: white; }
        .btn-primary:hover { background: #005ea6; }
        .btn-primary:disabled { background: #ccc; cursor: not-allowed; }
        .btn-danger { background: #ef4444; color: white; }
        .select-all { display: flex; align-items: center; gap: 10px; }
        .empty { padding: 40px; text-align: center; color: #666; }
        .total { font-size: 24px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>💰 Payment Dashboard</h1>

        <div class="stats">
            <div class="stat-card">
                <h3>Pending Payments</h3>
                <div class="value" id="pending-count">{{ pending_count }}</div>
            </div>
            <div class="stat-card">
                <h3>Total to Pay</h3>
                <div class="value">${{ "%.2f"|format(total_amount) }}</div>
            </div>
            <div class="stat-card">
                <h3>Paid This Month</h3>
                <div class="value">{{ paid_count }}</div>
            </div>
        </div>

        <div class="payment-list">
            <div class="payment-header">
                <div class="select-all">
                    <input type="checkbox" id="select-all" onchange="toggleAll()">
                    <label for="select-all">Select All</label>
                </div>
                <div>
                    <span class="total">Selected: $<span id="selected-total">0.00</span></span>
                    <button class="btn btn-primary" id="pay-btn" onclick="paySelected()" disabled>
                        Pay Selected
                    </button>
                </div>
            </div>

            {% if payments %}
                {% for payment in payments %}
                <div class="payment-item">
                    <input type="checkbox" class="payment-checkbox"
                           data-id="{{ payment.id }}"
                           data-amount="{{ payment.amount }}"
                           onchange="updateTotal()">
                    <div class="info">
                        <div class="campaign">{{ payment.campaign }}</div>
                        <div class="email">{{ payment.email }} {% if payment.tiktok_username %}({{ payment.tiktok_username }}){% endif %}</div>
                        <div class="paypal">PayPal: {{ payment.paypal }}</div>
                    </div>
                    <div class="amount">${{ "%.2f"|format(payment.amount) }}</div>
                </div>
                {% endfor %}
            {% else %}
                <div class="empty">
                    <p>🎉 No pending payments!</p>
                    <p>When creators complete campaigns, they'll appear here.</p>
                </div>
            {% endif %}
        </div>
    </div>

    <script>
        function toggleAll() {
            const selectAll = document.getElementById('select-all');
            const checkboxes = document.querySelectorAll('.payment-checkbox');
            checkboxes.forEach(cb => cb.checked = selectAll.checked);
            updateTotal();
        }

        function updateTotal() {
            const checkboxes = document.querySelectorAll('.payment-checkbox:checked');
            let total = 0;
            checkboxes.forEach(cb => {
                total += parseFloat(cb.dataset.amount);
            });
            document.getElementById('selected-total').textContent = total.toFixed(2);
            document.getElementById('pay-btn').disabled = checkboxes.length === 0;
        }

        function paySelected() {
            const checkboxes = document.querySelectorAll('.payment-checkbox:checked');
            const ids = Array.from(checkboxes).map(cb => cb.dataset.id);

            if (ids.length === 0) return;

            if (!confirm(`Mark ${ids.length} payment(s) as paid?`)) return;

            fetch('/api/mark-paid', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({payment_ids: ids})
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Error: ' + data.error);
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
    """Payment dashboard"""
    payments = get_payment_queue()
    data = load_data()

    total_amount = sum(p["amount"] for p in payments)
    paid_count = len(data.get("payment_history", []))

    return render_template_string(
        DASHBOARD_HTML,
        payments=payments,
        pending_count=len(payments),
        total_amount=total_amount,
        paid_count=paid_count
    )


@app.route('/api/mark-paid', methods=['POST'])
def api_mark_paid():
    """Mark payments as paid"""
    try:
        data = request.json
        payment_ids = data.get("payment_ids", [])

        if not payment_ids:
            return jsonify({"success": False, "error": "No payments selected"})

        mark_as_paid(payment_ids)

        return jsonify({
            "success": True,
            "message": f"Marked {len(payment_ids)} payment(s) as paid"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/queue', methods=['GET'])
def api_queue():
    """Get payment queue as JSON"""
    return jsonify({
        "success": True,
        "payments": get_payment_queue()
    })


@app.route('/api/creators', methods=['GET'])
def api_creators():
    """Get all stored creators"""
    data = load_data()
    return jsonify({
        "success": True,
        "creators": data.get("creators", {})
    })


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  PAYMENT AUTOMATION SERVER")
    print("=" * 60)
    print("""
    Endpoints:
      POST /webhook/done     - Handle "DONE" messages
      POST /webhook/paypal   - Collect PayPal email
      GET  /dashboard        - Payment dashboard UI
      GET  /api/queue        - Get payment queue (JSON)
      GET  /api/creators     - Get stored creators (JSON)

    Dashboard: http://localhost:5050/dashboard
    """)

    app.run(host='0.0.0.0', port=5050, debug=False)
