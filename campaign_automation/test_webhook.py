"""
Test the webhook server locally
"""

import httpx
import json

BASE_URL = "http://localhost:5050"

def test_health():
    """Test health endpoint"""
    print("\n--- Testing /health ---")
    response = httpx.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

def test_campaigns():
    """Test campaigns list"""
    print("\n--- Testing /campaigns ---")
    response = httpx.get(f"{BASE_URL}/campaigns", timeout=60)
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Found {data.get('count', 0)} campaigns")
    for c in data.get('campaigns', [])[:5]:
        print(f"  - {c['name']}")

def test_register():
    """Test registration webhook"""
    print("\n--- Testing /webhook/register ---")

    # Test with structured data
    payload = {
        "campaign": "CrossCuttin",
        "email": "test-webhook@example.com",
        "subscriber_id": "test123",
        "tiktok_username": "@testcreator"
    }

    response = httpx.post(
        f"{BASE_URL}/webhook/register",
        json=payload,
        timeout=60
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_register_message():
    """Test registration with raw message format"""
    print("\n--- Testing /webhook/register (message format) ---")

    # Test with message format (like ManyChat would send)
    payload = {
        "message": "CrossCuttin myemail@gmail.com",
        "subscriber_id": "test456"
    }

    response = httpx.post(
        f"{BASE_URL}/webhook/register",
        json=payload,
        timeout=60
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_payment():
    """Test payment webhook"""
    print("\n--- Testing /webhook/payment ---")

    payload = {
        "paypal_email": "creator@paypal.com",
        "subscriber_id": "test123"
    }

    response = httpx.post(
        f"{BASE_URL}/webhook/payment",
        json=payload,
        timeout=30
    )

    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

def test_registrations():
    """View all registrations"""
    print("\n--- Testing /registrations ---")
    response = httpx.get(f"{BASE_URL}/registrations")
    print(f"Status: {response.status_code}")
    print(f"Registrations: {json.dumps(response.json(), indent=2)}")


if __name__ == "__main__":
    print("=" * 60)
    print("  WEBHOOK SERVER TESTS")
    print("=" * 60)
    print("\nMake sure the server is running: python webhook_server.py\n")

    try:
        test_health()
        test_campaigns()
        # Uncomment to test actual registration (will send real invite!)
        # test_register()
        # test_register_message()
        # test_payment()
        test_registrations()
    except httpx.ConnectError:
        print("\nERROR: Could not connect to server.")
        print("Make sure you run: python webhook_server.py")
