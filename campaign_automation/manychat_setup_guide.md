# ManyChat Setup Guide - Campaign Automation

## Prerequisites Checklist

- [x] ManyChat account created
- [ ] TikTok Business account connected (Rising Tides)
- [ ] Zapier account created
- [ ] Google Sheet created (see google_sheet_template.md)

---

## Part 1: Connect TikTok to ManyChat

### Step 1.1: Access Channel Settings
1. Log into ManyChat dashboard
2. Click **Settings** (gear icon, bottom left)
3. Click **Channels** in the left menu
4. Find **TikTok** section

### Step 1.2: Connect TikTok Account
1. Click **Connect** next to TikTok
2. You'll be redirected to TikTok login
3. Log in with the **Rising Tides** account credentials
4. Click **Authorize** to grant ManyChat access
5. Return to ManyChat - should show "Connected"

⚠️ **If you see an error about account type:**
- Go to TikTok app → Profile → Menu (☰) → Settings → Account
- Click "Switch to Business Account"
- Select a business category (Entertainment, Music, etc.)
- Try connecting again

---

## Part 2: Create Custom Fields

### Step 2.1: Access Custom Fields
1. In ManyChat, go to **Settings** → **Custom Fields**
2. Click **+ New User Field** for each field below

### Step 2.2: Create These Fields

| Field Name | Field Type | Default Value |
|------------|------------|---------------|
| campaign_name | Text | (leave empty) |
| creator_email | Text | (leave empty) |
| paypal_email | Text | (leave empty) |
| registration_status | Text | new |
| completion_campaign | Text | (leave empty) |

**For each field:**
1. Click **+ New User Field**
2. Enter the Field Name exactly as shown
3. Select the Type
4. Click **Create**

---

## Part 3: Build Registration Flow

### Step 3.1: Create New Flow
1. Go to **Automation** → **Flows** (left sidebar)
2. Click **+ New Flow**
3. Name it: `Campaign Registration`
4. Click **Create**

### Step 3.2: Add Trigger
1. In the flow editor, click **Add Trigger**
2. Select **TikTok**
3. Choose **User Sends Message**
4. Configure the trigger:
   - **Message Type**: Contains keyword
   - **Keywords**: Add each campaign keyword on a new line:
     ```
     WinterPromo
     SpringLaunch
     SummerVibes
     ```
     (Add all your campaign keywords)
   - Check **Case insensitive**

### Step 3.3: Build the Flow Steps

**Starting Point → Condition Block**

1. Click the **+** after the trigger
2. Select **Condition**
3. Set up the condition to check for email:
   - Condition: **User Message** → **Contains** → `@`
   - Add another condition (AND): **User Message** → **Contains** → `.`

This checks if their message likely contains an email.

**Branch 1: No Email Found**

1. On the "Does Not Match" branch, click **+**
2. Select **Send Message**
3. Message type: **Text**
4. Enter this message:
```
Thanks for reaching out!

To register, please reply with the campaign name AND your email address.

Example:
WinterPromo you@email.com
```

5. After this message, click **+**
6. Select **Wait for User Reply**
7. After wait, connect back to the condition block (drag the connection)

**Branch 2: Email Found**

1. On the "Matches" branch, click **+**
2. Select **Action** → **Set Custom Field**
3. Configure:
   - Field: `campaign_name`
   - Value: Click the **{x}** button, then select **Matched Keyword** (this captures which campaign keyword triggered the flow)

4. Click **+** again
5. Select **Action** → **Set Custom Field**
6. Configure:
   - Field: `creator_email`
   - Value: We need to extract email from message. Use **User Message** and ManyChat will attempt to parse it, OR you can use regex if available

**Note on Email Extraction:**
ManyChat's basic plan may not have advanced text parsing. Workaround:
- Ask them to send JUST the email in a follow-up message
- Or use the full message and manually parse in Zapier

**Alternative Simpler Flow:**

If email extraction is tricky, use this 2-message approach:

```
[Trigger: Campaign keyword]
        ↓
[Send Message: "Got it! Please reply with JUST your email address:"]
        ↓
[Wait for Reply]
        ↓
[Set Custom Field: creator_email = User Reply]
[Set Custom Field: campaign_name = Matched Keyword]
        ↓
[External Request to Zapier]
        ↓
[Send Message: "You're registered! Check your email for the Cobrand link."]
```

### Step 3.4: Add External Request (Webhook to Zapier)

1. After setting custom fields, click **+**
2. Select **Action** → **External Request**
3. Configure:
   - **Request Type**: POST
   - **URL**: (You'll get this from Zapier - leave blank for now, see Part 5)
   - **Headers**:
     - Key: `Content-Type`
     - Value: `application/json`
   - **Body** (JSON):
   ```json
   {
     "campaign_name": "{{campaign_name}}",
     "creator_email": "{{creator_email}}",
     "tiktok_username": "{{tiktok_username}}",
     "manychat_id": "{{user_id}}",
     "timestamp": "{{current_date}}"
   }
   ```

   Use the **{x}** button to insert the actual field variables.

### Step 3.5: Add Confirmation Message

1. After the External Request, click **+**
2. Select **Send Message**
3. Message:
```
You're registered for {{campaign_name}}! 🎉

Check your email ({{creator_email}}) for your Cobrand upload link.

Once you've uploaded all your posts, reply:
DONE {{campaign_name}}

to submit for payment!
```

### Step 3.6: Publish the Flow
1. Click **Publish** (top right)
2. Confirm to make it live

---

## Part 4: Build Completion & Payment Flow

### Step 4.1: Create New Flow
1. Go to **Automation** → **Flows**
2. Click **+ New Flow**
3. Name it: `Completion and Payment`
4. Click **Create**

### Step 4.2: Add Trigger
1. Click **Add Trigger**
2. Select **TikTok** → **User Sends Message**
3. Configure:
   - **Keywords**:
     ```
     DONE
     COMPLETE
     FINISHED
     ```
   - Check **Case insensitive**

### Step 4.3: Check for Campaign Specification

1. Add **Condition** after trigger
2. Check if message contains a campaign keyword:
   - **User Message** → **Contains** → `WinterPromo`
   - OR **User Message** → **Contains** → `SpringLaunch`
   - (Add OR conditions for each campaign)

**If No Campaign Specified:**
```
[Send Message]
"Which campaign are you done with?

Reply like: DONE WinterPromo"

[Wait for Reply]
→ Loop back to check condition
```

**If Campaign Found:**
```
[Set Custom Field: completion_campaign = extracted campaign]
```

### Step 4.4: Verification Step (For Now - Manual)

Since we don't have Cobrand API yet, we'll trust the creator and proceed:

1. Add **Send Message**:
```
Thanks for completing {{completion_campaign}}! ✅

To receive your payment, please reply with your PayPal email address:
```

2. Add **Wait for User Reply**

3. Add **Set Custom Field**:
   - Field: `paypal_email`
   - Value: **User Reply**

4. Add **External Request** (to Zapier):
   - POST to your payment webhook URL
   - Body:
   ```json
   {
     "campaign_name": "{{completion_campaign}}",
     "tiktok_username": "{{tiktok_username}}",
     "paypal_email": "{{paypal_email}}",
     "manychat_id": "{{user_id}}",
     "timestamp": "{{current_date}}"
   }
   ```

5. Add **Send Message**:
```
Got it! 💰

PayPal: {{paypal_email}}
Campaign: {{completion_campaign}}

Payments are processed weekly. You'll receive a message when your payment has been sent!

Thanks for being part of the campaign! 🙌
```

### Step 4.5: Publish
1. Click **Publish**

---

## Part 5: Set Up Zapier Webhooks

### Step 5.1: Create Registration Zap

1. Go to [zapier.com](https://zapier.com) and log in
2. Click **+ Create Zap**

**Trigger:**
1. Search for **Webhooks by Zapier**
2. Select **Catch Hook**
3. Click **Continue**
4. **Copy the webhook URL** (looks like: `https://hooks.zapier.com/hooks/catch/xxxxx/xxxxx/`)
5. **Go back to ManyChat** and paste this URL in your Registration flow's External Request
6. **Test the trigger:** Send a test message to your TikTok
7. Return to Zapier and click **Test trigger** - it should find your test data

**Action:**
1. Click **+** to add action
2. Search for **Google Sheets**
3. Select **Create Spreadsheet Row**
4. Connect your Google account
5. Select your "Campaign Automation Tracker" spreadsheet
6. Select the "Registrations" worksheet
7. Map the fields:
   - Timestamp: `{{zap_meta_human_now}}`
   - Campaign: `{{campaign_name}}`
   - Creator Email: `{{creator_email}}`
   - TikTok Username: `{{tiktok_username}}`
   - ManyChat ID: `{{manychat_id}}`
   - Status: `registered`

8. Click **Test action** to verify it creates a row
9. Click **Publish Zap**

### Step 5.2: Create Payment Zap

Repeat the process:

1. **+ Create Zap**
2. **Trigger**: Webhooks by Zapier → Catch Hook
3. Copy this webhook URL to ManyChat's payment flow External Request
4. **Action**: Google Sheets → Create Spreadsheet Row
5. Select "Payment Queue" worksheet
6. Map fields:
   - Timestamp: `{{zap_meta_human_now}}`
   - Campaign: `{{campaign_name}}`
   - TikTok Username: `{{tiktok_username}}`
   - PayPal Email: `{{paypal_email}}`
   - Payment Status: `pending`

7. **Publish Zap**

---

## Part 6: Testing Checklist

### Test 1: Registration Flow
- [ ] From a test TikTok account, DM Rising Tides: "WinterPromo"
- [ ] Receive prompt for email
- [ ] Reply with email: "test@example.com"
- [ ] Receive confirmation message
- [ ] Check Google Sheet - row appears in Registrations tab

### Test 2: Completion Flow
- [ ] From test account, DM: "DONE WinterPromo"
- [ ] Receive prompt for PayPal email
- [ ] Reply with PayPal: "testpaypal@example.com"
- [ ] Receive confirmation message
- [ ] Check Google Sheet - row appears in Payment Queue tab

### Test 3: Edge Cases
- [ ] Try "winterpromo" (lowercase) - should still work
- [ ] Try "DONE" without campaign - should ask which campaign
- [ ] Try gibberish - should not trigger (good - no false positives)

---

## Troubleshooting

### "TikTok not connecting"
- Ensure account is Business type, not Creator
- Check if you're in EU/UK (ManyChat TikTok not available there)
- Try disconnecting and reconnecting

### "Webhook not firing"
- Check External Request URL is correct
- Verify the flow is Published (not just saved)
- Check Zapier's "Zap History" for errors

### "Email not capturing correctly"
- Use the 2-step approach (ask for email separately)
- Check the custom field is set up correctly

### "Sheet not updating"
- Verify Google Sheets connection in Zapier
- Check column mappings match your sheet exactly
- Look at Zap History for error messages

---

## Next Steps After Setup

1. **Add all campaign keywords** to both flows
2. **Create Campaigns tab** with payment amounts per campaign
3. **Set up weekly payment processing routine**
4. **When you get Cobrand API**: Replace manual invite process with API call in Zapier
