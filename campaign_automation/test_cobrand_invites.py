"""
Cobrand Invite API Tester
=========================

Tests the newly discovered invite endpoints:
- send_agency_upload_invite
- list_agency_upload_invites

Run with: python test_cobrand_invites.py
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import httpx
from datetime import datetime, timedelta
import json

# =============================================================================
# CONFIGURATION
# =============================================================================

# Bearer token from browser (Auth0)
# NOTE: This token expires! Get a fresh one if requests fail with 401
BEARER_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImE1VklFSG5tSXJXV0RjRWdRWFFlbiJ9.eyJpc3MiOiJodHRwczovL2xvdWRseS1haS51cy5hdXRoMC5jb20vIiwic3ViIjoiYXV0aDB8Njg1MTdjMjUxYWNkZmQxODNlZGUwYzZhIiwiYXVkIjpbImh0dHBzOi8vbG91ZGx5LWFpLnVzLmF1dGgwIiwiaHR0cHM6Ly9sb3VkbHktYWkudXMuYXV0aDAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTc2ODkzMDM4MCwiZXhwIjoxNzY5MDE2NzgwLCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIiwiYXpwIjoiaTVpcUxUSEJDZDVBQkx6SzZUS0hOYmtUQWJuS0FqQTAifQ.m8SLOZdubHhfiM9rhlIILxwBbhISRvkVOoo5GBasHr4jRghfPVDUTYJrqshsP3hP5P2C8yZr0r471trTGxJxZ015u7ndt2m3epY6sYIvBmT8zWPuaDMV7Sqyw6nb3BAkUOXpzjzWk569F5iPfgl2ZNC_znXsVSZNIruwGjXgC8_Lbxoh9JCqbjaeF2xRj25cmf7FbF69-OgTPONs2mt4wLtIL2wdrBkbMTiaQiTRf1Ql91ZI_3Y2ZhQ_Kez2r4vA1f08-3bog-DRiZD0EP3gIAvD8ZMsnQY5KhbAY3mH1Equcjrdqnsy9dAaOsUiYnnp9JyAMhh7a_SwuvH7_r_MyA"

# Known activation ID from the browser discovery
ACTIVATION_ID = "a3344c73-6771-4fd0-91ca-e72e73a35df5"

# API Base URL
BASE_URL = "https://api.cobrand.com/brand/v2"


# =============================================================================
# API FUNCTIONS
# =============================================================================

def get_headers():
    """Standard headers for authenticated requests"""
    return {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "Content-Type": "application/json"
    }


def list_invites(activation_id: str) -> dict:
    """
    List all invites for a campaign/activation.

    This tells us who has been invited and potentially their status.
    """
    url = f"{BASE_URL}/list_agency_upload_invites"
    body = {"activation_id": activation_id}

    print(f"\n📋 Listing invites for activation: {activation_id[:8]}...")

    try:
        response = httpx.post(url, headers=get_headers(), json=body, timeout=30)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            print("   ❌ Unauthorized - Token may be expired!")
            print("   Get a fresh token from browser DevTools")
            return None
        else:
            print(f"   ❌ Error: {response.text[:500]}")
            return None

    except httpx.HTTPError as e:
        print(f"   ❌ Request failed: {e}")
        return None


def send_invite(activation_id: str, email: str, expires_days: int = 30) -> dict:
    """
    Send an invite to a creator.

    WARNING: This actually sends an email! Use test emails carefully.
    """
    url = f"{BASE_URL}/send_agency_upload_invite"

    # Calculate expiry date
    expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat() + "Z"

    body = {
        "activation_id": activation_id,
        "email_addresses": [email],
        "expires_at": expires_at
    }

    print(f"\n📧 Sending invite to: {email}")
    print(f"   Activation: {activation_id[:8]}...")
    print(f"   Expires: {expires_at}")

    try:
        response = httpx.post(url, headers=get_headers(), json=body, timeout=30)
        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ Invite sent successfully!")
            return response.json()
        elif response.status_code == 401:
            print("   ❌ Unauthorized - Token may be expired!")
            return None
        else:
            print(f"   ❌ Error: {response.text[:500]}")
            return None

    except httpx.HTTPError as e:
        print(f"   ❌ Request failed: {e}")
        return None


def decode_jwt(token: str) -> dict:
    """
    Decode a JWT token to see its contents (without verification).
    Helps understand token expiry and claims.
    """
    import base64

    try:
        # JWT has 3 parts: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {"error": "Invalid JWT format"}

        # Decode the payload (middle part)
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)

    except Exception as e:
        return {"error": str(e)}


def pretty_print(data):
    """Print JSON nicely"""
    print(json.dumps(data, indent=2, default=str))


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("  COBRAND INVITE API TESTER")
    print("=" * 60)

    # First, let's check the token
    print("\n" + "=" * 60)
    print("  TOKEN INFO")
    print("=" * 60)

    token_info = decode_jwt(BEARER_TOKEN)
    if "error" not in token_info:
        exp_timestamp = token_info.get("exp", 0)
        exp_date = datetime.fromtimestamp(exp_timestamp)
        now = datetime.now()

        print(f"\n🔑 Token Details:")
        print(f"   Issuer: {token_info.get('iss', 'unknown')}")
        print(f"   Expires: {exp_date}")
        print(f"   Time remaining: {exp_date - now}")

        if exp_date < now:
            print("\n   ⚠️  TOKEN IS EXPIRED! Get a fresh one from browser.")
            return
        else:
            print("\n   ✅ Token is still valid")
    else:
        print(f"   Could not decode token: {token_info['error']}")

    # Test 1: List existing invites
    print("\n" + "=" * 60)
    print("  TEST 1: List Existing Invites")
    print("=" * 60)

    invites = list_invites(ACTIVATION_ID)
    if invites:
        print("\n📋 Invites found:")
        pretty_print(invites)

    # Test 2: Send a test invite (COMMENTED OUT FOR SAFETY)
    print("\n" + "=" * 60)
    print("  TEST 2: Send Invite (DISABLED)")
    print("=" * 60)
    print("""
    To test sending an invite, uncomment the code below and use a test email.

    WARNING: This will actually send an email!

    # result = send_invite(ACTIVATION_ID, "your-test-email@example.com")
    # if result:
    #     pretty_print(result)
    """)

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print("""
    Endpoints confirmed:
    ✅ list_agency_upload_invites - List who's been invited
    ⏳ send_agency_upload_invite - Ready to test (uncomment above)

    Next steps:
    1. Test send_invite with a real email you control
    2. Discover how to get activation_id from promotion_id
    3. Build the automation pipeline
    """)


if __name__ == "__main__":
    main()
