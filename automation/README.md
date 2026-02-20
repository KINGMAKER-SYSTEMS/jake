# Cobrand Automation - Proof of Concept

This folder contains the browser automation test for Cobrand integration.

## 🎯 Goal

Test if we can automate:
1. ✅ Login to Cobrand
2. ✅ Extract campaign data
3. ✅ Identify campaigns by status emoji (green ✅ vs gray ✅ vs none)
4. ✅ Extract creator lists from campaigns

## 📋 Setup Instructions

### Step 1: Install Playwright

Double-click `setup_playwright.bat` or run in terminal:

```bash
python -m pip install playwright
python -m playwright install chromium
```

### Step 2: Run the Test Script

```bash
python automation/cobrand_browser_test.py
```

### Step 3: First Run - Manual Login

1. A browser window will open
2. Login to Cobrand with your credentials:
   - Email: `jake@risingtidesent.com`
   - Password: (your saved browser password)
3. Wait until you see the Promotions page
4. Go back to terminal and press ENTER
5. The script will save your session cookies

### Step 4: Future Runs - Auto Login

The script will reuse saved cookies - no manual login needed!

## 📁 Files Created

- `cobrand_cookies.pkl` - Saved login session (keep private!)
- `cobrand_screenshot.png` - Screenshot of Promotions page
- `campaigns_extracted.json` - Extracted campaign data

## 🔍 What This Tests

1. **Cookie persistence** - Can we save/reuse login sessions?
2. **Page navigation** - Can we access Promotions page?
3. **Data extraction** - Can we read campaign titles and status?
4. **Bot detection** - Does Cobrand block automation?

## ✅ Success Criteria

If this works, we can build:
- Automated campaign status checking
- Creator list extraction
- Scheduled scraping via Clawdbot
- Auto-upload of results

## 🚀 Next Steps After Testing

1. Refine HTML selectors for campaign data
2. Add emoji detection (green ✅ vs gray ✅)
3. Extract creator usernames from campaign details
4. Integrate with existing scrapers
5. Set up Clawdbot for scheduled automation

## 🔒 Security Note

The `cobrand_cookies.pkl` file contains your login session.
**Do not commit this file to git!**

It's already in `.gitignore` for safety.
