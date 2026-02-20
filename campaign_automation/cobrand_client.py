"""
Cobrand API Client
==================

A complete client for automating Cobrand campaign management.

Features:
- List all promotions/campaigns
- Get campaign details and activation IDs
- Send creator invites
- Track invite status and submissions

Usage:
    from cobrand_client import CobrandClient

    client = CobrandClient(bearer_token="your_token")

    # List all campaigns
    campaigns = client.list_all_campaigns()

    # Send invite
    client.send_invite("CrossCuttin", "creator@email.com")
"""

import sys
import io

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import httpx
from datetime import datetime, timedelta
import json
from typing import Optional, List, Dict
from dataclasses import dataclass


# =============================================================================
# CONFIGURATION
# =============================================================================

# Your organization ID (found from browser)
ORGANIZATION_ID = "652c1528-f525-4c80-be5d-fda2aa6005fd"

# Bearer token - UPDATE THIS when it expires!
# Get from Chrome DevTools → Network → any api.cobrand.com request → Headers → Authorization
BEARER_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImE1VklFSG5tSXJXV0RjRWdRWFFlbiJ9.eyJpc3MiOiJodHRwczovL2xvdWRseS1haS51cy5hdXRoMC5jb20vIiwic3ViIjoiYXV0aDB8Njg1MTdjMjUxYWNkZmQxODNlZGUwYzZhIiwiYXVkIjpbImh0dHBzOi8vbG91ZGx5LWFpLnVzLmF1dGgwIiwiaHR0cHM6Ly9sb3VkbHktYWkudXMuYXV0aDAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTc3MDQyMDY2NSwiZXhwIjoxNzcwNTA3MDY1LCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIiwiYXpwIjoiaTVpcUxUSEJDZDVBQkx6SzZUS0hOYmtUQWJuS0FqQTAifQ.km-ScUC0Iy883vxgWljSjKmvx5zCgtkWyWenjZMXvrAEVBulLabPiN1oNz0WVBhN0hk1D1Gf3zkvHt0vZaR_ID8fMTd4WL5ZgDQfT0OFwitJO-FjiWFvKO5Rxpdi9LMdKvjC4whx8Gx-1uSS-NZc6w8wsYZFO6EfwplYAMAT7ng3w2uvD1xCtiBxno5tOZIAIbVUIocbw6eGtQsx9klnPSpPCDrW8blvoBNu4sTXj0XumkgXaIhT9uUbdfzXrt-BcemT0QabYSz_cduOVR7FVSzmE7No6cUjWRMyKaZGMBHE60SLmDb-6EQMXvvNu6h3wvy4_WPQiz0oKNjj4-zw-g"

# API Base URL
BASE_URL = "https://api.cobrand.com/brand/v2"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Activation:
    """Represents a campaign activation (the actual campaign creators join)"""
    id: str
    name: str
    status: str
    artist_name: str = ""
    budget: float = 0
    budget_currency: str = "USD"
    promotion_id: str = ""

    @property
    def keyword(self) -> str:
        """Generate a simple keyword from the name for DM matching"""
        # Remove special chars and spaces for a simple keyword
        return self.name.replace('"', '').replace("'", "").replace(" ", "").lower()


@dataclass
class Invite:
    """Represents a creator invite"""
    id: str
    email: str
    token: str
    expires_at: str
    created_at: str
    submission_count: int
    activation_id: str
    activation_name: str


# =============================================================================
# COBRAND CLIENT
# =============================================================================

class CobrandClient:
    """
    Client for interacting with Cobrand API.

    Handles:
    - Authentication
    - Listing campaigns
    - Sending invites
    - Tracking submissions
    """

    def __init__(self, bearer_token: str = BEARER_TOKEN, organization_id: str = ORGANIZATION_ID):
        self.bearer_token = bearer_token
        self.organization_id = organization_id
        self.base_url = BASE_URL

        # Cache for campaigns (to avoid repeated API calls)
        self._campaigns_cache: Dict[str, Activation] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(minutes=30)

    def _get_headers(self) -> dict:
        """Standard headers for authenticated requests"""
        return {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json"
        }

    def _post(self, endpoint: str, body: dict, return_success_on_null: bool = False) -> Optional[dict]:
        """Make a POST request to the API"""
        url = f"{self.base_url}/{endpoint}"

        try:
            response = httpx.post(
                url,
                headers=self._get_headers(),
                json=body,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                # Some endpoints return null on success (like send_invite)
                if result is None and return_success_on_null:
                    return {"success": True}
                return result
            elif response.status_code == 401:
                print(f"ERROR: Unauthorized - Token may be expired!")
                print(f"Get a fresh token from Chrome DevTools")
                return None
            else:
                print(f"ERROR: {response.status_code} - {response.text[:500]}")
                return None

        except httpx.HTTPError as e:
            print(f"ERROR: Request failed - {e}")
            return None

    # =========================================================================
    # CAMPAIGN LISTING
    # =========================================================================

    def list_promotions(self) -> List[dict]:
        """
        List all promotions (top-level campaign groups).

        Returns raw API response for promotions.
        """
        result = self._post("list_promotions_v3", {
            "organization_id": self.organization_id
        })

        if result:
            # Response has "items" array containing promotions
            return result.get("items", [])
        return []

    def get_promotion(self, promotion_id: str) -> Optional[dict]:
        """
        Get details for a specific promotion, including its activations.
        """
        return self._post("get_promotion", {
            "promotion_id": promotion_id
        })

    def get_activation(self, activation_id: str) -> Optional[dict]:
        """
        Get details for a specific activation.
        """
        return self._post("get_activation", {
            "activation_id": activation_id
        })

    def list_all_campaigns(self, force_refresh: bool = False) -> Dict[str, Activation]:
        """
        List all campaigns with their activation IDs.

        Returns a dict mapping campaign names to Activation objects.
        Uses caching to avoid repeated API calls.

        Example:
            campaigns = client.list_all_campaigns()
            for name, activation in campaigns.items():
                print(f"{name}: {activation.id}")
        """
        # Check cache
        if not force_refresh and self._campaigns_cache and self._cache_timestamp:
            if datetime.now() - self._cache_timestamp < self._cache_ttl:
                return self._campaigns_cache

        print("Fetching all campaigns from Cobrand...")
        campaigns = {}

        # Get all promotions
        promotions = self.list_promotions()
        print(f"Found {len(promotions)} promotions")

        for promo in promotions:
            promo_id = promo.get("id")
            promo_name = promo.get("name", "")
            promo_status = promo.get("status", "")

            if not promo_id:
                continue

            # Get promotion details (includes activations)
            promo_details = self.get_promotion(promo_id)
            if not promo_details:
                continue

            # Extract activations
            activations = promo_details.get("activations", [])
            for act in activations:
                artist_info = act.get("artist", {})
                artist_name = artist_info.get("name", "") if isinstance(artist_info, dict) else ""

                activation = Activation(
                    id=act.get("id", ""),
                    name=act.get("name", ""),
                    status=promo_status,
                    artist_name=artist_name,
                    budget=act.get("budget", 0),
                    budget_currency=act.get("budget_currency", "USD"),
                    promotion_id=promo_id
                )

                # Store by full name
                campaigns[activation.name] = activation

                # Also store by simplified keyword for easy lookup
                campaigns[activation.keyword] = activation

                # Also store by artist name for convenience
                if artist_name:
                    campaigns[artist_name.lower()] = activation

        # Update cache
        self._campaigns_cache = campaigns
        self._cache_timestamp = datetime.now()

        print(f"Found {len(campaigns)} total activations")
        return campaigns

    def find_campaign(self, query: str) -> Optional[Activation]:
        """
        Find a campaign by name or keyword.

        Searches for partial matches in campaign names.

        Example:
            campaign = client.find_campaign("CrossCuttin")
            if campaign:
                print(f"Found: {campaign.name} ({campaign.id})")
        """
        campaigns = self.list_all_campaigns()
        query_lower = query.lower().replace(" ", "").replace('"', '').replace("'", "")

        # Try exact match first
        if query in campaigns:
            return campaigns[query]
        if query_lower in campaigns:
            return campaigns[query_lower]

        # Try partial match
        for name, activation in campaigns.items():
            if query_lower in name.lower().replace(" ", ""):
                return activation

        return None

    # =========================================================================
    # INVITES
    # =========================================================================

    def send_invite(
        self,
        activation_id_or_name: str,
        email: str,
        expires_days: int = 30
    ) -> Optional[dict]:
        """
        Send an invite to a creator.

        Args:
            activation_id_or_name: Either the activation UUID or a campaign name/keyword
            email: Creator's email address
            expires_days: How many days until the invite expires (default 30)

        Returns:
            API response if successful, None otherwise

        Example:
            # By activation ID
            client.send_invite("a3344c73-6771-4fd0-91ca-e72e73a35df5", "creator@email.com")

            # By campaign name
            client.send_invite("CrossCuttin", "creator@email.com")
        """
        # Determine if we got an ID or a name
        activation_id = activation_id_or_name

        # If it doesn't look like a UUID, try to find the campaign
        if "-" not in activation_id_or_name or len(activation_id_or_name) < 30:
            campaign = self.find_campaign(activation_id_or_name)
            if campaign:
                activation_id = campaign.id
                print(f"Found campaign: {campaign.name}")
            else:
                print(f"ERROR: Could not find campaign matching '{activation_id_or_name}'")
                return None

        # Calculate expiry
        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat() + "Z"

        print(f"Sending invite to {email} for activation {activation_id[:8]}...")

        result = self._post("send_agency_upload_invite", {
            "activation_id": activation_id,
            "email_addresses": [email],
            "expires_at": expires_at
        }, return_success_on_null=True)

        if result:
            print(f"SUCCESS: Invite sent to {email}")

        return result

    def send_bulk_invites(
        self,
        activation_id_or_name: str,
        emails: List[str],
        expires_days: int = 30
    ) -> Optional[dict]:
        """
        Send invites to multiple creators at once.

        The API supports batch invites, so this is more efficient than
        calling send_invite multiple times.
        """
        # Resolve activation ID
        activation_id = activation_id_or_name
        if "-" not in activation_id_or_name or len(activation_id_or_name) < 30:
            campaign = self.find_campaign(activation_id_or_name)
            if campaign:
                activation_id = campaign.id
            else:
                print(f"ERROR: Could not find campaign matching '{activation_id_or_name}'")
                return None

        expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat() + "Z"

        print(f"Sending {len(emails)} invites for activation {activation_id[:8]}...")

        result = self._post("send_agency_upload_invite", {
            "activation_id": activation_id,
            "email_addresses": emails,
            "expires_at": expires_at
        }, return_success_on_null=True)

        if result:
            print(f"SUCCESS: {len(emails)} invites sent")

        return result

    def list_invites(self, activation_id_or_name: str) -> List[Invite]:
        """
        List all invites for a campaign.

        Returns list of Invite objects with submission status.

        Example:
            invites = client.list_invites("CrossCuttin")
            for inv in invites:
                print(f"{inv.email}: {inv.submission_count} submissions")
        """
        # Resolve activation ID
        activation_id = activation_id_or_name
        if "-" not in activation_id_or_name or len(activation_id_or_name) < 30:
            campaign = self.find_campaign(activation_id_or_name)
            if campaign:
                activation_id = campaign.id
            else:
                print(f"ERROR: Could not find campaign matching '{activation_id_or_name}'")
                return []

        result = self._post("list_agency_upload_invites", {
            "activation_id": activation_id
        })

        if not result:
            return []

        invites = []
        for item in result if isinstance(result, list) else []:
            invite = Invite(
                id=item.get("id", ""),
                email=item.get("email_address", ""),
                token=item.get("token", ""),
                expires_at=item.get("expires_at", ""),
                created_at=item.get("created_at", ""),
                submission_count=item.get("submission_count", 0),
                activation_id=item.get("activation", {}).get("id", ""),
                activation_name=item.get("activation", {}).get("name", "")
            )
            invites.append(invite)

        return invites

    def get_pending_completions(self, activation_id_or_name: str, required_posts: int = 1) -> List[Invite]:
        """
        Get creators who have completed their required posts.

        Returns invites where submission_count >= required_posts.

        Example:
            completed = client.get_pending_completions("CrossCuttin", required_posts=5)
            for inv in completed:
                print(f"{inv.email} completed {inv.submission_count} posts!")
        """
        invites = self.list_invites(activation_id_or_name)
        return [inv for inv in invites if inv.submission_count >= required_posts]

    # =========================================================================
    # STATS
    # =========================================================================

    def get_campaign_stats(
        self,
        promotion_id: str,
        share_token: str,
        days: int = 7
    ) -> Optional[dict]:
        """
        Get performance stats for a campaign.

        Note: This uses the shareable endpoint which needs a share token,
        not the bearer token.

        Returns the latest day's cumulative stats.
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        url = f"{self.base_url}/shareable/promotion_live_post_performance"
        params = {"token": share_token}
        body = {
            "promotion_id": promotion_id,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }

        try:
            response = httpx.post(url, params=params, json=body, timeout=30)
            if response.status_code == 200:
                data = response.json()
                # Return the last (most recent) entry
                return data[-1] if data else None
        except httpx.HTTPError as e:
            print(f"ERROR: {e}")

        return None


# =============================================================================
# MAIN - DEMO/TEST
# =============================================================================

def main():
    """Demo the client capabilities"""

    print("=" * 60)
    print("  COBRAND CLIENT DEMO")
    print("=" * 60)

    client = CobrandClient()

    # Test 1: List all campaigns
    print("\n" + "=" * 60)
    print("  TEST 1: List All Campaigns")
    print("=" * 60)

    campaigns = client.list_all_campaigns()

    if campaigns:
        print(f"\nFound {len(campaigns)} campaigns:\n")
        seen_ids = set()
        for name, activation in campaigns.items():
            if activation.id not in seen_ids:
                seen_ids.add(activation.id)
                print(f"  {activation.name}")
                print(f"    ID: {activation.id}")
                print(f"    Status: {activation.status}")
                print(f"    Keyword: {activation.keyword}")
                print()
    else:
        print("No campaigns found or error occurred")

    # Test 2: Find a specific campaign
    print("\n" + "=" * 60)
    print("  TEST 2: Find Campaign by Keyword")
    print("=" * 60)

    test_keywords = ["CrossCuttin", "Xavier", "Wulf"]
    for keyword in test_keywords:
        campaign = client.find_campaign(keyword)
        if campaign:
            print(f"\n  '{keyword}' -> {campaign.name}")
            print(f"    Activation ID: {campaign.id}")
            break

    # Test 3: List invites for a known campaign
    print("\n" + "=" * 60)
    print("  TEST 3: List Invites")
    print("=" * 60)

    # Use the known activation ID
    invites = client.list_invites("a3344c73-6771-4fd0-91ca-e72e73a35df5")
    print(f"\nFound {len(invites)} invites:")
    for inv in invites[:5]:  # Show first 5
        print(f"  {inv.email}: {inv.submission_count} submissions")

    # Summary
    print("\n" + "=" * 60)
    print("  READY FOR AUTOMATION")
    print("=" * 60)
    print("""
    The client is ready! You can now:

    1. FIND CAMPAIGNS:
       campaign = client.find_campaign("CrossCuttin")

    2. SEND INVITES:
       client.send_invite("CrossCuttin", "creator@email.com")

    3. CHECK COMPLETIONS:
       completed = client.get_pending_completions("CrossCuttin", required_posts=5)

    4. LIST ALL INVITES:
       invites = client.list_invites("CrossCuttin")
    """)


if __name__ == "__main__":
    main()
