# Campaign Automation - Google Sheet Template

## Sheet Structure

Create a new Google Sheet named: **"Campaign Automation Tracker"**

---

## Tab 1: "Registrations"

### Columns

| Column | Header | Description | Example |
|--------|--------|-------------|---------|
| A | Timestamp | Auto-filled by Zapier | 2025-01-20 14:30:00 |
| B | Campaign | Campaign keyword | WinterPromo |
| C | Creator Email | Email for Cobrand invite | creator@email.com |
| D | TikTok Username | Their TikTok handle | @musicfan123 |
| E | ManyChat ID | For sending messages back | 12345678 |
| F | Cobrand Invited | Manual checkbox or Y/N | Y |
| G | Posts Required | Number of posts for campaign | 5 |
| H | Posts Submitted | Update from Cobrand | 3 |
| I | Status | Current state | registered / invited / complete |
| J | Date Registered | When they signed up | 2025-01-20 |
| K | Date Completed | When posts verified | 2025-01-25 |
| L | Notes | Any manual notes | "Re-sent invite on 1/22" |

### Row 1 (Headers)
```
Timestamp | Campaign | Creator Email | TikTok Username | ManyChat ID | Cobrand Invited | Posts Required | Posts Submitted | Status | Date Registered | Date Completed | Notes
```

### Data Validation for Status Column (I)
1. Select column I (starting from I2)
2. Data → Data validation
3. Criteria: List of items
4. Enter: `registered, invited, in_progress, complete, payment_pending, paid`

### Conditional Formatting
1. Select columns A-L
2. Format → Conditional formatting

**Rule 1: Highlight complete**
- Apply to range: I2:I1000
- Format cells if: Text is exactly "complete"
- Formatting style: Green background

**Rule 2: Highlight payment pending**
- Apply to range: I2:I1000
- Format cells if: Text is exactly "payment_pending"
- Formatting style: Yellow background

**Rule 3: Highlight paid**
- Apply to range: I2:I1000
- Format cells if: Text is exactly "paid"
- Formatting style: Blue background

---

## Tab 2: "Payment Queue"

### Columns

| Column | Header | Description | Example |
|--------|--------|-------------|---------|
| A | Timestamp | When added to queue | 2025-01-25 10:00:00 |
| B | Campaign | Campaign name | WinterPromo |
| C | TikTok Username | Creator handle | @musicfan123 |
| D | Creator Email | For reference | creator@email.com |
| E | PayPal Email | Payment destination | payment@email.com |
| F | Amount | Payment amount | 50.00 |
| G | Payment Status | pending/processing/sent/failed | pending |
| H | Date Paid | When payment sent | 2025-01-27 |
| I | Transaction ID | PayPal reference | PAY-123456 |
| J | Notes | Any issues | "Resent - wrong PayPal first time" |

### Row 1 (Headers)
```
Timestamp | Campaign | TikTok Username | Creator Email | PayPal Email | Amount | Payment Status | Date Paid | Transaction ID | Notes
```

### Useful Formulas

**In a summary cell - Count pending payments:**
```
=COUNTIF(G:G, "pending")
```

**Total pending amount:**
```
=SUMIF(G:G, "pending", F:F)
```

**Count by campaign:**
```
=COUNTIF(B:B, "WinterPromo")
```

---

## Tab 3: "Campaigns"

Master list of active campaigns for reference.

### Columns

| Column | Header | Description | Example |
|--------|--------|-------------|---------|
| A | Campaign Keyword | What creators type | WinterPromo |
| B | Full Name | Display name | Winter 2025 Promotion |
| C | Posts Required | How many posts needed | 5 |
| D | Payment Amount | Per creator | 50.00 |
| E | Start Date | Campaign start | 2025-01-15 |
| F | End Date | Campaign deadline | 2025-02-15 |
| G | Status | active/paused/complete | active |
| H | Cobrand Campaign ID | For API integration | camp_abc123 |

### Row 1 (Headers)
```
Campaign Keyword | Full Name | Posts Required | Payment Amount | Start Date | End Date | Status | Cobrand Campaign ID
```

---

## Tab 4: "Dashboard" (Optional but Recommended)

Summary view with key metrics.

### Layout

```
Row 1: CAMPAIGN AUTOMATION DASHBOARD
Row 2: Last Updated: [=NOW()]
Row 3: (blank)
Row 4: === REGISTRATIONS ===
Row 5: Total Registered    | [formula]
Row 6: Awaiting Invite     | [formula]
Row 7: In Progress         | [formula]
Row 8: Complete            | [formula]
Row 9: (blank)
Row 10: === PAYMENTS ===
Row 11: Pending Payment    | [formula] | Total: $[formula]
Row 12: Processing         | [formula]
Row 13: Paid This Week     | [formula] | Total: $[formula]
Row 14: Paid All Time      | [formula] | Total: $[formula]
```

### Dashboard Formulas

**Cell B5 - Total Registered:**
```
=COUNTA(Registrations!A:A)-1
```

**Cell B6 - Awaiting Invite:**
```
=COUNTIF(Registrations!F:F, "N") + COUNTIF(Registrations!F:F, "")
```

**Cell B7 - In Progress:**
```
=COUNTIF(Registrations!I:I, "in_progress")
```

**Cell B8 - Complete:**
```
=COUNTIF(Registrations!I:I, "complete")
```

**Cell B11 - Pending Payment Count:**
```
=COUNTIF('Payment Queue'!G:G, "pending")
```

**Cell C11 - Pending Payment Total:**
```
=SUMIF('Payment Queue'!G:G, "pending", 'Payment Queue'!F:F)
```

**Cell B14 - Paid All Time:**
```
=COUNTIF('Payment Queue'!G:G, "sent")
```

**Cell C14 - Paid Total:**
```
=SUMIF('Payment Queue'!G:G, "sent", 'Payment Queue'!F:F)
```

---

## Zapier Integration Notes

### Webhook Data Expected from ManyChat

**Registration webhook sends:**
```json
{
  "campaign_name": "WinterPromo",
  "creator_email": "creator@email.com",
  "tiktok_username": "@musicfan123",
  "manychat_id": "12345678"
}
```

**Payment webhook sends:**
```json
{
  "campaign_name": "WinterPromo",
  "tiktok_username": "@musicfan123",
  "paypal_email": "payment@email.com",
  "manychat_id": "12345678"
}
```

### Zapier Column Mapping

**Zap 1: Registration → Registrations tab**
- Column A (Timestamp): Use Zapier's `{{zap_meta_human_now}}`
- Column B (Campaign): `{{campaign_name}}`
- Column C (Creator Email): `{{creator_email}}`
- Column D (TikTok Username): `{{tiktok_username}}`
- Column E (ManyChat ID): `{{manychat_id}}`
- Column F (Cobrand Invited): Leave blank or "N"
- Column I (Status): "registered"
- Column J (Date Registered): Use `{{zap_meta_human_now}}`

**Zap 2: Payment Info → Payment Queue tab**
- Column A (Timestamp): Use `{{zap_meta_human_now}}`
- Column B (Campaign): `{{campaign_name}}`
- Column C (TikTok Username): `{{tiktok_username}}`
- Column E (PayPal Email): `{{paypal_email}}`
- Column G (Payment Status): "pending"

---

## Quick Setup Checklist

- [ ] Create new Google Sheet
- [ ] Rename to "Campaign Automation Tracker"
- [ ] Create Tab 1: Registrations (add headers)
- [ ] Create Tab 2: Payment Queue (add headers)
- [ ] Create Tab 3: Campaigns (add your campaign list)
- [ ] Create Tab 4: Dashboard (optional)
- [ ] Add data validation to Status columns
- [ ] Add conditional formatting
- [ ] Share sheet with team members
- [ ] Copy sheet URL for Zapier integration
