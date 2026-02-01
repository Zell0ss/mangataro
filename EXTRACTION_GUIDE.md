# MangaTaro Extraction Guide

## Overview
This guide explains how to run the MangaTaro extractor script to process all 94 bookmarks from the export file.

## Test Run (Completed)
The test run on the first manga was successful:
- Downloaded cover image: `e04eb3c0-1264-41f4-b7a9-850481803cbf.png`
- Scraped alternative titles and scanlation group from manga page
- Created database entries for manga and scanlator
- Generated markdown ficha: `docs/fichas/girls-x-vampire.md`

## Running the Full Extraction

### Important Notes
- The full extraction will process **94 manga bookmarks**
- With 2-5 second delays between requests, this will take approximately **1-2 hours**
- The script runs in headless browser mode using Playwright
- All progress is logged to `logs/extract_mangataro_*.log`

### Command to Run Full Extraction

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the full extraction
python scripts/extract_mangataro.py
```

### What the Script Does

For each manga bookmark:
1. **Downloads cover image** to `data/img/`
2. **Scrapes the manga page** with Playwright to extract:
   - Alternative titles (paragraph with "/" separators)
   - Scanlation group name (cleaned to remove "X chapters" and "View Group Profile")
3. **Inserts into database**:
   - Creates entry in `mangas` table
   - Finds or creates scanlator in `scanlators` table
   - Links them in `manga_scanlator` table
4. **Generates markdown ficha** in `docs/fichas/{slug}.md`
5. **Waits 2-5 seconds** before processing next manga

After all manga are processed:
- Generates `docs/scanlators.md` with checklist of all scanlators found

### Monitoring Progress

You can monitor the extraction in real-time by tailing the log file:

```bash
# In another terminal
tail -f logs/extract_mangataro_*.log
```

### Output Files

After completion, you'll have:

**Images:**
- `data/img/*.png` or `*.webp` - Cover images

**Markdown Fichas:**
- `docs/fichas/*.md` - One file per manga with info and cover image

**Scanlators Checklist:**
- `docs/scanlators.md` - List of all unique scanlators found

**Database:**
- `mangas` table - All manga entries
- `scanlators` table - All scanlation groups
- `manga_scanlator` table - Relationships between manga and scanlators

### Database Queries

Check extraction results:

```bash
# Count total mangas
mysql -u mangataro_user -pyour_password_here mangataro -e "SELECT COUNT(*) FROM mangas;"

# Count unique scanlators
mysql -u mangataro_user -pyour_password_here mangataro -e "SELECT COUNT(*) FROM scanlators;"

# View all manga titles
mysql -u mangataro_user -pyour_password_here mangataro -e "SELECT title, date_added FROM mangas ORDER BY date_added DESC;"

# View all scanlators
mysql -u mangataro_user -pyour_password_here mangataro -e "SELECT name FROM scanlators ORDER BY name;"
```

### Error Handling

The script is designed to continue even if individual manga fail:
- Errors are logged but don't stop the extraction
- Failed manga are counted in the final summary
- Check the log file for details on any failures

### Re-running the Extraction

If you need to re-run the extraction:

1. **Clear existing data:**
```bash
mysql -u mangataro_user -pyour_password_here mangataro << EOF
DELETE FROM chapters;
DELETE FROM manga_scanlator;
DELETE FROM mangas;
DELETE FROM scanlators;
EOF

rm -f data/img/*
rm -f docs/fichas/*.md
```

2. **Run extraction again:**
```bash
source .venv/bin/activate
python scripts/extract_mangataro.py
```

## Next Steps After Extraction

After the extraction completes:

1. Review `docs/scanlators.md` and identify which scanlators you want to track
2. For each scanlator, create a scraper class in the appropriate directory
3. Update scanlator entries in the database with correct `base_url` and set `active=TRUE`
4. Test scrapers to ensure they can fetch new chapters

## Troubleshooting

**Database connection errors:**
- Ensure MariaDB is running: `systemctl status mariadb`
- Verify credentials in `.env` file

**Playwright errors:**
- Install browsers: `playwright install chromium`
- Check internet connection

**Memory issues:**
- The script processes one manga at a time, so memory should be fine
- If issues occur, you can run in batches by modifying the script

## Script Options

```bash
# Test mode (first manga only)
python scripts/extract_mangataro.py --test

# Full extraction (all manga)
python scripts/extract_mangataro.py

# Custom export file
python scripts/extract_mangataro.py --export-file /path/to/export.json
```
