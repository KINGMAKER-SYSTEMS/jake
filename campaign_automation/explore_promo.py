"""Explore a single promotion in detail"""
import httpx
import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = 'https://api.cobrand.com/brand/v2'
TOKEN = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImE1VklFSG5tSXJXV0RjRWdRWFFlbiJ9.eyJpc3MiOiJodHRwczovL2xvdWRseS1haS51cy5hdXRoMC5jb20vIiwic3ViIjoiYXV0aDB8Njg1MTdjMjUxYWNkZmQxODNlZGUwYzZhIiwiYXVkIjpbImh0dHBzOi8vbG91ZGx5LWFpLnVzLmF1dGgwIiwiaHR0cHM6Ly9sb3VkbHktYWkudXMuYXV0aDAuY29tL3VzZXJpbmZvIl0sImlhdCI6MTc3MDQyMDY2NSwiZXhwIjoxNzcwNTA3MDY1LCJzY29wZSI6Im9wZW5pZCBwcm9maWxlIGVtYWlsIiwiYXpwIjoiaTVpcUxUSEJDZDVBQkx6SzZUS0hOYmtUQWJuS0FqQTAifQ.km-ScUC0Iy883vxgWljSjKmvx5zCgtkWyWenjZMXvrAEVBulLabPiN1oNz0WVBhN0hk1D1Gf3zkvHt0vZaR_ID8fMTd4WL5ZgDQfT0OFwitJO-FjiWFvKO5Rxpdi9LMdKvjC4whx8Gx-1uSS-NZc6w8wsYZFO6EfwplYAMAT7ng3w2uvD1xCtiBxno5tOZIAIbVUIocbw6eGtQsx9klnPSpPCDrW8blvoBNu4sTXj0XumkgXaIhT9uUbdfzXrt-BcemT0QabYSz_cduOVR7FVSzmE7No6cUjWRMyKaZGMBHE60SLmDb-6EQMXvvNu6h3wvy4_WPQiz0oKNjj4-zw-g'
ORG_ID = '652c1528-f525-4c80-be5d-fda2aa6005fd'

headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

# Get first few promotions
r = httpx.post(f'{BASE_URL}/list_promotions_v3', headers=headers, json={
    'organization_id': ORG_ID,
    'page': 1,
    'page_size': 10
}, timeout=30)

promos = r.json().get('items', [])

# Pick one without checkmark (active)
active = [p for p in promos if '✅' not in p.get('name', '') and '✓' not in p.get('name', '')]
if active:
    promo = active[0]
    print(f"=== Exploring: {promo.get('name')} ===")
    print(f"Promo ID: {promo.get('id')}")
    
    # Get full promotion details
    r2 = httpx.post(f'{BASE_URL}/get_promotion', headers=headers, json={
        'promotion_id': promo.get('id')
    }, timeout=30)
    
    if r2.status_code == 200:
        details = r2.json()
        print(f"\nPromotion keys: {list(details.keys())}")
        print(f"Collaboration count: {details.get('collaboration_count')}")
        print(f"Live submissions: {details.get('live_submission_count')}")
        print(f"Draft submissions: {details.get('draft_submission_count')}")
        
        activations = details.get('activations', [])
        print(f"\nActivations: {len(activations)}")
        
        if activations:
            act = activations[0]
            act_id = act.get('id')
            print(f"\nFirst activation: {act.get('name')}")
            print(f"Activation ID: {act_id}")
            print(f"Collaboration count: {act.get('collaboration_count')}")
            
            # Try to get activation details
            r3 = httpx.post(f'{BASE_URL}/get_activation', headers=headers, json={
                'activation_id': act_id
            }, timeout=30)
            
            if r3.status_code == 200:
                act_details = r3.json()
                print(f"\nActivation keys: {list(act_details.keys())}")
                
                # Look for creator-related fields
                for key in act_details:
                    val = act_details[key]
                    if isinstance(val, list) and len(val) > 0:
                        print(f"  {key}: list with {len(val)} items")
                    elif isinstance(val, int) and val > 0:
                        print(f"  {key}: {val}")
            
            # Try other endpoints for this activation
            print("\n=== Trying other endpoints ===")
            
            # list_agency_upload_invites
            r4 = httpx.post(f'{BASE_URL}/list_agency_upload_invites', headers=headers, json={
                'activation_id': act_id
            }, timeout=30)
            print(f"list_agency_upload_invites: {r4.status_code}, items: {len(r4.json()) if r4.status_code == 200 and r4.json() else 0}")
            
            # Try to find collaboration endpoints
            test_endpoints = [
                'list_activation_collaborations',
                'list_collaborations_v2', 
                'get_collaborations',
                'list_hires',
                'list_activation_hires',
            ]
            
            for ep in test_endpoints:
                try:
                    r5 = httpx.post(f'{BASE_URL}/{ep}', headers=headers, json={
                        'activation_id': act_id
                    }, timeout=10)
                    if r5.status_code == 200:
                        data = r5.json()
                        count = len(data) if isinstance(data, list) else len(data.get('items', [])) if isinstance(data, dict) else 'N/A'
                        print(f"{ep}: 200 OK! Count: {count}")
                        if data:
                            if isinstance(data, list) and data:
                                print(f"  First item keys: {list(data[0].keys())[:10]}")
                            elif isinstance(data, dict) and data.get('items'):
                                print(f"  First item keys: {list(data['items'][0].keys())[:10]}")
                    else:
                        print(f"{ep}: {r5.status_code}")
                except Exception as e:
                    print(f"{ep}: Error - {e}")
