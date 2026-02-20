#!/usr/bin/env python3
"""
Robust Campaign Scraper - Wrapper for master_tracker.py
Automatically adjusts video limit based on date range
"""

import sys
from pathlib import Path
from datetime import datetime

# Import from master_tracker
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'scrapers'))
from master_tracker import main

if __name__ == '__main__':
    main()

