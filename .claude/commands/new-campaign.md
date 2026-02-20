# Create New Campaign

Set up a new campaign CSV for tracking.

## Campaign Details: $ARGUMENTS

If arguments provided, parse them. Otherwise ask for:
1. Campaign/Song name
2. Artist name
3. TikTok account URLs (comma-separated or one per line)

## Steps:

1. Create campaign CSV file in data/campaigns/
2. Use format: `Song,Artist,Account`
3. Validate all TikTok URLs are properly formatted
4. Save as `{song_name_snake_case}_campaign.csv`
5. Offer to run initial scrape of the campaign

## Example Output File:
```csv
Song,Artist,Account
Song Name,Artist Name,https://www.tiktok.com/@account1
Song Name,Artist Name,https://www.tiktok.com/@account2
```
