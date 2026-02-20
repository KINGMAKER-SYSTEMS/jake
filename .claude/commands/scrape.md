# Scrape Campaign or Accounts

Run TikTok/Instagram scraping based on the target specified.

## Target: $ARGUMENTS

Based on the target argument:

1. **If a campaign CSV path is provided**: Run master_tracker.py with that campaign
2. **If "warner" is specified**: Run scrape_warner_accounts.py
3. **If an account username is provided**: Scrape that specific account
4. **If no argument**: Ask what to scrape

## Steps:
1. Identify the scraping target from the argument
2. Run the appropriate scraper script
3. Report results including:
   - Number of accounts scraped
   - Total videos found
   - Any errors encountered
4. Suggest generating reports if scrape was successful
