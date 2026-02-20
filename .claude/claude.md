# Warner Sound Tracker - Claude Code Context

## Project Overview
TikTok/Instagram analytics tracker for Warner Music campaigns. Scrapes creator accounts, extracts sound usage data, and generates reports for campaign performance tracking.

## Tech Stack
- **Language**: Python 3.7+
- **Scraping**: yt-dlp (TikTok), Instaloader (Instagram)
- **Web**: Flask (port 5001)
- **Database**: SQLite (optional), Pickle caching
- **Reports**: HTML, Excel (openpyxl), CSV

## Key Directories
```
src/scrapers/     # Main scrapers (master_tracker.py is primary)
src/core/         # Core analyzers and daemon
src/reports/      # HTML/Excel/CSV report generators
src/utils/        # Config and utilities
data/campaigns/   # Campaign CSVs (Song,Artist,Account)
data/accounts/    # Account list CSVs
output/           # Generated reports
cache/            # Pickle cache files per account
```

## Primary Files
- `src/scrapers/master_tracker.py` - Production scraper with parallel processing
- `src/scrapers/scrape_warner_accounts.py` - Warner campaign scraper
- `src/utils/config.py` - Central configuration (accounts, dates, filters)
- `src/reports/generate_complete_html.py` - HTML report generator

## Code Patterns

### Scraping with yt-dlp
```python
cmd = ['yt-dlp', '--flat-playlist', '--dump-json', '--playlist-end', str(limit), url]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
for line in result.stdout.strip().split('\n'):
    video = json.loads(line)
```

### Parallel Processing
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(fn, item): item for item in items}
    for future in tqdm(as_completed(futures), total=len(futures)):
        result = future.result()
```

### Caching
```python
cache_file = Path(f"cache/tiktok_{account}_cache.pkl")
with open(cache_file, 'rb') as f:
    data = pickle.load(f)
```

### Retry Logic
```python
from tenacity import retry, stop_after_attempt, wait_exponential
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
def fetch_data():
    pass
```

## Conventions
- Use `log(message, level)` function for logging with timestamps
- Import config values from `src/utils/config.py`
- Store output in `output/` directory
- Cache scraped data in `cache/` as pickle files
- Campaign CSVs use format: `Song,Artist,Account`
- Account CSVs use format: `URL` header with TikTok/Instagram URLs

## Common Tasks
1. **Scrape accounts**: Run `master_tracker.py` with campaign CSV
2. **Generate reports**: Use `src/reports/` scripts after scraping
3. **Check cache**: Look in `cache/` for `tiktok_*_cache.pkl` files
4. **Update config**: Edit `src/utils/config.py` for accounts/dates/filters

## Performance Notes
- Parallel scraping: 5-10x speedup
- Sound ID caching: 3-5x speedup on re-scrapes
- Early termination: 2x speedup for cached videos
- Typical scrape: 100 videos/account in ~30-60 seconds
