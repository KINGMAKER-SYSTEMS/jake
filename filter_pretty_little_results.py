import csv
from pathlib import Path

# Read the results CSV
results_file = Path('output/Pretty_Little_Cameron_Whitcomb_campaign_results_20251209_091850.csv')
copy_paste_file = Path('output/Pretty_Little_Cameron_Whitcomb_copy_paste.txt')

target_accounts = ['@nicholaskuniec', '@enzowms']

with open(results_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    filtered_videos = [row for row in reader if row['account'] in target_accounts]

print(f"Found {len(filtered_videos)} videos from @nicholaskuniec and @enzowms")

# Group by account
by_account = {}
for video in filtered_videos:
    account = video['account']
    if account not in by_account:
        by_account[account] = []
    by_account[account].append(video)

for account, videos in by_account.items():
    print(f"  {account}: {len(videos)} videos")

# Write copy/paste file
with open(copy_paste_file, 'w', encoding='utf-8') as f:
    for account in target_accounts:
        if account in by_account:
            f.write(f"\n{account}\n")
            f.write("-" * 80 + "\n")
            for video in by_account[account]:
                f.write(f"{video['url']}\n")

print(f"\nCopy/paste file created: {copy_paste_file}")

