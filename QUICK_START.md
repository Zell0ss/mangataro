# Quick Start Guide

## Task 2: MangaTaro Extractor - COMPLETE ✅

### What Was Implemented

A complete extraction pipeline that:
1. Reads your MangaTaro export (94 manga bookmarks)
2. Downloads cover images
3. Scrapes manga pages for additional info (alternative titles, scanlation groups)
4. Inserts everything into the database
5. Generates markdown info cards (fichas) for each manga
6. Creates a scanlators checklist

### Files Created

```
/data/mangataro/
├── api/
│   └── utils.py                      # Helper functions
├── scripts/
│   ├── extract_mangataro.py          # Main extractor script
│   └── run_full_extraction.sh        # Helper script
├── EXTRACTION_GUIDE.md               # Detailed guide
└── TASK2_COMPLETE.md                 # Implementation summary
```

### Test Results

Successfully tested on first manga ("Girls x Vampire"):
- ✅ Cover image downloaded
- ✅ Alternative titles scraped: "ガールズ×ヴァンパイア / Girls x Vampire / Дівчата × Вампір / بنات × مصاصي الدماء / Kızlar × Vampir"
- ✅ Scanlator found and cleaned: "Uscanlations"
- ✅ Database entry created
- ✅ Markdown ficha generated

### Running the Full Extraction

**Option 1: Direct command**
```bash
cd /data/mangataro
source .venv/bin/activate
python scripts/extract_mangataro.py
```

**Option 2: Helper script**
```bash
cd /data/mangataro
./scripts/run_full_extraction.sh
```

**Test mode (first manga only):**
```bash
source .venv/bin/activate
python scripts/extract_mangataro.py --test
```

### Monitoring Progress

In another terminal:
```bash
tail -f /data/mangataro/logs/extract_mangataro_*.log
```

### Expected Results

After completion:
- **94 cover images** in `data/img/`
- **94 markdown fichas** in `docs/fichas/`
- **Scanlators checklist** at `docs/scanlators.md`
- **Database entries:**
  - 94 entries in `mangas` table
  - Multiple entries in `scanlators` table (unique groups)
  - 94 entries in `manga_scanlator` junction table

### Estimated Time

- **15-20 minutes** for all 94 manga
  - Image downloads: ~3 min
  - Web scraping: ~8 min
  - Delays between requests: ~6 min

### Verification

Check the results:
```bash
# Count manga
mysql -u mangataro_user -pyour_password_here mangataro \
  -e "SELECT COUNT(*) FROM mangas;"

# Count scanlators
mysql -u mangataro_user -pyour_password_here mangataro \
  -e "SELECT COUNT(*) FROM scanlators;"

# View manga with scanlators
mysql -u mangataro_user -pyour_password_here mangataro \
  -e "SELECT m.title, s.name FROM mangas m
      JOIN manga_scanlator ms ON m.id = ms.manga_id
      JOIN scanlators s ON ms.scanlator_id = s.id
      LIMIT 10;"
```

### Key Features

- ✅ Sync Playwright API (not async)
- ✅ Multiple CSS selector strategies for robustness
- ✅ Automatic scanlator name cleaning
- ✅ Polite delays (2-5 seconds) between requests
- ✅ Comprehensive error handling
- ✅ Detailed logging
- ✅ Handles relative URLs
- ✅ Skips already-downloaded images
- ✅ Graceful failure handling

### What's Next?

After running the extraction:

1. **Review scanlators**: Check `docs/scanlators.md`
2. **Identify active scanlators**: Which ones to track
3. **Task 3**: Create scraper classes for each scanlator
4. **Task 4**: Implement background monitoring system

### Documentation

- **EXTRACTION_GUIDE.md** - Detailed extraction guide
- **TASK2_COMPLETE.md** - Full implementation summary
- **QUICK_START.md** - This file

### Troubleshooting

**Database errors:**
- Verify MariaDB is running: `systemctl status mariadb`
- Check credentials in `.env`

**Playwright errors:**
- Install browser: `playwright install chromium`
- Check internet connection

**Need to re-run:**
```bash
# Clear data
mysql -u mangataro_user -pyour_password_here mangataro << EOF
DELETE FROM chapters;
DELETE FROM manga_scanlator;
DELETE FROM mangas;
DELETE FROM scanlators;
EOF

rm -f data/img/*
rm -f docs/fichas/*.md

# Run again
source .venv/bin/activate
python scripts/extract_mangataro.py
```

---

**Ready to extract!** Just run the command and let it work. ⏱️ 15-20 minutes
