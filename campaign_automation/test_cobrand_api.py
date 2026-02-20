"""
Cobrand API Explorer
====================

This script helps you:
1. Test the known API endpoint
2. Explore for other endpoints
3. Understand what data you can pull

Run with: python test_cobrand_api.py
"""

import sys
import io

# Fix Windows console encoding for special characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import httpx
from datetime import datetime, timedelta
import json

# =============================================================================
# CONFIGURATION - Your actual Cobrand links
# =============================================================================

# Campaign: b5117e97-bf40-4928-a136-a9c469526d54
#
# Link 1 (Share/View - for clients):
# https://music.cobrand.com/promote/b5117e97-bf40-4928-a136-a9c469526d54/share?token=XWtOn1DW7RXvcZ3FcLA8PkvsNklqmD5NDYjLd_Ua1Wg
#
# Link 2 (Upload - for creators):
# https://music.cobrand.com/promote/b5117e97-bf40-4928-a136-a9c469526d54/upload/?token=YZ726PTBudelgGcB4JZhWuKMDBgZwEIC24IhV_qpTtQ

PROMOTION_ID = "b5117e97-bf40-4928-a136-a9c469526d54"

# Two different tokens for different purposes
SHARE_TOKEN = "XWtOn1DW7RXvcZ3FcLA8PkvsNklqmD5NDYjLd_Ua1Wg"   # View stats
UPLOAD_TOKEN = "YZ726PTBudelgGcB4JZhWuKMDBgZwEIC24IhV_qpTtQ"  # Creator uploads

# Default to share token for stats
TOKEN = SHARE_TOKEN

# API Base URL
BASE_URL = "https://api.cobrand.com/brand/v2/shareable"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def pretty_print(data):
    """Print JSON data nicely formatted"""
    print(json.dumps(data, indent=2))


def parse_share_link(url: str) -> dict:
    """
    Extract promotion_id and token from a Cobrand share link.

    Example input:
    https://music.cobrand.com/promote/2d19ed1c-5fb9-451e-a9fc-04004d35127d/share/?token=N6optg7B...

    Returns:
    {"promotion_id": "2d19ed1c-...", "token": "N6optg7B..."}
    """
    from urllib.parse import urlparse, parse_qs

    parsed = urlparse(url)
    path_parts = parsed.path.split('/')

    # Find promotion ID (UUID format)
    promotion_id = None
    for part in path_parts:
        if len(part) == 36 and part.count('-') == 4:  # UUID format
            promotion_id = part
            break

    # Extract token from query string
    query_params = parse_qs(parsed.query)
    token = query_params.get('token', [None])[0]

    return {
        "promotion_id": promotion_id,
        "token": token
    }


# =============================================================================
# API FUNCTIONS (KNOWN WORKING)
# =============================================================================

def get_campaign_performance(promotion_id: str, token: str, days: int = 7) -> dict:
    """
    Get campaign performance stats for the last N days.

    This endpoint is CONFIRMED WORKING.

    Returns daily cumulative stats:
    - play_count_total (views)
    - heart_count_total (likes)
    - share_count_total (shares)
    - comment_count_total (comments)
    - engagement_rate
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    url = f"{BASE_URL}/promotion_live_post_performance"
    params = {"token": token}
    body = {
        "promotion_id": promotion_id,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }

    print(f"\n📊 Fetching performance for promotion: {promotion_id[:8]}...")
    print(f"   Date range: {body['start_date']} to {body['end_date']}")

    try:
        response = httpx.post(url, params=params, json=body, timeout=30)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        print(f"❌ Error: {e}")
        return None


def get_latest_stats(performance_data: list) -> dict:
    """
    Extract the latest (most recent) stats from performance data.
    Since the data is cumulative, the last entry has the totals.
    """
    if not performance_data:
        return None
    return performance_data[-1]


# =============================================================================
# API EXPLORATION (UNTESTED - MIGHT NOT WORK)
# =============================================================================

def explore_endpoint(endpoint: str, promotion_id: str, token: str, method: str = "POST", body: dict = None):
    """
    Try hitting an endpoint to see if it exists.

    Use this to discover new endpoints.
    """
    url = f"{BASE_URL}/{endpoint}"
    params = {"token": token}

    if body is None:
        body = {"promotion_id": promotion_id}

    print(f"\n🔍 Exploring: {method} {url}")

    try:
        if method == "GET":
            response = httpx.get(url, params={**params, "promotion_id": promotion_id}, timeout=30)
        else:
            response = httpx.post(url, params=params, json=body, timeout=30)

        print(f"   Status: {response.status_code}")

        if response.status_code == 200:
            print("   ✅ Endpoint exists!")
            return response.json()
        elif response.status_code == 404:
            print("   ❌ Endpoint not found")
            return None
        elif response.status_code == 401:
            print("   🔒 Unauthorized - might need different auth")
            return None
        else:
            print(f"   ⚠️ Unexpected response: {response.text[:200]}")
            return None

    except httpx.HTTPError as e:
        print(f"   ❌ Error: {e}")
        return None


# =============================================================================
# MAIN SCRIPT
# =============================================================================

def main():
    print("=" * 60)
    print("  COBRAND API EXPLORER")
    print("=" * 60)

    # Test 1: Known working endpoint
    print("\n" + "=" * 60)
    print("  TEST 1: Campaign Performance (Known Working)")
    print("=" * 60)

    performance = get_campaign_performance(PROMOTION_ID, TOKEN, days=7)

    if performance:
        latest = get_latest_stats(performance)
        if latest:
            print("\n📈 Latest Campaign Stats:")
            print(f"   📺 Total Views:    {latest['play_count_total']:,}")
            print(f"   ❤️  Total Likes:    {latest['heart_count_total']:,}")
            print(f"   🔄 Total Shares:   {latest['share_count_total']:,}")
            print(f"   💬 Total Comments: {latest['comment_count_total']:,}")
            print(f"   📊 Engagement:     {latest['engagement_rate']:.2%}")
            print(f"\n   Full response ({len(performance)} days of data):")
            pretty_print(performance)

    # Test 2: Explore potential endpoints
    print("\n" + "=" * 60)
    print("  TEST 2: Exploring Other Endpoints")
    print("=" * 60)

    # These are GUESSES based on common API patterns
    # Most will probably fail, but if any work, we've discovered something!

    potential_endpoints = [
        "promotion_details",
        "promotion_creators",
        "promotion_collaborators",
        "promotion_submissions",
        "creator_list",
        "invite_list",
    ]

    print("\nTrying potential endpoints (expect most to fail)...")

    for endpoint in potential_endpoints:
        result = explore_endpoint(endpoint, PROMOTION_ID, TOKEN)
        if result:
            print(f"\n🎉 Found working endpoint: {endpoint}")
            pretty_print(result)

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print("""
What we know works:
  ✅ promotion_live_post_performance - Get campaign stats

What we still need to discover:
  ❓ How to list creators in a campaign
  ❓ How to check creator submission status
  ❓ How to invite creators programmatically

Next steps:
  1. Ask your team for Cobrand API documentation
  2. Use browser Network tab to watch API calls in Cobrand UI
  3. Contact Cobrand support for API access
    """)


def parse_link_demo():
    """Demo the share link parser"""
    test_url = "https://music.cobrand.com/promote/2d19ed1c-5fb9-451e-a9fc-04004d35127d/share/?token=N6optg7B4R0sXcFNP8jpNM7_oLm-30rtW_qh45haczI"

    print("\n📎 Share Link Parser Demo")
    print(f"   Input: {test_url[:60]}...")

    parsed = parse_share_link(test_url)
    print(f"   Promotion ID: {parsed['promotion_id']}")
    print(f"   Token: {parsed['token'][:20]}...")


if __name__ == "__main__":
    main()
    parse_link_demo()
