"""
Test sending a real invite through the Cobrand API
"""

# Import client (which handles encoding fix)
from cobrand_client import CobrandClient

# Initialize client
client = CobrandClient()

# Test email
TEST_EMAIL = "jakebalik@gmail.com"

# Campaign to invite to (using Xavier Wulf as the test)
CAMPAIGN = "CrossCuttin"

print("=" * 60)
print("  SENDING REAL INVITE")
print("=" * 60)

# First, find the campaign
print(f"\n1. Finding campaign '{CAMPAIGN}'...")
campaign = client.find_campaign(CAMPAIGN)

if campaign:
    print(f"   Found: {campaign.name}")
    print(f"   Activation ID: {campaign.id}")
    print(f"   Artist: {campaign.artist_name}")

    # Send the invite
    print(f"\n2. Sending invite to {TEST_EMAIL}...")
    result = client.send_invite(campaign.id, TEST_EMAIL)

    if result:
        print(f"\n   SUCCESS! Invite sent.")
        print(f"\n   Check {TEST_EMAIL} for the Cobrand invite email!")
    else:
        print(f"\n   Failed to send invite.")

    # Verify by listing invites
    print(f"\n3. Verifying invite was created...")
    invites = client.list_invites(campaign.id)

    for inv in invites:
        if inv.email == TEST_EMAIL:
            print(f"   CONFIRMED: Found invite for {TEST_EMAIL}")
            print(f"   Token: {inv.token[:20]}...")
            print(f"   Expires: {inv.expires_at}")
            break
    else:
        print(f"   Note: Invite not yet visible in list (may take a moment)")

else:
    print(f"   ERROR: Could not find campaign '{CAMPAIGN}'")
