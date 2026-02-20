"""
Campaign Automation Webhook Server
==================================

Receives webhooks from ManyChat, processes creator registrations,
and sends Cobrand invites automatically.

Run with: python webhook_server.py
Then use ngrok to expose: ngrok http 5050

Endpoints:
  POST /webhook/register - Creator registration (campaign + email)
  POST /webhook/payment  - Payment info collection (PayPal email)
  GET  /health           - Health check
  GET  /campaigns        - List available campaigns
"""

from flask import Flask, request, jsonify
from cobrand_client import CobrandClient
import re
from datetime import datetime

app = Flask(__name__)

# Initialize Cobrand client
client = CobrandClient()

# Simple in-memory store for tracking (in production, use a database)
registrations = {}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def extract_email(text: str) -> str | None:
    """Extract email address from text"""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    match = re.search(email_pattern, text)
    return match.group(0) if match else None


def extract_campaign_keyword(text: str, known_campaigns: list) -> str | None:
    """
    Extract campaign keyword from text.
    Matches against known campaign names/keywords.
    """
    text_lower = text.lower().replace(" ", "").replace('"', '').replace("'", "")

    for campaign_name in known_campaigns:
        # Create variations to match against
        keyword = campaign_name.lower().replace(" ", "").replace('"', '').replace("'", "")

        if keyword in text_lower:
            return campaign_name

        # Also try matching just the main part (e.g., "CrossCuttin" from "Xavier Wulf Cross Cuttin R1")
        parts = campaign_name.replace('"', '').split()
        for part in parts:
            if len(part) > 4 and part.lower() in text_lower:
                return campaign_name

    return None


def log(message: str):
    """Simple logging with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


# =============================================================================
# WEBHOOK ENDPOINTS
# =============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/campaigns', methods=['GET'])
def list_campaigns():
    """List available campaigns (for debugging/reference)"""
    try:
        campaigns = client.list_all_campaigns()
        # Get unique campaigns (avoid duplicates from keyword indexing)
        seen_ids = set()
        unique_campaigns = []
        for name, activation in campaigns.items():
            if activation.id not in seen_ids:
                seen_ids.add(activation.id)
                unique_campaigns.append({
                    "name": activation.name,
                    "id": activation.id,
                    "artist": activation.artist_name,
                    "keyword": activation.keyword
                })

        return jsonify({
            "count": len(unique_campaigns),
            "campaigns": unique_campaigns
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/webhook/register', methods=['POST'])
def register_creator():
    """
    Handle creator registration from ManyChat.

    Expected payload from ManyChat:
    {
        "message": "CrossCuttin creator@email.com",
        "subscriber_id": "12345",
        "tiktok_username": "@creator123",
        ...
    }

    Or simpler:
    {
        "campaign": "CrossCuttin",
        "email": "creator@email.com",
        "subscriber_id": "12345"
    }
    """
    try:
        data = request.json
        log(f"Received registration webhook: {data}")

        # Extract campaign and email
        # Support both structured and message-based formats
        campaign_keyword = data.get('campaign')
        email = data.get('email')
        subscriber_id = data.get('subscriber_id', 'unknown')
        tiktok_username = data.get('tiktok_username', '')

        # If not structured, try to parse from message
        if not campaign_keyword or not email:
            message = data.get('message', '')

            if not email:
                email = extract_email(message)

            if not campaign_keyword:
                # Get list of campaign names to match against
                campaigns = client.list_all_campaigns()
                campaign_names = list(set(a.name for a in campaigns.values()))
                campaign_keyword = extract_campaign_keyword(message, campaign_names)

        # Validate we have what we need
        if not email:
            log(f"ERROR: No email found in request")
            return jsonify({
                "success": False,
                "error": "no_email",
                "message": "Could not find email address. Please include your email."
            }), 400

        if not campaign_keyword:
            log(f"ERROR: No campaign keyword found in request")
            return jsonify({
                "success": False,
                "error": "no_campaign",
                "message": "Could not identify campaign. Please include the campaign name."
            }), 400

        # Find the campaign
        campaign = client.find_campaign(campaign_keyword)
        if not campaign:
            log(f"ERROR: Campaign not found: {campaign_keyword}")
            return jsonify({
                "success": False,
                "error": "campaign_not_found",
                "message": f"Campaign '{campaign_keyword}' not found."
            }), 404

        # Send the invite
        log(f"Sending invite: {email} -> {campaign.name}")
        result = client.send_invite(campaign.id, email)

        if result:
            # Store registration
            registrations[email] = {
                "campaign": campaign.name,
                "activation_id": campaign.id,
                "subscriber_id": subscriber_id,
                "tiktok_username": tiktok_username,
                "registered_at": datetime.now().isoformat(),
                "status": "invited"
            }

            log(f"SUCCESS: Invite sent to {email} for {campaign.name}")

            return jsonify({
                "success": True,
                "message": f"You're registered for {campaign.name}! Check your email for the upload link.",
                "campaign_name": campaign.name,
                "artist": campaign.artist_name
            })
        else:
            log(f"ERROR: Failed to send invite")
            return jsonify({
                "success": False,
                "error": "invite_failed",
                "message": "Failed to send invite. Please try again."
            }), 500

    except Exception as e:
        log(f"ERROR: {str(e)}")
        return jsonify({
            "success": False,
            "error": "server_error",
            "message": str(e)
        }), 500


@app.route('/webhook/payment', methods=['POST'])
def collect_payment():
    """
    Handle PayPal email collection from ManyChat.

    Expected payload:
    {
        "paypal_email": "creator@paypal.com",
        "subscriber_id": "12345",
        "campaign": "CrossCuttin"  (optional)
    }
    """
    try:
        data = request.json
        log(f"Received payment webhook: {data}")

        paypal_email = data.get('paypal_email')
        subscriber_id = data.get('subscriber_id', 'unknown')
        creator_email = data.get('email', '')

        if not paypal_email:
            return jsonify({
                "success": False,
                "error": "no_paypal",
                "message": "Please provide your PayPal email."
            }), 400

        # Find existing registration
        registration = None
        for email, reg in registrations.items():
            if reg.get('subscriber_id') == subscriber_id:
                registration = reg
                creator_email = email
                break

        if registration:
            registration['paypal_email'] = paypal_email
            registration['payment_status'] = 'pending'
            registration['payment_submitted_at'] = datetime.now().isoformat()

            log(f"SUCCESS: PayPal collected for {creator_email}: {paypal_email}")

            return jsonify({
                "success": True,
                "message": f"Got it! We'll send payment to {paypal_email}. Payments are processed weekly.",
                "paypal_email": paypal_email
            })
        else:
            # Store anyway even without matching registration
            log(f"Payment info received (no matching registration): {paypal_email}")
            return jsonify({
                "success": True,
                "message": f"Got it! We'll send payment to {paypal_email}.",
                "paypal_email": paypal_email,
                "note": "No matching registration found"
            })

    except Exception as e:
        log(f"ERROR: {str(e)}")
        return jsonify({
            "success": False,
            "error": "server_error",
            "message": str(e)
        }), 500


@app.route('/webhook/check-completion', methods=['POST'])
def check_completion():
    """
    Check if a creator has completed their submissions.

    Expected payload:
    {
        "email": "creator@email.com",
        "campaign": "CrossCuttin",
        "required_posts": 5
    }
    """
    try:
        data = request.json
        email = data.get('email')
        campaign_keyword = data.get('campaign')
        required_posts = data.get('required_posts', 1)

        if not email or not campaign_keyword:
            return jsonify({
                "success": False,
                "error": "missing_params"
            }), 400

        # Find campaign
        campaign = client.find_campaign(campaign_keyword)
        if not campaign:
            return jsonify({
                "success": False,
                "error": "campaign_not_found"
            }), 404

        # List invites and find this creator
        invites = client.list_invites(campaign.id)
        for invite in invites:
            if invite.email.lower() == email.lower():
                is_complete = invite.submission_count >= required_posts

                return jsonify({
                    "success": True,
                    "email": email,
                    "campaign": campaign.name,
                    "submissions": invite.submission_count,
                    "required": required_posts,
                    "is_complete": is_complete,
                    "message": "Complete!" if is_complete else f"Need {required_posts - invite.submission_count} more posts"
                })

        return jsonify({
            "success": False,
            "error": "invite_not_found",
            "message": f"No invite found for {email} in {campaign.name}"
        }), 404

    except Exception as e:
        log(f"ERROR: {str(e)}")
        return jsonify({
            "success": False,
            "error": "server_error",
            "message": str(e)
        }), 500


@app.route('/registrations', methods=['GET'])
def get_registrations():
    """View all registrations (for debugging)"""
    return jsonify(registrations)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  CAMPAIGN AUTOMATION WEBHOOK SERVER")
    print("=" * 60)
    print("""
    Endpoints:
      POST /webhook/register    - Creator registration
      POST /webhook/payment     - PayPal collection
      POST /webhook/check-completion - Check submission status
      GET  /campaigns           - List available campaigns
      GET  /registrations       - View registrations (debug)
      GET  /health              - Health check

    To expose to internet:
      1. Install ngrok: https://ngrok.com/download
      2. Run: ngrok http 5050
      3. Use the https URL in ManyChat

    """)

    app.run(host='0.0.0.0', port=5050, debug=True)
