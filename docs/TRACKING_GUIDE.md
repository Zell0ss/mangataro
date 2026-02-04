# Chapter Tracking Guide

This guide explains how to use the chapter tracking system to automatically fetch new manga chapters from scanlator websites.

## Overview

The tracking system uses the scanlator plugin architecture to:
1. Query the database for active manga-scanlator mappings
2. Fetch chapters from each scanlator website
3. Insert new chapters into the database
4. Log errors and provide detailed reports

## Prerequisites

Before you can track chapters, you need:

1. **Active scanlator plugins** - At least one scanlator plugin implemented (e.g., `AsuraScans`)
2. **Verified manga-scanlator mappings** - Manga sources added and manually verified
3. **Database setup** - Database schema created and configured

### Setting Up Scanlator Plugins

Scanlator plugins must:
- Inherit from `BaseScanlator`
- Implement `obtener_capitulos(manga_url)` method
- Be placed in the `scanlators/` directory
- Have the correct `class_name` stored in the database

Example: `AsuraScans` class → database `class_name` should be `"AsuraScans"`

### Adding Manga Sources

Use the interactive script to add manga-scanlator mappings:

```bash
python scripts/add_manga_source.py
```

This will:
1. Show you all available mangas
2. Let you select a scanlator
3. Prompt for the manga URL on that scanlator's site
4. Mark the mapping as `manually_verified=True`

## Main Tracking Script

### Basic Usage

Track all active manga-scanlator mappings:

```bash
python scripts/track_chapters.py
```

### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--manga-id <id>` | Track only specific manga | `--manga-id 5` |
| `--scanlator-id <id>` | Track only specific scanlator | `--scanlator-id 2` |
| `--limit <n>` | Process only first N mappings | `--limit 5` |
| `--headless` | Run browser in headless mode (default) | `--headless` |
| `--visible` | Run with visible browser for debugging | `--visible` |

### Examples

Track a specific manga:
```bash
python scripts/track_chapters.py --manga-id 42
```

Track all manga from a specific scanlator:
```bash
python scripts/track_chapters.py --scanlator-id 7
```

Test with first 3 mappings:
```bash
python scripts/track_chapters.py --limit 3
```

Debug with visible browser:
```bash
python scripts/track_chapters.py --visible --limit 1
```

### Output

The script provides:
- Progress updates for each manga-scanlator pair
- Count of new chapters found
- Error notifications
- Summary report at the end

Example output:
```
============================================================
CHAPTER TRACKING STARTED
============================================================
Found 25 manga-scanlator mapping(s) to track

[1/25] ==================================================
Processing: Solo Leveling @ Asura Scans
Found 201 chapters on site
New chapter inserted: Solo Leveling - Ch. 200 (ID: 1234)
New chapter inserted: Solo Leveling - Ch. 201 (ID: 1235)

[2/25] ==================================================
Processing: One Piece @ Asura Scans
Found 150 chapters on site

============================================================
TRACKING COMPLETE!
============================================================
Manga-scanlator pairs checked: 25
New chapters found: 42
Errors: 0

Top updates:
  - Solo Leveling: 5 new chapters
  - One Piece: 3 new chapters
  - Naruto: 2 new chapters
============================================================
```

## Test Script

### Basic Usage

Test the tracking system with a limited dataset:

```bash
python scripts/test_tracking.py
```

### What It Tests

The test script verifies:
1. **Database state** - Shows current mangas, scanlators, and chapters
2. **Chapter fetching** - Runs tracking on 1-2 mappings
3. **Database insertion** - Verifies chapters were inserted correctly
4. **Duplicate detection** - Tests that duplicates are rejected
5. **Idempotency** - Runs tracking again to ensure duplicates are skipped

### Command-Line Options

| Option | Description |
|--------|-------------|
| `--visible` | Run with visible browser for debugging |
| `--skip-tracking` | Only check database state (no tracking) |

### Examples

Run full test suite:
```bash
python scripts/test_tracking.py
```

Check database state only:
```bash
python scripts/test_tracking.py --skip-tracking
```

Debug with visible browser:
```bash
python scripts/test_tracking.py --visible
```

### Expected Output

```
============================================================
CHAPTER TRACKING TEST SUITE
============================================================

STEP 1: Pre-tracking database check
Total mangas: 94
Total scanlators: 28 (1 active)
Manga-scanlator mappings: 95 (1 verified)
Total chapters: 0

STEP 2: Running tracking test
Processing: Solo Leveling @ Asura Scans
Found 199 chapters on site

STEP 3: Verifying chapters were inserted
Verification for: Solo Leveling @ Asura Scans
Chapters in database: 199
✓ Verification passed!

STEP 4: Testing duplicate detection
✓ PASSED: Duplicate chapter was rejected as expected

STEP 5: Running tracking again (should skip duplicates)
Processing: Solo Leveling @ Asura Scans
Found 201 chapters on site
New chapters found: 0

TEST SUMMARY
Total chapters: 199
Test complete!
```

## Database Schema

### Chapters Table

Chapters are stored with the following structure:

```sql
CREATE TABLE chapters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_scanlator_id INT NOT NULL,
    chapter_number VARCHAR(20) NOT NULL,
    chapter_title VARCHAR(255),
    chapter_url VARCHAR(500) NOT NULL,
    published_date DATETIME,
    detected_date DATETIME NOT NULL,
    read BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME,
    FOREIGN KEY (manga_scanlator_id) REFERENCES manga_scanlator(id),
    UNIQUE KEY unique_chapter (manga_scanlator_id, chapter_number)
);
```

Key points:
- `manga_scanlator_id` links to the manga-scanlator mapping (not directly to manga)
- `chapter_number` is stored as VARCHAR to support formats like "42.5"
- Unique constraint on `(manga_scanlator_id, chapter_number)` prevents duplicates
- `published_date` is the date from the scanlator site (if available)
- `detected_date` is when we first discovered the chapter

### Scraping Errors Table

Errors are logged to help debug issues:

```sql
CREATE TABLE scraping_errors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manga_scanlator_id INT,
    error_type VARCHAR(50),
    error_message TEXT,
    timestamp DATETIME NOT NULL,
    resolved BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (manga_scanlator_id) REFERENCES manga_scanlator(id)
);
```

## Error Handling

The tracking system handles errors gracefully:

1. **Per-mapping errors** - If one manga-scanlator fails, tracking continues with the next
2. **Error logging** - All errors are logged to the `scraping_errors` table
3. **Retry logic** - The `safe_goto()` method in plugins handles retries
4. **Duplicate handling** - Database unique constraints prevent duplicate chapters

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Plugin not found` | `class_name` doesn't match actual class | Update database `class_name` to match plugin class |
| `HTTP 404` | Manga URL is incorrect or manga removed | Update URL in database or mark as inactive |
| `Timeout` | Website is slow or blocking | Increase `PLAYWRIGHT_TIMEOUT` in `.env` |
| `No chapters found` | Selectors changed on website | Update scanlator plugin selectors |

## Configuration

Environment variables in `.env`:

```bash
# Scraping settings
PLAYWRIGHT_TIMEOUT=30000        # Timeout for page loads (ms)
SCRAPING_DELAY_MIN=2           # Minimum delay between requests (seconds)
SCRAPING_DELAY_MAX=5           # Maximum delay between requests (seconds)
USER_AGENT=Mozilla/5.0 ...     # User agent string
```

## Scheduling

To run tracking automatically, set up a cron job:

```bash
# Run tracking every 6 hours
0 */6 * * * cd /data/mangataro && /usr/bin/python3 scripts/track_chapters.py >> /data/mangataro/logs/cron_tracking.log 2>&1

# Run tracking daily at 3 AM
0 3 * * * cd /data/mangataro && /usr/bin/python3 scripts/track_chapters.py >> /data/mangataro/logs/cron_tracking.log 2>&1
```

## Troubleshooting

### No chapters found

Check:
1. URL is correct: `python scripts/test_tracking.py --visible`
2. Scanlator plugin is working: Test with the plugin's test script
3. Selectors are up-to-date: Websites change their HTML structure

### Duplicate chapters

The unique constraint should prevent duplicates, but if you see them:
1. Check `manga_scanlator_id` is correct
2. Verify `chapter_number` parsing is consistent
3. Look for race conditions (unlikely with single-threaded tracking)

### Plugin not found

Ensure:
1. Plugin file exists in `scanlators/` directory
2. Plugin class inherits from `BaseScanlator`
3. Database `class_name` matches the actual class name exactly

### Performance issues

To improve performance:
1. Increase `SCRAPING_DELAY_MIN/MAX` to avoid rate limiting
2. Use `--limit` to process fewer mappings at once
3. Run in headless mode (default)
4. Check your internet connection

## Best Practices

1. **Test first** - Use `test_tracking.py` before running full tracking
2. **Monitor errors** - Check `scraping_errors` table regularly
3. **Update URLs** - Keep manga URLs current as sites change
4. **Verify mappings** - Only track manually verified mappings
5. **Use delays** - Respect scanlator sites with appropriate delays
6. **Log everything** - Logs are in `/data/mangataro/logs/`
7. **Backup database** - Before running tracking on many mangas

## Next Steps

1. Add more scanlator plugins (see `scanlators/template.py`)
2. Add more manga sources with `add_manga_source.py`
3. Set up cron jobs for automatic tracking
4. Build a notification system for new chapters
5. Create a web UI to manage manga and chapters
