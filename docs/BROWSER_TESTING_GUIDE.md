# Browser Testing Guide: Manga-Scanlator Mapping UI

**Feature:** Manga-Scanlator Mapping Web Interface
**URL:** http://localhost:4343/admin/map-sources
**Date:** 2026-02-05

---

## Prerequisites

Before starting browser tests, ensure:

1. **API Server Running:**
   ```bash
   # Check API is running
   curl http://localhost:8008/health
   # Should return: {"status":"healthy","api":"operational"}
   ```

2. **Frontend Server Running:**
   ```bash
   # Check frontend is running
   curl http://localhost:4343
   # Should return: HTML page
   ```

3. **Database Access:**
   ```bash
   # Verify database connection
   mysql -u mangataro_user -p mangataro -e "SELECT COUNT(*) FROM mangas;"
   ```

4. **Browser DevTools Ready:**
   - Open Chrome/Firefox DevTools (F12)
   - Have Console and Network tabs visible
   - Disable browser cache for accurate testing

---

## Test Scenarios

### Test 1: Page Load and Default Scanlator

**Objective:** Verify page loads correctly with default scanlator.

**Steps:**
1. Navigate to: http://localhost:4343/admin/map-sources
2. Open DevTools Console
3. Check for JavaScript errors (should be none)

**Expected Results:**
- [ ] Page loads without errors
- [ ] Title shows "Map Manga Sources - MangaTaro"
- [ ] "Back to Library" link visible
- [ ] Scanlator dropdown shows "Asura Scans" selected
- [ ] Counter displays: "X manga need mapping"
- [ ] List of manga rows displayed
- [ ] Each row has: thumbnail, title, URL input, "Add" button

**Console Checks:**
- No errors in console
- Alpine.js loaded (check for Alpine global object)

**Screenshots:**
- [ ] Full page view
- [ ] Individual manga row closeup

---

### Test 2: Scanlator Dropdown

**Objective:** Verify scanlator switching works (if multiple scanlators available).

**Steps:**
1. Click on scanlator dropdown
2. Note available scanlators
3. If multiple available, select different one
4. Observe page reload

**Expected Results:**
- [ ] Dropdown opens and shows all active scanlators
- [ ] Selecting different scanlator reloads page
- [ ] URL updates with query param: `?scanlator=X`
- [ ] New list of unmapped manga loads
- [ ] Counter updates to reflect new count

**Current State:**
- Only 1 scanlator active (Asura Scans)
- Cannot fully test switching
- Dropdown UI should still work

**Screenshots:**
- [ ] Dropdown opened
- [ ] URL bar showing query parameter

---

### Test 3: URL Validation - Invalid Formats

**Objective:** Test client-side URL validation with invalid inputs.

#### Test 3.1: Empty URL
**Steps:**
1. Leave URL input blank
2. Click somewhere else (blur event)

**Expected:**
- [ ] No error shown (empty is neutral state)
- [ ] "Add" button remains disabled

#### Test 3.2: Invalid URL (No Protocol)
**Steps:**
1. Enter: `asuracomic.net/manga/test`
2. Click outside input (blur event)

**Expected:**
- [ ] Error message appears: "Invalid URL format"
- [ ] Error text is red
- [ ] "Add" button is disabled
- [ ] Input border may turn red

#### Test 3.3: Invalid URL (Wrong Protocol)
**Steps:**
1. Enter: `ftp://asuracomic.net/manga/test`
2. Blur input

**Expected:**
- [ ] Error message: "URL must start with http:// or https://"
- [ ] "Add" button disabled

#### Test 3.4: Wrong Domain
**Steps:**
1. Enter: `https://mangadex.org/title/12345`
2. Blur input

**Expected:**
- [ ] Error message: "URL must be from asuracomic.net"
- [ ] "Add" button disabled

#### Test 3.5: Valid URL
**Steps:**
1. Enter: `https://asuracomic.net/series/solo-leveling-001`
2. Blur input

**Expected:**
- [ ] No error message
- [ ] Error message (if any) disappears
- [ ] "Add" button is enabled (blue, not grayed)

**Screenshots:**
- [ ] Each validation error state
- [ ] Valid URL state with enabled button

---

### Test 4: Successful Mapping

**Objective:** Test complete mapping flow from input to row removal.

**Important:** Use a real manga URL from AsuraScans website for this test.

**Steps:**
1. Find a real manga on https://asuracomic.net
2. Copy its URL (e.g., `https://asuracomic.net/series/solo-leveling-001`)
3. Paste URL into first manga row's input field
4. Blur input (click outside)
5. Verify "Add" button is enabled
6. Open Network tab in DevTools
7. Click "Add" button
8. Watch for:
   - Button text changes to "Adding..."
   - Network request to `/api/tracking/manga-scanlators`
   - Row fades out (0.3s transition)
   - Row disappears from page

**Expected Results:**
- [ ] Button shows "Adding..." during submission
- [ ] Network tab shows POST request:
  - URL: `http://localhost:8008/api/tracking/manga-scanlators`
  - Status: 200 or 201
  - Method: POST
  - Body includes: manga_id, scanlator_id, url, manually_verified
- [ ] Response is successful (check in Network tab)
- [ ] Row smoothly fades out (opacity transition)
- [ ] Row is removed from DOM after 0.3 seconds
- [ ] Counter decrements by 1
- [ ] No JavaScript errors in console

**If Last Row:**
- [ ] Page reloads automatically
- [ ] Empty state appears (Test 6)

**Verification in Database:**
```bash
# Check mapping was created
mysql -u mangataro_user -p mangataro -e "
  SELECT ms.id, m.titulo, s.name, ms.scanlator_manga_url, ms.manually_verified
  FROM manga_scanlator ms
  JOIN mangas m ON ms.manga_id = m.id
  JOIN scanlators s ON ms.scanlator_id = s.id
  WHERE m.titulo = 'MANGA_TITLE_HERE';"
```

**Screenshots:**
- [ ] Before clicking "Add" (valid URL entered)
- [ ] Network tab showing POST request
- [ ] Network tab showing response (200/201)
- [ ] During fade out (if fast enough)
- [ ] After row removed (counter decremented)
- [ ] Database query result

---

### Test 5: Error Handling

**Objective:** Test error scenarios and error message display.

#### Test 5.1: Network Error (API Down)
**Steps:**
1. Stop API server: `Ctrl+C` on uvicorn terminal
2. Enter valid URL in a manga row
3. Click "Add"
4. Wait for response

**Expected:**
- [ ] Error message appears inline (red text)
- [ ] Error says something like: "Failed to save. Try again."
- [ ] Row does NOT disappear
- [ ] Button returns to "Add" state (not stuck on "Adding...")
- [ ] Entered URL is preserved (not cleared)
- [ ] User can retry after restarting API

**Restart API before continuing:**
```bash
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8008
```

#### Test 5.2: Duplicate Mapping
**Steps:**
1. Create a mapping successfully (Test 4)
2. Refresh page (F5)
3. Try to create same mapping again (same manga + scanlator)

**Expected:**
- [ ] Manga should NOT appear in unmapped list anymore
- [ ] If it somehow does, attempting to add should fail with error
- [ ] Error message: "Already mapped to this scanlator" or similar

**Alternative Test:**
```bash
# Manually create duplicate via API
curl -X POST http://localhost:8008/api/tracking/manga-scanlators \
  -H "Content-Type: application/json" \
  -d '{
    "manga_id": 25,
    "scanlator_id": 7,
    "scanlator_manga_url": "https://asuracomic.net/series/test",
    "manually_verified": true
  }'

# Try same request again - should fail
```

#### Test 5.3: Invalid Response from API
**Steps:**
1. Enter valid URL for unmapped manga
2. Click "Add"
3. Check console if 4xx or 5xx error occurs

**Expected:**
- [ ] Error message displays API error details
- [ ] Error is user-friendly (not raw JSON)
- [ ] Console may show error details (for debugging)

**Screenshots:**
- [ ] Each error scenario
- [ ] Error messages (inline, red text)
- [ ] Console errors (if any)

---

### Test 6: Empty State

**Objective:** Verify empty state appears when all manga are mapped.

**Setup Options:**

**Option A: Map all manga manually**
- Complete Test 4 for all visible manga
- Watch for automatic reload when last row removed

**Option B: Temporary database update**
```bash
# Mark all manga as mapped temporarily
mysql -u mangataro_user -p mangataro -e "
  INSERT INTO manga_scanlator (manga_id, scanlator_id, scanlator_manga_url, manually_verified)
  SELECT m.id, 7, CONCAT('https://asuracomic.net/test/', m.id), 1
  FROM mangas m
  WHERE m.id NOT IN (
    SELECT manga_id FROM manga_scanlator WHERE scanlator_id = 7
  );"
```

**Steps:**
1. Navigate to: http://localhost:4343/admin/map-sources
2. Observe empty state

**Expected Results:**
- [ ] Large celebratory emoji: 🎉
- [ ] Heading: "All Done!"
- [ ] Message: "All manga are mapped to Asura Scans"
- [ ] No manga rows visible
- [ ] No counter displayed
- [ ] Scanlator dropdown still visible
- [ ] Page looks centered and prominent

**Clean Up (if used Option B):**
```bash
# Remove test mappings
mysql -u mangataro_user -p mangataro -e "
  DELETE FROM manga_scanlator
  WHERE scanlator_manga_url LIKE '%/test/%';"
```

**Screenshots:**
- [ ] Full empty state view
- [ ] Close-up of message

---

### Test 7: Responsive Layout

**Objective:** Verify UI works on different screen sizes.

**Tools:**
- Chrome DevTools: Toggle device emulation (Ctrl+Shift+M)
- Test with: iPhone SE, iPad, Desktop

#### Test 7.1: Mobile (375px width - iPhone SE)
**Steps:**
1. Open DevTools
2. Toggle device toolbar
3. Select "iPhone SE"
4. Interact with page

**Check:**
- [ ] Page doesn't require horizontal scroll
- [ ] Scanlator dropdown fits width
- [ ] Manga row layout is usable
- [ ] Cover thumbnail visible and sized correctly
- [ ] URL input doesn't overflow
- [ ] "Add" button is tappable (min 44x44px)
- [ ] Text is readable (not too small)
- [ ] Error messages fit on screen

#### Test 7.2: Tablet (768px width - iPad)
**Steps:**
1. Select "iPad" in device toolbar
2. Test all interactions

**Check:**
- [ ] Layout uses available space well
- [ ] Multi-column (if applicable)
- [ ] Touch targets adequate

#### Test 7.3: Desktop (1280px+ width)
**Steps:**
1. Disable device emulation
2. Resize browser window wide

**Check:**
- [ ] Content is centered (max-w-4xl container)
- [ ] Not stretched too wide
- [ ] Margins on left/right

**Screenshots:**
- [ ] Mobile view
- [ ] Tablet view
- [ ] Desktop view

---

### Test 8: Multiple Mappings in Sequence

**Objective:** Test adding multiple mappings rapidly.

**Steps:**
1. Have 3-5 unmapped manga visible
2. Enter valid URLs for all of them (don't submit yet)
3. Validate all URLs (blur inputs)
4. Verify all "Add" buttons are enabled
5. Click "Add" on first manga
6. Immediately click "Add" on second manga
7. Continue for remaining manga

**Expected Results:**
- [ ] All submissions process correctly
- [ ] Rows fade out in order clicked
- [ ] No race conditions or conflicts
- [ ] Counter decrements correctly for each
- [ ] Network tab shows all POST requests succeeded
- [ ] No duplicate submissions

**Screenshots:**
- [ ] Multiple rows with valid URLs
- [ ] Network tab showing multiple successful requests

---

### Test 9: Browser Compatibility

**Objective:** Test in different browsers.

**Browsers to Test:**
- [ ] Chrome/Chromium (primary)
- [ ] Firefox
- [ ] Safari (if available)
- [ ] Edge (Chromium-based)

**For Each Browser:**
1. Load page: http://localhost:4343/admin/map-sources
2. Run Tests 1, 3, 4, 5
3. Check console for errors
4. Note any differences in behavior

**Common Issues:**
- [ ] Alpine.js compatibility
- [ ] Fetch API support
- [ ] CSS rendering differences
- [ ] Animation smoothness

---

## Test Data Preparation

### Get Real AsuraScans URLs

Visit https://asuracomic.net and find manga that match your database entries:

**Example URLs (verify these are current):**
- Solo Leveling: `https://asuracomic.net/series/solo-leveling-001`
- One Punch Man: `https://asuracomic.net/series/one-punch-man-001`
- Tower of God: `https://asuracomic.net/series/tower-of-god-001`

**Important:** AsuraScans URLs may change over time. Always verify URLs are current.

### Database Queries for Testing

**Check unmapped count:**
```sql
SELECT COUNT(*) FROM mangas m
WHERE m.id NOT IN (
  SELECT manga_id FROM manga_scanlator
  WHERE scanlator_id = 7 AND manually_verified = 1
);
```

**Check mapped count:**
```sql
SELECT COUNT(*) FROM manga_scanlator
WHERE scanlator_id = 7 AND manually_verified = 1;
```

**View all mappings:**
```sql
SELECT m.titulo, ms.scanlator_manga_url, ms.manually_verified
FROM manga_scanlator ms
JOIN mangas m ON ms.manga_id = m.id
WHERE ms.scanlator_id = 7
ORDER BY m.titulo;
```

---

## Success Criteria

All tests should pass with:
- ✅ No JavaScript errors in console
- ✅ All API requests return 2xx status codes
- ✅ UI feedback is clear and immediate
- ✅ Animations are smooth
- ✅ Error messages are user-friendly
- ✅ Responsive layout works on all devices
- ✅ Data persists correctly in database

---

## Troubleshooting

### Page Won't Load
```bash
# Check frontend server
ps aux | grep astro

# Check API server
curl http://localhost:8008/health

# Restart if needed
cd /data/mangataro/frontend && npm run dev
```

### JavaScript Errors
- Check browser console (F12)
- Verify Alpine.js loaded: `console.log(Alpine)`
- Check Network tab for failed requests

### API Errors
- Check API logs: `tail -f /tmp/api.log`
- Verify database connection
- Check .env file has correct credentials

### Database Issues
```bash
# Test connection
mysql -u mangataro_user -p mangataro -e "SELECT 1;"

# Check tables exist
mysql -u mangataro_user -p mangataro -e "SHOW TABLES;"
```

---

## Post-Test Cleanup

After completing all tests:

1. **Remove test mappings:**
   ```sql
   DELETE FROM manga_scanlator
   WHERE scanlator_manga_url LIKE '%test%';
   ```

2. **Verify database state:**
   ```sql
   SELECT COUNT(*) FROM manga_scanlator
   WHERE manually_verified = 1;
   ```

3. **Document results:**
   - Update test report
   - Save screenshots
   - Note any bugs found

4. **Report issues:**
   - Create bug reports for failures
   - Include screenshots and console logs
   - Provide reproduction steps

---

## Test Report Template

For each test scenario, document:

**Test Name:** [e.g., Test 4: Successful Mapping]
**Date/Time:** [timestamp]
**Browser:** [Chrome 120, Firefox 115, etc.]
**Status:** [PASS / FAIL / BLOCKED]
**Notes:** [observations, issues, etc.]
**Screenshots:** [links or file paths]

---

**Guide Created:** 2026-02-05
**Last Updated:** 2026-02-05
**Version:** 1.0
