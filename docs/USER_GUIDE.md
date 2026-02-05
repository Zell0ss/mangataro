# MangaTaro User Guide

Complete guide to using the MangaTaro manga tracking system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Web Interface](#web-interface)
3. [Managing Manga](#managing-manga)
4. [Tracking Chapters](#tracking-chapters)
5. [Notifications](#notifications)
6. [CLI Tools](#cli-tools)

---

## Quick Start

### Access the Web UI

1. Ensure the API is running: `uvicorn api.main:app --reload`
2. Ensure the frontend is running: `cd frontend && npm run dev`
3. Open your browser: http://localhost:4343

### Daily Workflow

1. Visit the **Homepage** to see unread chapter updates
2. Click "Mark as Read" on chapters you've read
3. Browse your **Library** to discover new manga
4. Click on any manga to see all available chapters

---

## Web Interface

### Homepage (Updates Feed)

**URL:** http://localhost:4343/

**Features:**
- Shows unread chapters across all tracked manga
- Sorted by detection date (newest first)
- Mark chapters as read with one click
- Links directly to scanlator websites

**Filters:**
- Search by manga title
- Filter by reading status (All, Unread, Read)

### Library Page

**URL:** http://localhost:4343/library

**Features:**
- Grid view of all manga in your collection
- Cover images with titles
- Reading status indicators
- Search and filters

**Actions:**
- Click on any manga card to view details
- Use search bar to find manga by title
- Filter by status or genre (if implemented)

### Manga Detail Page

**URL:** http://localhost:4343/manga/{id}

**Features:**
- Manga information (title, cover, description)
- List of all scanlators tracking this manga
- Complete chapter list with read/unread status
- Bulk actions (mark all as read)

**Actions:**
- Mark individual chapters as read/unread
- Click chapter links to read on scanlator site
- View scanlator information

---

## Managing Manga

### Adding Manga Sources

To track chapters for a manga, you need to map it to a scanlator URL.

**Using Web UI (Recommended):**

1. Navigate to **Admin → Map Sources** in the navigation menu
2. Select a scanlator from the dropdown (defaults to AsuraScans)
3. See the list of unmapped manga for that scanlator
4. For each manga:
   - Enter the manga's URL on the scanlator's website
   - URL is validated automatically (must match scanlator domain)
   - Click "Add" to create the mapping
   - Row fades out when successful
5. Switch scanlators using the dropdown to map manga from other sources
6. When all manga are mapped, you'll see a success message

**URL:** http://localhost:4343/admin/map-sources

**Features:**
- Real-time URL validation (format and domain checking)
- Inline error messages for invalid URLs
- Automatic row removal on successful mapping
- Counter showing remaining unmapped manga
- Empty state when all manga are mapped

**Using CLI Tool (Alternative):**

```bash
python scripts/add_manga_source.py
```

Follow the interactive prompts:
1. Select manga from your collection
2. Select scanlator (or add new)
3. Enter the manga URL on the scanlator site
4. Verify the mapping

**Using API (Programmatic):**

```bash
curl -X POST http://localhost:8008/api/tracking/manga-scanlators \
  -H "Content-Type: application/json" \
  -d '{
    "manga_id": 60,
    "scanlator_id": 3,
    "scanlator_manga_url": "https://asura-scans.com/manga/solo-leveling",
    "manually_verified": true
  }'
```

### Viewing Tracked Manga

**API Endpoint:**

```bash
curl http://localhost:8008/api/manga/{manga_id}
```

Shows manga details with all linked scanlators.

---

## Tracking Chapters

### Manual Tracking

Run tracking manually for all verified manga:

```bash
python scripts/track_chapters.py
```

**Options:**
- `--limit N`: Process only first N manga
- `--visible`: Run with visible browser (for debugging)
- `--manga-id ID`: Track specific manga only
- `--scanlator-id ID`: Track specific scanlator only

**Example:**

```bash
# Track all manga
python scripts/track_chapters.py

# Track specific manga with visible browser
python scripts/track_chapters.py --manga-id 60 --visible

# Track first 5 manga only
python scripts/track_chapters.py --limit 5
```

### Automated Tracking

**Option 1: Cron Job (Recommended)**

Setup automated tracking:

```bash
./scripts/setup_cron.sh
```

This runs tracking daily at 9 AM and 9 PM.

**Option 2: API Trigger**

Trigger tracking via API:

```bash
# Trigger tracking
curl -X POST http://localhost:8008/api/tracking/trigger \
  -H "Content-Type: application/json" \
  -d '{"notify": true}'

# Check job status
curl http://localhost:8008/api/tracking/jobs/{job_id}

# List recent jobs
curl http://localhost:8008/api/tracking/jobs
```

**Option 3: n8n Workflow**

See `n8n/README.md` for n8n workflow setup.

---

## Notifications

### Discord Notifications

Get notified when new chapters are detected.

**Setup:**

1. Create a Discord webhook:
   - Go to Server Settings > Integrations > Webhooks
   - Click "New Webhook"
   - Copy the webhook URL

2. Add to `.env`:
   ```bash
   NOTIFICATION_TYPE=discord
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE
   ```

3. Restart the API:
   ```bash
   uvicorn api.main:app --reload
   ```

4. Test notification:
   ```bash
   curl -X POST http://localhost:8008/api/tracking/test-notification
   ```

**What You'll Receive:**

- Notification when new chapters are detected
- Rich embed with manga title, chapter number, and link
- Up to 10 chapters per notification
- Summary if more than 10 chapters

---

## CLI Tools

### Extract from MangaTaro

**Purpose:** Import your manga collection from MangaTaro export.

```bash
python scripts/extract_mangataro.py
```

**Output:**
- Manga imported to database
- Cover images downloaded
- Markdown fichas created

### Add Manga Source

**Purpose:** Map manga to scanlator URLs for tracking.

```bash
python scripts/add_manga_source.py
```

**Interactive CLI** guides you through the process.

### Track Chapters

**Purpose:** Check scanlator sites for new chapters.

```bash
python scripts/track_chapters.py
```

See [Tracking Chapters](#tracking-chapters) for details.

### Test Scanlator Plugin

**Purpose:** Verify scanlator plugin works correctly.

```bash
python scripts/test_asura_scans.py
```

**Tests:**
- Search functionality
- Chapter extraction
- Manga page parsing

---

## Tips & Tricks

### Keyboard Shortcuts

- `/` - Focus search bar
- `Esc` - Clear search
- `Enter` - Submit search

### Performance

- Use `--limit` flag when testing tracking
- Run tracking during off-peak hours
- Use headless mode for faster tracking

### Troubleshooting

**Chapters not appearing:**
- Verify manga-scanlator mapping exists
- Check `manually_verified` is `true`
- Run tracking with `--visible` to debug

**Notifications not working:**
- Test with `/api/tracking/test-notification`
- Verify Discord webhook URL is correct
- Check API logs for errors

**Frontend not loading:**
- Ensure API is running on port 8008
- Check CORS settings in `.env`
- Verify frontend .env has correct API URL

---

## Next Steps

- Set up automated tracking (cron or n8n)
- Configure Discord notifications
- Add more manga-scanlator mappings
- Explore the API documentation

For API details, see `docs/api_guide.md`.

For setup instructions, see `docs/SETUP.md`.
