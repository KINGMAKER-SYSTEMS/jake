"""Simple API test"""
import httpx
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = 'https://api.cobrand.com/brand/v2'
TOKEN = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImE1VklFSG5tSXJXV0RjRWdRWFFlbiJ9.eyJpc3MiOiJodHRwczovL2xvdWRseS1haS51cy5hdXRoMC5jb20vIiwic3ViIjoiYXV0aDB8Njg1MTdjMjUxYWNkZmQxODNlZGUwYzZhIiwiYXVkIjpbImh0dHBzOi8vbG91ZGx5LWFpLnVzLmF1dGgwIiwiaHR0cHM6Ly9sb3VkbHktYWkudXMuYXV0aDAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTc3MDQyMDY2NSwiZXhwIjoxNzcwNTA3MDY1LCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIiwiYXpwIjoiaTVpcUxUSEJDZDVBQkx6SzZUS0hOYmtUQWJuS0FqQTAifQ.km-ScUC0Iy883vxgWljSjKmvx5zCgtkWyWenjZMXvrAEVBulLabPiN1oNz0WVBhN0hk1D1Gf3zkvHt0vZaR_ID8fMTd4WL5ZgDQfT0OFwitJO-FjiWFvKO5Rxpdi9LMdKvjC4whx8Gx-1uSS-NZc6w8wsYZFO6EfwplYAMAT7ng3w2uvD1xCtiBxno5tOZIAIbVUIocbw6eGtQsx9klnPSpPCDrW8blvoBNu4sTXj0XumkgXaIhT9uUbdfzXrt-BcemT0QabYSz_cduOVR7FVSzmE7No6cUjWRMyKaZGMBHE60SLmDb-6EQMXvvNu6h3wvy4_WPQiz0oKNjj4-zw-g'
ORG_ID = '652c1528-f525-4c80-be5d-fda2aa6005fd'

print("Testing Cobrand API...")
headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

# Get multiple pages
all_promos = []
for page in range(1, 5):  # Get first 4 pages
    r = httpx.post(f'{BASE_URL}/list_promotions_v3', headers=headers, json={
        'organization_id': ORG_ID,
        'page': page,
        'page_size': 50
    }, timeout=30)
    
    if r.status_code != 200:
        print(f"Page {page} error: {r.status_code}")
        break
        
    data = r.json()
    items = data.get('items', [])
    if not items:
        break
    all_promos.extend(items)
    print(f"Page {page}: {len(items)} promotions")

print(f"\nTotal: {len(all_promos)} promotions")

# Count by status
statuses = {}
for p in all_promos:
    s = p.get('status', 'unknown')
    statuses[s] = statuses.get(s, 0) + 1
print(f"By status: {statuses}")

# Find ones with live submissions
with_subs = [(p.get('name', 'Unknown'), p.get('live_submission_count', 0)) 
             for p in all_promos if (p.get('live_submission_count') or 0) > 0]
print(f"\nWith live submissions: {len(with_subs)}")
for name, count in with_subs[:10]:
    print(f"  {name[:50]}: {count}")

# Check for checkmarks (completed)
completed = [p for p in all_promos if '✅' in p.get('name', '') or '✓' in p.get('name', '')]
print(f"\nWith checkmark (completed): {len(completed)}")
