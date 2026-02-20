import csv
import re
from collections import defaultdict

csv_path = r"C:\Users\jakeb\OneDrive\Desktop\Tracker-Warner-jake-onboarding\output\campaigns\Malcom_Todd_Dougie_Mashup.csv"

sound_ids = set()
sound_keys = set()

print(f"Loading: {csv_path}")

with open(csv_path, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    
    for row in reader:
        print(f"\nRow: {dict(row)}")
        
        # Extract sound ID
        sound_id = None
        for col in ['Tiktok Sound ID', 'Tiktok Sound', 'Sound ID', 'sound_id']:
            if col in row and row[col]:
                sound_url = row[col].strip()
                print(f"  Checking column '{col}': {sound_url}")
                
                patterns = [
                    r'original-sound-(\d+)',
                    r'song-(\d+)',
                    r'music/[^-]+-(\d+)',
                    r'-(\d+)$'
                ]
                for pattern in patterns:
                    match = re.search(pattern, sound_url)
                    if match:
                        sound_id = match.group(1)
                        print(f"    Matched pattern '{pattern}': {sound_id}")
                        break
                
                # If no pattern matched but it's just a number, use it directly
                if not sound_id and sound_url.isdigit():
                    sound_id = sound_url
                    print(f"    Direct number: {sound_id}")
                    
                if sound_id:
                    break
        
        if sound_id:
            sound_ids.add(sound_id)
            print(f"  Added sound ID: {sound_id}")
        else:
            print(f"  NO SOUND ID EXTRACTED!")

print(f"\n\nFinal sound_ids: {sound_ids}")
