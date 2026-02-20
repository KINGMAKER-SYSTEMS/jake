"""Run scraper for Sombr Original Sound campaign"""
from datetime import datetime
from master_tracker import process_campaign

results = process_campaign(
    r'C:\Users\jakeb\OneDrive\Desktop\Tracker-Warner-jake-onboarding\output\campaigns\Sombr_Original_Sound.csv',
    platform='tiktok',
    start_date=datetime(2026, 2, 2).date(),  # Campaign created Feb 2
    workers=5
)

print(f'\n\nRESULTS SUMMARY:')
print(f'Total videos scraped: {results["total_videos_scraped"]}')
print(f'Matched videos: {results["matched_videos"]}')

if results['videos']:
    print(f'\nMATCHED VIDEOS:')
    for v in results['videos']:
        print(f"  {v['url']}")
