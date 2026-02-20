"""Run scraper for Say Less campaign"""
from datetime import datetime
from master_tracker import process_campaign

results = process_campaign(
    r'C:\Users\jakeb\OneDrive\Desktop\Tracker-Warner-jake-onboarding\output\campaigns\JYT_Say_Less.csv',
    platform='tiktok',
    start_date=datetime(2026, 1, 23).date(),
    workers=5
)

print(f'\n\nRESULTS SUMMARY:')
print(f'Total videos scraped: {results["total_videos_scraped"]}')
print(f'Matched videos: {results["matched_videos"]}')

if results['videos']:
    print(f'\nMATCHED VIDEOS:')
    for v in results['videos']:
        print(f"  {v['url']}")
        print(f"    Account: {v['account']}")
        print(f"    Views: {v.get('views', 'N/A')}")
        print(f"    Date: {v.get('upload_date', 'N/A')}")
