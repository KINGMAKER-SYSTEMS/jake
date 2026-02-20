"""Try to find working endpoints"""
import httpx
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = 'https://api.cobrand.com/brand/v2'
TOKEN = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImE1VklFSG5tSXJXV0RjRWdRWFFlbiJ9.eyJpc3MiOiJodHRwczovL2xvdWRseS1haS51cy5hdXRoMC5jb20vIiwic3ViIjoiYXV0aDB8Njg1MTdjMjUxYWNkZmQxODNlZGUwYzZhIiwiYXVkIjpbImh0dHBzOi8vbG91ZGx5LWFpLnVzLmF1dGgwIiwiaHR0cHM6Ly9sb3VkbHktYWkudXMuYXV0aDAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTc3MDQyMDY2NSwiZXhwIjoxNzcwNTA3MDY1LCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIiwiYXpwIjoiaTVpcUxUSEJDZDVBQkx6SzZUS0hOYmtUQWJuS0FqQTAifQ.km-ScUC0Iy883vxgWljSjKmvx5zCgtkWyWenjZMXvrAEVBulLabPiN1oNz0WVBhN0hk1D1Gf3zkvHt0vZaR_ID8fMTd4WL5ZgDQfT0OFwitJO-FjiWFvKO5Rxpdi9LMdKvjC4whx8Gx-1uSS-NZc6w8wsYZFO6EfwplYAMAT7ng3w2uvD1xCtiBxno5tOZIAIbVUIocbw6eGtQsx9klnPSpPCDrW8blvoBNu4sTXj0XumkgXaIhT9uUbdfzXrt-BcemT0QabYSz_cduOVR7FVSzmE7No6cUjWRMyKaZGMBHE60SLmDb-6EQMXvvNu6h3wvy4_WPQiz0oKNjj4-zw-g'
ORG_ID = '652c1528-f525-4c80-be5d-fda2aa6005fd'
ACT_ID = '019c351d-5385-72ea-925c-25b580ce1bbb'
PROMO_ID = '019c351c-a258-731d-bb64-7af921f33347'

headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

# More endpoints to try
endpoints = [
    # Collaboration related
    ('list_collaboration', {'activation_id': ACT_ID}),
    ('get_collaboration', {'activation_id': ACT_ID}),
    ('list_promotion_collaborations', {'promotion_id': PROMO_ID}),
    ('get_promotion_collaborations', {'promotion_id': PROMO_ID}),
    
    # Creator related  
    ('list_creators', {'activation_id': ACT_ID}),
    ('list_activation_creators', {'activation_id': ACT_ID}),
    ('search_creators', {'activation_id': ACT_ID}),
    
    # Booking related
    ('list_bookings', {'activation_id': ACT_ID}),
    ('list_activation_bookings', {'activation_id': ACT_ID}),
    
    # Hire related
    ('list_hire', {'activation_id': ACT_ID}),
    ('get_hires', {'activation_id': ACT_ID}),
    
    # Submission related
    ('list_submissions', {'activation_id': ACT_ID}),
    ('list_promotion_submissions', {'promotion_id': PROMO_ID}),
    ('list_live_submissions', {'activation_id': ACT_ID}),
    ('get_submissions', {'activation_id': ACT_ID}),
    
    # Member/participant related
    ('list_members', {'activation_id': ACT_ID}),
    ('list_participants', {'activation_id': ACT_ID}),
    
    # Organization level
    ('list_organization_creators', {'organization_id': ORG_ID}),
    ('list_organization_collaborations', {'organization_id': ORG_ID}),
]

print("Testing endpoints...\n")

working = []
for name, body in endpoints:
    try:
        r = httpx.post(f'{BASE_URL}/{name}', headers=headers, json=body, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data:
                if isinstance(data, list):
                    count = len(data)
                elif isinstance(data, dict):
                    count = len(data.get('items', data.get('data', [])))
                else:
                    count = 'unknown'
                print(f"✓ {name}: 200 OK - {count} items")
                working.append((name, body, data))
            else:
                print(f"✓ {name}: 200 OK - empty")
        elif r.status_code == 404:
            pass  # Skip 404s silently
        else:
            print(f"✗ {name}: {r.status_code}")
    except Exception as e:
        print(f"✗ {name}: Error - {str(e)[:50]}")

print(f"\n=== Working endpoints: {len(working)} ===")
for name, body, data in working:
    print(f"\n{name}:")
    if isinstance(data, list) and data:
        print(f"  First item keys: {list(data[0].keys())[:8]}")
    elif isinstance(data, dict):
        print(f"  Keys: {list(data.keys())[:8]}")
