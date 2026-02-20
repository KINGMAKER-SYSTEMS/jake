# Cobrand API Exploration

## CONFIRMED WORKING ENDPOINTS

### 1. Get Campaign Performance Stats
```
POST https://api.cobrand.com/brand/v2/shareable/promotion_live_post_performance?token=XXX
```

**Authentication**: Token in query string (from share link)

**Request**:
```json
{
  "promotion_id": "b5117e97-bf40-4928-a136-a9c469526d54",
  "start_date": "2026-01-13",
  "end_date": "2026-01-20"
}
```

**Response**: Array of daily cumulative performance data
```json
[
  {
    "date": "2026-01-20",
    "play_count_total": 1721708,
    "share_count_total": 87758,
    "comment_count_total": 1229,
    "heart_count_total": 107622,
    "engagement_rate": 0.1141941606822992
  }
]
```

---

### 2. Send Creator Invite (DISCOVERED!)
```
POST https://api.cobrand.com/brand/v2/send_agency_upload_invite
```

**Authentication**: Bearer token (Auth0) in Authorization header

**Headers**:
```
Authorization: Bearer <your_access_token>
Content-Type: application/json
```

**Request**:
```json
{
  "activation_id": "a3344c73-6771-4fd0-91ca-e72e73a35df5",
  "email_addresses": ["creator@email.com"],
  "expires_at": "2026-02-15T05:00:00.000Z"
}
```

**Parameters**:
| Field | Type | Description |
|-------|------|-------------|
| activation_id | UUID string | The campaign/activation to invite to |
| email_addresses | string[] | Array of emails (can batch invite!) |
| expires_at | ISO 8601 | When the invite link expires |

---

### 3. List Campaign Invites (DISCOVERED!)
```
POST https://api.cobrand.com/brand/v2/list_agency_upload_invites
```

**Authentication**: Bearer token (Auth0)

**Request**:
```json
{
  "activation_id": "a3344c73-6771-4fd0-91ca-e72e73a35df5"
}
```

**Response**: (To be documented - likely returns list of invited creators and their status)

---

## Key Concepts

### Two Types of IDs

| ID Type | What It Is | Where You Get It |
|---------|-----------|------------------|
| `promotion_id` | Overall promotion/campaign | From share link URL |
| `activation_id` | Specific activation within promo | From Cobrand UI or API |

### Two Types of Authentication

| Auth Type | Used For | How |
|-----------|----------|-----|
| Share Token | Read-only stats | Query param `?token=XXX` |
| Bearer Token | Write operations (invites) | Header `Authorization: Bearer XXX` |

---

## Link Types

| Link Type | URL Pattern | Purpose |
|-----------|-------------|---------|
| Share/View | `/promote/{id}/share?token=XXX` | Read-only stats for clients |
| Upload | `/promote/{id}/upload/?token=XXX` | Creator submission portal |

---

## API Pattern Analysis

Based on the endpoint structure, I can infer the likely API design:

```
Base URL: https://api.cobrand.com/brand/v2/

Namespace: shareable/
  └── promotion_live_post_performance  ✓ (confirmed)
  └── promotion_details                ? (likely exists)
  └── promotion_creators               ? (likely exists)
  └── creator_submissions              ? (likely exists)

Other likely namespaces:
  └── promotions/                      ? (CRUD for promotions)
  └── creators/                        ? (creator management)
  └── invites/                         ? (invitation system)
```

---

## Endpoints to Discover

Ask your team or Cobrand support about these:

### 1. List Creators in a Campaign
```
GET /brand/v2/shareable/promotion_creators?token=XXX
or
POST /brand/v2/shareable/promotion_creators
{
  "promotion_id": "...",
  "token": "..."
}
```

**What we'd want back**:
```json
{
  "creators": [
    {
      "email": "creator@email.com",
      "tiktok_username": "@creator123",
      "status": "submitted",  // or "pending", "verified"
      "posts_required": 5,
      "posts_submitted": 5,
      "invited_at": "2025-01-15",
      "submitted_at": "2025-01-18"
    }
  ]
}
```

### 2. Get Promotion Details
```
GET /brand/v2/shareable/promotion_details?token=XXX&promotion_id=XXX
```

**What we'd want back**:
```json
{
  "promotion_id": "2d19ed1c-...",
  "name": "Winter Promo 2025",
  "song_name": "Song Title",
  "artist": "Artist Name",
  "posts_required_per_creator": 5,
  "payment_per_creator": 50.00,
  "start_date": "2025-01-01",
  "end_date": "2025-02-01",
  "total_creators_invited": 25,
  "total_creators_completed": 18
}
```

### 3. Add Creator to Campaign (Invite)
```
POST /brand/v2/shareable/promotion_invite
{
  "promotion_id": "...",
  "token": "...",
  "email": "newcreator@email.com"
}
```

**What we'd want back**:
```json
{
  "success": true,
  "invite_link": "https://music.cobrand.com/submit/abc123",
  "creator_id": "creator_xyz"
}
```

### 4. Webhooks (if supported)
```
POST /brand/v2/webhooks/register
{
  "event": "creator_completed",
  "url": "https://your-server.com/webhook/cobrand",
  "token": "..."
}
```

Events we'd want:
- `creator_invited` - When invite is sent
- `creator_submitted` - When creator uploads posts
- `creator_verified` - When posts are approved
- `promotion_completed` - When campaign reaches goal

---

## How to Discover More

### Option 1: Ask Your Team
"Hey, do we have documentation for Cobrand's API? I'm trying to automate some of our campaign workflows."

### Option 2: Network Inspector
1. Open Cobrand in Chrome
2. Press F12 → Network tab
3. Click around the interface (view creators, invite someone, etc.)
4. Watch the API calls that appear
5. Document the endpoints, request/response formats

### Option 3: Ask Cobrand Support
"We'd like to automate parts of our workflow using your API. Can you share documentation for:
- Adding collaborators/creators to a campaign
- Checking creator submission status
- Listing all creators in a campaign
- Webhook support for completion events"

---

## Quick Test Script

Once you discover endpoints, test them with this Python script:

```python
import httpx

BASE_URL = "https://api.cobrand.com/brand/v2/shareable"

# Known working endpoint
def get_performance(promotion_id: str, token: str, start_date: str, end_date: str):
    url = f"{BASE_URL}/promotion_live_post_performance"
    params = {"token": token}
    body = {
        "promotion_id": promotion_id,
        "start_date": start_date,
        "end_date": end_date
    }
    response = httpx.post(url, params=params, json=body)
    return response.json()

# Test other endpoints (modify as you discover them)
def get_creators(promotion_id: str, token: str):
    url = f"{BASE_URL}/promotion_creators"  # GUESS - verify this endpoint
    params = {"token": token}
    body = {"promotion_id": promotion_id}
    response = httpx.post(url, params=params, json=body)
    return response.json()

# Usage
if __name__ == "__main__":
    PROMO_ID = "2d19ed1c-5fb9-451e-a9fc-04004d35127d"
    TOKEN = "N6optg7B4R0sXcFNP8jpNM7_oLm-30rtW_qh45haczI"

    # This should work
    performance = get_performance(PROMO_ID, TOKEN, "2025-12-08", "2025-12-15")
    print("Performance:", performance)

    # This is a guess - might not work
    # creators = get_creators(PROMO_ID, TOKEN)
    # print("Creators:", creators)
```

---

## Priority Questions for Cobrand

1. **How do we programmatically invite a creator to a campaign?**
   - We want to automate: Creator DMs us → System adds them to Cobrand → They get invite email

2. **How do we check if a creator has completed their submissions?**
   - We want to automate: Creator says "done" → System verifies with Cobrand → Triggers payment flow

3. **Do you support webhooks for events like "creator completed"?**
   - Would eliminate need for polling

4. **Is there rate limiting on the API?**
   - Important if we're checking status frequently
