# Generate Reports

Generate reports from scraped data.

## Format: $ARGUMENTS

Based on the format argument:

1. **"html"**: Generate HTML report using src/reports/generate_complete_html.py
2. **"excel"**: Generate Excel report using src/reports/generate_song_excel.py
3. **"csv"**: Generate CSV reports using src/reports/generate_csv_report.py
4. **"all"**: Generate all report formats
5. **No argument**: Generate HTML report (default)

## Steps:
1. Check that scraped data exists in output/ or cache/
2. Run the appropriate report generator
3. Report the output file location
4. Offer to open the file if on Windows/Mac
