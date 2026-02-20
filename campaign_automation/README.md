# Campaign Automation System

Automates creator registration, post verification, and payment collection for music campaigns using ManyChat (TikTok DM automation), Zapier (integration layer), and Google Sheets (tracking).

## Quick Start Checklist

```
[ ] 1. Switch Rising Tides TikTok to Business Account
[ ] 2. Connect TikTok to ManyChat (Settings → Channels → TikTok)
[ ] 3. Create custom fields in ManyChat (see guide)
[ ] 4. Create Google Sheet from template
[ ] 5. Create Zapier account and set up webhooks
[ ] 6. Build Registration flow in ManyChat
[ ] 7. Build Completion/Payment flow in ManyChat
[ ] 8. Test with a test TikTok account
[ ] 9. Add all campaign keywords
```

## System Overview

```
Creator DMs Rising Tides          ManyChat                    Zapier                 Google Sheet
─────────────────────────         ────────                    ──────                 ────────────
"WinterPromo me@email.com"   →    Captures data          →    Webhook fires     →    New row in
                                  Confirms registration        Processes data          Registrations

"DONE WinterPromo"           →    Asks for PayPal       →    (future: verify   →
                                                              with Cobrand)

"pay@paypal.com"             →    Captures PayPal       →    Webhook fires     →    New row in
                                  Confirms submission          Processes data          Payment Queue
```

## Files in This Folder

| File | Description |
|------|-------------|
| `README.md` | This overview |
| `manychat_setup_guide.md` | Step-by-step ManyChat configuration |
| `google_sheet_template.md` | Sheet structure and formulas |

## Current Capabilities (Phase 1)

✅ **Automated:**
- Creator registration via TikTok DM
- Campaign keyword detection
- Email capture
- PayPal email collection
- Logging to Google Sheets

❌ **Manual (until Cobrand API):**
- Sending Cobrand invite links
- Verifying post completion
- Processing payments

## Future Enhancements (Phase 2 - With Cobrand API)

- Auto-trigger Cobrand invites when creator registers
- Auto-detect when all posts are submitted
- Auto-trigger payment flow on completion
- PayPal Payouts API for batch payments

## Campaigns Setup

Add campaign keywords to:
1. ManyChat Registration flow trigger
2. ManyChat Completion flow condition
3. Google Sheet "Campaigns" tab

## Weekly Payment Process

1. Open Google Sheet → Payment Queue tab
2. Filter by Status = "pending"
3. Process payments in PayPal
4. Update Status to "sent" and add Transaction ID
5. (Future: Trigger ManyChat confirmation message)

## Support

- ManyChat Help: https://help.manychat.com
- Zapier Help: https://help.zapier.com
- TikTok Business: https://www.tiktok.com/business
