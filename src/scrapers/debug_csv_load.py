"""Debug CSV loading"""
import csv

csv_path = r'C:\Users\jakeb\OneDrive\Desktop\Tracker-Warner-jake-onboarding\output\campaigns\JYT_Say_Less.csv'

with open(csv_path, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    print("Headers:", reader.fieldnames)
    for i, row in enumerate(reader):
        print(f"\nRow {i}:")
        for k, v in row.items():
            print(f"  {k!r}: {v!r}")
        if i >= 1:
            break
