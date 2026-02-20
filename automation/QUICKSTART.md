# 🚀 Quick Start - Cobrand Automation Test

## Run These Commands (In Order)

### 1️⃣ Install Playwright
```bash
python -m pip install playwright
python -m playwright install chromium
```

OR just double-click: `setup_playwright.bat`

---

### 2️⃣ Run the Test
```bash
python automation/cobrand_browser_test.py
```

---

### 3️⃣ First Run: Login Manually

When the browser opens:
1. Login to Cobrand (email: jake@risingtidesent.com)
2. Wait for Promotions page to load
3. Go back to terminal, press ENTER
4. ✅ Cookies saved! Future runs will auto-login

---

### 4️⃣ Check Results

Files created:
- `automation/cobrand_screenshot.png` - What the script sees
- `automation/campaigns_extracted.json` - Extracted data
- `automation/cobrand_cookies.pkl` - Saved session (private!)

---

## ✅ What This Proves

If this works, we can automate:
- ✅ Login to Cobrand without password
- ✅ Navigate to campaigns
- ✅ Extract campaign data
- ✅ Identify status emojis (green ✅ vs gray ✅)
- ✅ Get creator lists

Then we integrate with Clawdbot for scheduled daily runs!

---

## 🆘 Troubleshooting

**"playwright not found"**
→ Run: `python -m pip install playwright`

**"chromium not installed"**
→ Run: `python -m playwright install chromium`

**"Login failed"**
→ Make sure you're on the Promotions page before pressing ENTER

**Browser closes too fast**
→ Normal! Check the JSON file for extracted data
