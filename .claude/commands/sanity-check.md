# Sanity Check

Run code quality checks on the project.

## Steps:

1. **Python Syntax Check**: Run `python -m py_compile` on key files
2. **Import Check**: Verify all imports resolve correctly
3. **Config Validation**: Check that config.py has required fields
4. **Cache Health**: Check cache/ directory for any corrupted pickle files
5. **Dependencies**: Verify yt-dlp and other tools are available

## Key Files to Check:
- src/scrapers/master_tracker.py
- src/scrapers/scrape_warner_accounts.py
- src/utils/config.py
- src/reports/generate_complete_html.py

Report any issues found with suggested fixes.
