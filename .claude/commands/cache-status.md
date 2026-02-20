# Cache Status

Check the status and health of scraper caches.

## Steps:

1. List all pickle files in cache/ directory
2. For each cache file:
   - Show file size
   - Show last modified time
   - Try to load and count videos
   - Report any corrupted files
3. Summarize:
   - Total cached accounts
   - Total cached videos
   - Oldest cache timestamp
   - Newest cache timestamp
   - Any accounts missing from config that have caches
   - Any accounts in config missing caches

## Output Format:
```
Account          | Videos | Last Updated     | Size
-----------------+--------+------------------+--------
@beaujenkins     | 100    | 2025-01-18 14:30 | 245 KB
@codyjames6.7    | 87     | 2025-01-18 14:32 | 198 KB
...
```
