"""
Debug script to see raw API responses
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import httpx
import json

BEARER_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImE1VklFSG5tSXJXV0RjRWdRWFFlbiJ9.eyJpc3MiOiJodHRwczovL2xvdWRseS1haS51cy5hdXRoMC5jb20vIiwic3ViIjoiYXV0aDB8Njg1MTdjMjUxYWNkZmQxODNlZGUwYzZhIiwiYXVkIjpbImh0dHBzOi8vbG91ZGx5LWFpLnVzLmF1dGgwIiwiaHR0cHM6Ly9sb3VkbHktYWkudXMuYXV0aDAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTc2ODkzMDM4MCwiZXhwIjoxNzY5MDE2NzgwLCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIiwiYXpwIjoiaTVpcUxUSEJDZDVBQkx6SzZUS0hOYmtUQWJuS0FqQTAifQ.m8SLOZdubHhfiM9rhlIILxwBbhISRvkVOoo5GBasHr4jRghfPVDUTYJrqshsP3hP5P2C8yZr0r471trTGxJxZ015u7ndt2m3epY6sYIvBmT8zWPuaDMV7Sqyw6nb3BAkUOXpzjzWk569F5iPfgl2ZNC_znXsVSZNIruwGjXgC8_Lbxoh9JCqbjaeF2xRj25cmf7FbF69-OgTPONs2mt4wLtIL2wdrBkbMTiaQiTRf1Ql91ZI_3Y2ZhQ_Kez2r4vA1f08-3bog-DRiZD0EP3gIAvD8ZMsnQY5KhbAY3mH1Equcjrdqnsy9dAaOsUiYnnp9JyAMhh7a_SwuvH7_r_MyA"
ORGANIZATION_ID = "652c1528-f525-4c80-be5d-fda2aa6005fd"
BASE_URL = "https://api.cobrand.com/brand/v2"

headers = {
    "Authorization": f"Bearer {BEARER_TOKEN}",
    "Content-Type": "application/json"
}

print("=" * 60)
print("DEBUG: Raw API Responses")
print("=" * 60)

# Test list_promotions_v3
print("\n--- list_promotions_v3 ---")
response = httpx.post(
    f"{BASE_URL}/list_promotions_v3",
    headers=headers,
    json={"organization_id": ORGANIZATION_ID},
    timeout=30
)
print(f"Status: {response.status_code}")
print(f"Response type: {type(response.json())}")
print(f"Response (first 2000 chars):")
print(json.dumps(response.json(), indent=2)[:2000])

# Test get_promotion with known ID
print("\n--- get_promotion ---")
KNOWN_PROMOTION_ID = "c2e0d593-71d2-4147-bc34-9bc52cbec357"
response = httpx.post(
    f"{BASE_URL}/get_promotion",
    headers=headers,
    json={"promotion_id": KNOWN_PROMOTION_ID},
    timeout=30
)
print(f"Status: {response.status_code}")
print(f"Response (first 3000 chars):")
print(json.dumps(response.json(), indent=2)[:3000])

# Test get_activation with known ID
print("\n--- get_activation ---")
KNOWN_ACTIVATION_ID = "a3344c73-6771-4fd0-91ca-e72e73a35df5"
response = httpx.post(
    f"{BASE_URL}/get_activation",
    headers=headers,
    json={"activation_id": KNOWN_ACTIVATION_ID},
    timeout=30
)
print(f"Status: {response.status_code}")
print(f"Response (first 2000 chars):")
print(json.dumps(response.json(), indent=2)[:2000])
