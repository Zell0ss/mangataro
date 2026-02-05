# Manga Tracker Frontend Design

**Date:** 2026-02-02
**Status:** Approved - Ready for Implementation
**Estimated Effort:** 3-4 hours

---

## Overview

Design for a clean, functional web UI to browse manga collection, track new chapter updates, and manage read/unread status. Built with Astro + TailwindCSS for speed and simplicity.

---

## Architecture & Technology Stack

### Framework: Astro with TailwindCSS

**Why Astro:**
- Content-driven pages (perfect for displaying manga lists)
- Minimal JavaScript by default (fast page loads)
- Built-in support for Alpine.js (lightweight interactivity)
- Static-first with dynamic islands where needed

**Tech Stack:**
- **Astro** - Page framework and routing
- **TailwindCSS** - Utility-first styling
- **Alpine.js** - Client-side interactivity (mark as read, search)
- **Fetch API** - Backend communication (FastAPI at localhost:8008)

**Key Principle:** Keep it simple. The API handles all logic - the frontend just displays data and sends simple commands.

---

## User Requirements

Based on user responses:

1. **Primary Use Case:** Both quick browsing AND library management
   - See new chapter updates at a glance
   - Browse and organize manga collection
   - Mark chapters as read/unread

2. **Layout Preference:** Updates-first homepage with separate library page
   - Homepage: Feed of new chapters (what's new)
   - Library page: Browse all manga collection

3. **Chapter Interaction:** Open in new tab with manual "mark as read"
   - Chapter links open scanlator sites in new tabs
   - Separate button/checkbox to mark as read
   - Full control over read status

---

## Page Structure

### 1. Homepage (/) - Updates Feed

**Purpose:** See what's new across all tracked manga

**Data Source:** `GET /api/tracking/chapters/unread?limit=50`

**Layout:**
- Chronological feed of unread chapters
- Each entry shows:
  - Manga cover (small thumbnail)
  - Manga title
  - Chapter number & title
  - Scanlator name
  - "X days ago" timestamp
- Click chapter number → opens scanlator site in new tab
- "Mark as read" button next to each chapter
- "Load More" button for pagination

**Key Features:**
- Fast scanning for updates
- One-click to read or mark
- Clean, feed-style layout

---

### 2. Library Page (/library) - Collection Browse

**Purpose:** Browse and manage full manga collection

**Data Source:** `GET /api/manga?limit=100`

**Layout:**
- Responsive grid of manga covers
  - 6 columns (desktop)
  - 3 columns (tablet)
  - 2 columns (mobile)
- Each card shows:
  - Cover image
  - Manga title
  - Unread chapter count badge (if > 0)
- Click card → navigate to manga detail page

**Key Features:**
- Search bar at top (client-side filtering)
- Status filter tabs: All | Reading | Completed | On Hold
- Visual browsing with covers
- Clear unread indicators

---

### 3. Manga Detail Page (/manga/[id])

**Purpose:** View all chapters for a specific manga

**Data Sources:**
- `GET /api/manga/{id}` - Manga info + scanlators
- `GET /api/manga/{id}/chapters` - Chapter list

**Layout:**
- **Top Section:**
  - Large cover image
  - Manga title
  - Status indicator
  - Tracked scanlators list

- **Chapter List:**
  - Grouped by scanlator (if multiple sources)
  - Each chapter shows:
    - Chapter number
    - Chapter title
    - Release date
    - Read/unread status (visual indicator)
    - Link to read (opens in new tab)
    - "Mark as read" checkbox

- **Bulk Actions:**
  - "Mark all as read" button

**Key Features:**
- Complete chapter history
- Easy marking of multiple chapters
- Clear read/unread status

---

## Data Flow & Interactivity

### Client-Side State Management

**Minimal JavaScript Approach:**
- Most pages are static Astro (fast load)
- Alpine.js for dynamic interactions
- No complex state management needed

### Mark as Read Flow

```
User clicks "Mark as read"
  ↓
Alpine.js → PUT /api/tracking/chapters/{id}/mark-read
  ↓
Success: Update UI (fade out or style change)
Error: Show toast notification
```

### Library Search & Filter

**Client-side filtering (94 manga is small enough):**
- Fetch all manga on page load
- Search input filters by title (no API calls)
- Status tabs filter by status (no API calls)
- Fast and responsive

### Navigation

**Top nav bar (always visible):**
- "Updates" link → Homepage
- "Library" link → Library page
- Simple, clean navigation

### Image Loading

**Cover Images:**
- Served from `/data/img/{filename}`
- Native browser lazy loading (`loading="lazy"`)
- Placeholder/fallback for missing images

**Key Insight:** With only 94 manga, load everything client-side for instant filtering/search. No need for complex server-side pagination.

---

## Styling & Visual Design

### TailwindCSS Design System

**Color Scheme:**
- Dark mode friendly (slate/zinc grays)
- Accent color for unread badges (blue or red)
- Subtle status indicators

**Typography:**
- System fonts for speed (`font-sans`)
- Clear hierarchy (headings, body, small text)

**Spacing:**
- Generous whitespace
- Easy to scan layouts
- Mobile-first responsive

**Component Styles:**

**Unread Badges:**
- Bright accent color
- Pill shape with count
- Visible at a glance

**Status Indicators:**
- Read: Muted gray
- Unread: Bold/prominent
- Visual differentiation

**Buttons:**
- Primary actions: Filled
- Secondary: Outline
- Clear hover states

---

## Implementation Plan

### Task 10: Astro Setup (30 minutes)

```bash
# Create Astro project
npm create astro@latest frontend

# Install dependencies
cd frontend
npm install -D tailwindcss@latest
npx tailwindcss init

# Configure API base URL
# Set up basic layout component
```

**Deliverables:**
- Working Astro dev server
- TailwindCSS configured
- Base layout with navigation
- API client utility

---

### Task 11: Homepage with Updates Feed (1-2 hours)

**Files to create:**
- `src/pages/index.astro` - Homepage
- `src/components/UpdatesFeed.astro` - Feed component
- `src/components/ChapterItem.astro` - Single chapter entry
- `src/utils/api.ts` - API client functions

**Features:**
- Fetch unread chapters from `/api/tracking/chapters/unread`
- Display feed with manga covers and chapter info
- "Mark as read" button with Alpine.js
- "Load More" pagination
- Responsive layout

---

### Task 12: Library & Detail Pages (1-2 hours)

**Files to create:**
- `src/pages/library.astro` - Library grid
- `src/pages/manga/[id].astro` - Detail page
- `src/components/MangaCard.astro` - Grid card
- `src/components/ChapterList.astro` - Chapter list
- `src/components/SearchBar.astro` - Search input

**Features:**
- Library: Grid layout with search and filters
- Detail: Chapter list with bulk actions
- Client-side search/filter
- Mark as read functionality
- Responsive design

---

## API Endpoints Used

### Homepage (Updates Feed)
- `GET /api/tracking/chapters/unread?skip=0&limit=50`

### Library Page
- `GET /api/manga?limit=100`

### Detail Page
- `GET /api/manga/{id}`
- `GET /api/manga/{id}/chapters`

### Mark as Read
- `PUT /api/tracking/chapters/{id}/mark-read`
- `PUT /api/tracking/chapters/{id}/mark-unread`

---

## Success Criteria

**Functional:**
- [ ] Can view all unread chapters on homepage
- [ ] Can mark chapters as read
- [ ] Can browse all manga in library
- [ ] Can search and filter manga
- [ ] Can view chapter history for any manga
- [ ] All pages are responsive (mobile, tablet, desktop)

**Technical:**
- [ ] Fast page loads (< 2s)
- [ ] Works with 94 manga without performance issues
- [ ] Clean, maintainable code
- [ ] Proper error handling

**User Experience:**
- [ ] Clear visual hierarchy
- [ ] Easy to spot new updates
- [ ] Simple navigation
- [ ] Obvious interactive elements

---

## Future Enhancements

(Not in scope for initial implementation)

- Dark/light mode toggle
- Bulk mark as read from homepage
- Filter updates by manga
- Sorting options (by date, title, etc.)
- Notifications for new chapters
- Keyboard shortcuts

---

## Notes

- Keep it simple: The 94 manga collection is small enough to avoid complex pagination
- Static-first: Use Astro's strengths for fast page loads
- Progressive enhancement: Core functionality works without JavaScript, Alpine.js enhances it
- Mobile-friendly: Many users will check updates on mobile devices

---

**Design Status:** ✅ APPROVED
**Next Step:** Implementation (Tasks 10-12)
