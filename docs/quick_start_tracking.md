# Quick Start: Chapter Tracking

This guide will get you tracking manga chapters in 5 minutes.

## Step 1: Verify Database Setup

Check your database is ready:

```bash
python scripts/test_tracking.py --skip-tracking
```

You should see:
- Mangas in database
- At least one active scanlator
- At least one verified manga-scanlator mapping

## Step 2: Add a Manga Source (if needed)

If you have no verified mappings, add one:

```bash
python scripts/add_manga_source.py
```

Follow the prompts to:
1. Select a manga
2. Select a scanlator (must be active)
3. Enter the manga's URL on that scanlator's site

**Important**: The `class_name` in the database must match your plugin's class name exactly!

Example:
- Plugin class: `AsuraScans`
- Database `class_name`: `"AsuraScans"` (not "asura_scans")

To fix a mismatch:

```python
from api.database import SessionLocal
from api.models import Scanlator

db = SessionLocal()
scanlator = db.query(Scanlator).filter(Scanlator.name == 'Asura Scans').first()
scanlator.class_name = 'AsuraScans'  # Match the actual class name
db.commit()
db.close()
```

## Step 3: Test Tracking

Test with 1-2 mangas first:

```bash
python scripts/test_tracking.py
```

This will:
- Show database state before and after
- Track chapters from 1-2 verified mappings
- Verify chapters were inserted
- Test duplicate detection
- Run tracking again to ensure idempotency

## Step 4: Run Full Tracking

Track all verified manga-scanlator mappings:

```bash
python scripts/track_chapters.py
```

Or start small:

```bash
# Track first 5 mappings
python scripts/track_chapters.py --limit 5

# Track a specific manga
python scripts/track_chapters.py --manga-id 42

# Track all manga from one scanlator
python scripts/track_chapters.py --scanlator-id 7
```

## Step 5: Verify Results

Check the database:

```python
from api.database import SessionLocal
from api.models import Chapter

db = SessionLocal()
chapter_count = db.query(Chapter).count()
print(f"Total chapters: {chapter_count}")

# See recent chapters
recent = db.query(Chapter).order_by(Chapter.detected_date.desc()).limit(10).all()
for ch in recent:
    print(f"Ch. {ch.chapter_number}: {ch.manga_scanlator.manga.title}")
db.close()
```

## Common Issues

### "Plugin not found"

**Problem**: Database `class_name` doesn't match the actual plugin class name.

**Solution**: Update the database:

```python
from api.database import SessionLocal
from api.models import Scanlator

db = SessionLocal()
scanlator = db.query(Scanlator).filter(Scanlator.id == YOUR_ID).first()
scanlator.class_name = 'ActualClassName'  # e.g., 'AsuraScans'
db.commit()
db.close()
```

### "HTTP 404" or "No chapters found"

**Problem**: Manga URL is incorrect or manga was removed from the site.

**Solution**:
1. Visit the URL in your browser
2. If it's 404, find the correct URL
3. Update the database:

```python
from api.database import SessionLocal
from api.models import MangaScanlator

db = SessionLocal()
mapping = db.query(MangaScanlator).filter(MangaScanlator.id == YOUR_ID).first()
mapping.scanlator_manga_url = 'https://correct-url.com/manga/...'
db.commit()
db.close()
```

### No verified mappings

**Problem**: You need to add manga sources first.

**Solution**: Run `python scripts/add_manga_source.py` and mark mappings as verified.

## What's Next?

1. **Add more scanlators**: Create plugins for your favorite scanlation sites
2. **Automate tracking**: Set up a cron job to run tracking regularly
3. **Build notifications**: Get alerts when new chapters are released
4. **Create a UI**: Build a web interface to manage your manga library

See `docs/tracking_guide.md` for detailed documentation.

## Quick Command Reference

```bash
# Test tracking system
python scripts/test_tracking.py

# Track all verified mappings
python scripts/track_chapters.py

# Track with limit (testing)
python scripts/track_chapters.py --limit 5

# Track specific manga
python scripts/track_chapters.py --manga-id 42

# Track specific scanlator
python scripts/track_chapters.py --scanlator-id 7

# Debug with visible browser
python scripts/track_chapters.py --visible --limit 1

# Add manga source
python scripts/add_manga_source.py

# Check database state
python scripts/test_tracking.py --skip-tracking
```

## Success Criteria

You'll know tracking is working when:
- ✓ No errors in the tracking output
- ✓ "New chapters found" count is > 0 (first run)
- ✓ Chapters appear in the database
- ✓ Duplicate detection works (second run finds 0 new)
- ✓ Summary report shows manga updates

Example successful output:

```
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
