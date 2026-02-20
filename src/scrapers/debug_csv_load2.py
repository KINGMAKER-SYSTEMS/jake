"""Debug CSV loading - trace exact logic"""
import csv
import re
from collections import defaultdict

csv_path = r'C:\Users\jakeb\OneDrive\Desktop\Tracker-Warner-jake-onboarding\output\campaigns\JYT_Say_Less.csv'

sound_ids = set()
accounts_by_sound = defaultdict(set)

with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    
    for row in reader:
        print(f"\nProcessing row: {row['creator_name']}")
        
        # Extract sound ID - same logic as master_tracker
        sound_id = None
        for col in ['Tiktok Sound ID', 'Tiktok Sound', 'Sound ID', 'sound_id']:
            if col in row and row[col]:
                sound_url = row[col].strip()
                print(f"  Found col '{col}' with value: {sound_url}")
                patterns = [
                    r'original-sound-(\d+)',
                    r'song-(\d+)',
                    r'music/[^-]+-(\d+)',
                    r'-(\d+)$',
                ]
                for pattern in patterns:
                    match = re.search(pattern, sound_url)
                    if match:
                        sound_id = match.group(1)
                        print(f"  Extracted sound_id: {sound_id} using pattern: {pattern}")
                        break
                if sound_id:
                    break
                else:
                    # Maybe it's just a raw ID?
                    if sound_url.isdigit():
                        sound_id = sound_url
                        print(f"  Raw ID found: {sound_id}")
                        break
        
        if sound_id:
            sound_ids.add(sound_id)
            print(f"  Added to sound_ids: {sound_id}")
        else:
            print(f"  NO sound_id found!")
        
        # Extract account
        account = None
        for col in ['Account', 'account', 'Account URL', 'URL', 'account Handle', 'Creator Handles']:
            if col in row and row[col]:
                account = row[col].strip()
                print(f"  Found account: {account}")
                break
        
        if account and sound_id:
            accounts_by_sound[sound_id].add(account)

print(f"\n\nFINAL RESULT:")
print(f"sound_ids: {sound_ids}")
print(f"accounts_by_sound: {dict(accounts_by_sound)}")
