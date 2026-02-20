"""
Test sending a real invite - with debug output
"""

from cobrand_client import CobrandClient
import httpx
from datetime import datetime, timedelta

client = CobrandClient()

TEST_EMAIL = "jakebalik+test2@gmail.com"  # Using +test2 to test again
ACTIVATION_ID = "a3344c73-6771-4fd0-91ca-e72e73a35df5"

print("=" * 60)
print("  SENDING INVITE WITH DEBUG")
print("=" * 60)

# Direct API call to see full response
url = "https://api.cobrand.com/brand/v2/send_agency_upload_invite"
headers = {
    "Authorization": f"Bearer {client.bearer_token}",
    "Content-Type": "application/json"
}
expires_at = (datetime.now() + timedelta(days=30)).isoformat() + "Z"
body = {
    "activation_id": ACTIVATION_ID,
    "email_addresses": [TEST_EMAIL],
    "expires_at": expires_at
}

print(f"\nSending invite to: {TEST_EMAIL}")
print(f"Activation: {ACTIVATION_ID[:8]}...")

response = httpx.post(url, headers=headers, json=body, timeout=30)

print(f"\nStatus Code: {response.status_code}")
print(f"Response Headers: {dict(response.headers)}")
print(f"Response Body: {response.text}")

# Verify
print("\n--- Verifying ---")
invites = client.list_invites(ACTIVATION_ID)
for inv in invites:
    if TEST_EMAIL in inv.email:
        print(f"CONFIRMED: {inv.email}")
        print(f"  Token: {inv.token[:30]}...")
