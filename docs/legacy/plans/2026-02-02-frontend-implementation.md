# Astro Frontend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a clean, functional web UI with Astro + TailwindCSS for browsing manga, viewing updates, and managing read/unread status.

**Architecture:** Three-page Astro application (homepage updates feed, library grid, manga detail pages) with client-side interactivity via Alpine.js. Static-first with dynamic islands for mark-as-read functionality.

**Tech Stack:** Astro 4.x, TailwindCSS 3.x, Alpine.js (built-in), TypeScript

---

## Task 10: Astro Setup and Base Layout

**Goal:** Initialize Astro project with TailwindCSS and create base layout with navigation.

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/astro.config.mjs`
- Create: `frontend/tailwind.config.mjs`
- Create: `frontend/tsconfig.json`
- Create: `frontend/src/layouts/Layout.astro`
- Create: `frontend/src/components/Navigation.astro`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/public/.gitkeep`

### Step 1: Initialize Astro project

```bash
cd /data/mangataro
npm create astro@latest frontend -- --template minimal --install --git --typescript strict --no-dry-run
```

Expected: Creates `frontend/` directory with Astro boilerplate

### Step 2: Install TailwindCSS

```bash
cd frontend
npm install -D tailwindcss@latest @astrojs/tailwind@latest @astrojs/alpinejs@latest
npx tailwindcss init
```

Expected: Installs packages and creates `tailwind.config.mjs`

### Step 3: Configure Astro integrations

Edit `frontend/astro.config.mjs`:

```javascript
import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import alpinejs from '@astrojs/alpinejs';

export default defineConfig({
  integrations: [tailwind(), alpinejs()],
  server: {
    port: 4321,
  },
});
```

### Step 4: Configure Tailwind

Edit `frontend/tailwind.config.mjs`:

```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

### Step 5: Create API utility

Create `frontend/src/lib/api.ts`:

```typescript
const API_BASE = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

export interface Manga {
  id: number;
  title: string;
  alternative_titles: string | null;
  cover_filename: string | null;
  mangataro_url: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Chapter {
  id: number;
  chapter_number: string;
  chapter_title: string | null;
  chapter_url: string;
  published_date: string | null;
  detected_date: string;
  read: boolean;
  manga_scanlator: {
    id: number;
    manga_id: number;
    scanlator: {
      id: number;
      name: string;
    };
  };
}

export interface MangaWithScanlators extends Manga {
  manga_scanlators: Array<{
    id: number;
    scanlator: {
      id: number;
      name: string;
    };
  }>;
}

export const api = {
  async getUnreadChapters(limit = 50): Promise<Chapter[]> {
    const response = await fetch(`${API_BASE}/api/tracking/chapters/unread?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch unread chapters');
    return response.json();
  },

  async getAllManga(): Promise<Manga[]> {
    const response = await fetch(`${API_BASE}/api/manga?limit=100`);
    if (!response.ok) throw new Error('Failed to fetch manga');
    return response.json();
  },

  async getManga(id: number): Promise<MangaWithScanlators> {
    const response = await fetch(`${API_BASE}/api/manga/${id}`);
    if (!response.ok) throw new Error('Failed to fetch manga');
    return response.json();
  },

  async getMangaChapters(id: number): Promise<Chapter[]> {
    const response = await fetch(`${API_BASE}/api/manga/${id}/chapters?limit=500`);
    if (!response.ok) throw new Error('Failed to fetch chapters');
    return response.json();
  },

  async markChapterRead(chapterId: number): Promise<void> {
    const response = await fetch(`${API_BASE}/api/tracking/chapters/${chapterId}/mark-read`, {
      method: 'PUT',
    });
    if (!response.ok) throw new Error('Failed to mark chapter as read');
  },

  async markChapterUnread(chapterId: number): Promise<void> {
    const response = await fetch(`${API_BASE}/api/tracking/chapters/${chapterId}/mark-unread`, {
      method: 'PUT',
    });
    if (!response.ok) throw new Error('Failed to mark chapter as unread');
  },
};
```

### Step 6: Create base layout

Create `frontend/src/layouts/Layout.astro`:

```astro
---
interface Props {
  title: string;
}

const { title } = Astro.props;
---

<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="description" content="Manga Tracker - Track your manga chapters" />
    <meta name="viewport" content="width=device-width" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <title>{title}</title>
  </head>
  <body class="bg-slate-950 text-slate-100 min-h-screen">
    <nav class="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-50">
      <div class="container mx-auto px-4">
        <div class="flex items-center justify-between h-16">
          <div class="flex items-center space-x-8">
            <a href="/" class="text-xl font-bold text-blue-400">MangaTaro</a>
            <div class="flex space-x-4">
              <a
                href="/"
                class="px-3 py-2 rounded-md text-sm font-medium hover:bg-slate-800 transition"
              >
                Updates
              </a>
              <a
                href="/library"
                class="px-3 py-2 rounded-md text-sm font-medium hover:bg-slate-800 transition"
              >
                Library
              </a>
            </div>
          </div>
        </div>
      </div>
    </nav>
    <main class="container mx-auto px-4 py-8">
      <slot />
    </main>
  </body>
</html>
```

### Step 7: Create environment file

Create `frontend/.env`:

```
PUBLIC_API_URL=http://localhost:8000
```

### Step 8: Test dev server

```bash
cd frontend
npm run dev
```

Expected: Server starts at http://localhost:4321 with default Astro page

### Step 9: Commit setup

```bash
git add frontend/
git commit -m "feat: initialize Astro frontend with TailwindCSS

- Set up Astro 4.x with TypeScript
- Configure TailwindCSS and Alpine.js
- Create base layout with navigation
- Add API client utilities
- Configure dev server on port 4321"
```

---

## Task 11: Homepage with Updates Feed

**Goal:** Create homepage that displays unread chapters feed with mark-as-read functionality.

**Files:**
- Create: `frontend/src/pages/index.astro`
- Create: `frontend/src/components/ChapterItem.astro`
- Create: `frontend/src/lib/utils.ts`

### Step 1: Create utility functions

Create `frontend/src/lib/utils.ts`:

```typescript
export function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  const intervals = {
    year: 31536000,
    month: 2592000,
    week: 604800,
    day: 86400,
    hour: 3600,
    minute: 60,
  };

  for (const [unit, secondsInUnit] of Object.entries(intervals)) {
    const interval = Math.floor(seconds / secondsInUnit);
    if (interval >= 1) {
      return `${interval} ${unit}${interval > 1 ? 's' : ''} ago`;
    }
  }

  return 'just now';
}

export function getCoverUrl(filename: string | null): string {
  if (!filename) return '/placeholder-cover.jpg';
  return `/data/img/${filename}`;
}
```

### Step 2: Create ChapterItem component

Create `frontend/src/components/ChapterItem.astro`:

```astro
---
import type { Chapter } from '../lib/api';
import { formatTimeAgo, getCoverUrl } from '../lib/utils';

interface Props {
  chapter: Chapter;
}

const { chapter } = Astro.props;
const manga = chapter.manga_scanlator;
const scanlator = manga.scanlator;
---

<div
  class="flex gap-4 p-4 bg-slate-900/50 rounded-lg hover:bg-slate-800/50 transition"
  x-data="{ read: false }"
  :class="read && 'opacity-50'"
>
  <!-- Manga Cover -->
  <div class="flex-shrink-0">
    <a href={`/manga/${manga.manga_id}`}>
      <img
        src={getCoverUrl(null)}
        alt="Cover"
        class="w-16 h-24 object-cover rounded"
        loading="lazy"
      />
    </a>
  </div>

  <!-- Chapter Info -->
  <div class="flex-1 min-w-0">
    <div class="flex items-start justify-between gap-4">
      <div class="flex-1 min-w-0">
        <a
          href={`/manga/${manga.manga_id}`}
          class="text-lg font-semibold text-slate-100 hover:text-blue-400 transition line-clamp-1"
        >
          {manga.manga_id}
        </a>
        <div class="flex items-center gap-2 mt-1 text-sm text-slate-400">
          <a
            href={chapter.chapter_url}
            target="_blank"
            rel="noopener noreferrer"
            class="text-blue-400 hover:text-blue-300 font-medium"
          >
            Chapter {chapter.chapter_number}
          </a>
          {chapter.chapter_title && (
            <span class="line-clamp-1">- {chapter.chapter_title}</span>
          )}
        </div>
        <div class="flex items-center gap-2 mt-1 text-xs text-slate-500">
          <span>{scanlator.name}</span>
          <span>•</span>
          <span>{formatTimeAgo(chapter.detected_date)}</span>
        </div>
      </div>

      <!-- Mark as Read Button -->
      <button
        @click="
          read = true;
          fetch(`http://localhost:8000/api/tracking/chapters/${chapter.id}/mark-read`, { method: 'PUT' })
            .catch(err => { console.error(err); read = false; });
        "
        :disabled="read"
        class="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:cursor-not-allowed rounded transition"
      >
        <span x-show="!read">Mark Read</span>
        <span x-show="read" class="text-slate-400">✓ Read</span>
      </button>
    </div>
  </div>
</div>
```

### Step 3: Create homepage

Create `frontend/src/pages/index.astro`:

```astro
---
import Layout from '../layouts/Layout.astro';
import ChapterItem from '../components/ChapterItem.astro';
import { api } from '../lib/api';

const chapters = await api.getUnreadChapters(50);
---

<Layout title="Updates - MangaTaro">
  <div class="max-w-4xl mx-auto">
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-slate-100">Recent Updates</h1>
      <p class="text-slate-400 mt-2">
        {chapters.length} unread chapter{chapters.length !== 1 ? 's' : ''} across your collection
      </p>
    </div>

    {chapters.length === 0 ? (
      <div class="text-center py-16">
        <p class="text-slate-400 text-lg">No unread chapters</p>
        <p class="text-slate-500 text-sm mt-2">All caught up!</p>
      </div>
    ) : (
      <div class="space-y-3">
        {chapters.map((chapter) => (
          <ChapterItem chapter={chapter} />
        ))}
      </div>
    )}
  </div>
</Layout>
```

### Step 4: Test homepage

```bash
cd frontend
npm run dev
```

Visit http://localhost:4321 and verify:
- Unread chapters display correctly
- "Mark as read" button works
- Links to chapters open in new tabs

### Step 5: Commit homepage

```bash
git add frontend/src/
git commit -m "feat: implement homepage with updates feed

- Create ChapterItem component with mark-as-read
- Add formatTimeAgo utility for timestamps
- Display unread chapters in chronological order
- Alpine.js integration for interactive buttons
- Responsive layout with hover states"
```

---

## Task 12: Library and Detail Pages

**Goal:** Create library page with manga grid and detail pages showing chapter lists.

**Files:**
- Create: `frontend/src/pages/library.astro`
- Create: `frontend/src/pages/manga/[id].astro`
- Create: `frontend/src/components/MangaCard.astro`
- Create: `frontend/src/components/ChapterList.astro`

### Step 1: Create MangaCard component

Create `frontend/src/components/MangaCard.astro`:

```astro
---
import type { Manga } from '../lib/api';
import { getCoverUrl } from '../lib/utils';

interface Props {
  manga: Manga;
  unreadCount?: number;
}

const { manga, unreadCount = 0 } = Astro.props;
---

<a
  href={`/manga/${manga.id}`}
  class="block group relative bg-slate-900/50 rounded-lg overflow-hidden hover:ring-2 hover:ring-blue-500 transition"
>
  <!-- Cover Image -->
  <div class="aspect-[2/3] overflow-hidden bg-slate-800">
    <img
      src={getCoverUrl(manga.cover_filename)}
      alt={manga.title}
      class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
      loading="lazy"
    />
  </div>

  <!-- Unread Badge -->
  {unreadCount > 0 && (
    <div class="absolute top-2 right-2 bg-red-600 text-white text-xs font-bold px-2 py-1 rounded-full">
      {unreadCount}
    </div>
  )}

  <!-- Title -->
  <div class="p-3">
    <h3 class="font-medium text-slate-100 line-clamp-2 text-sm">
      {manga.title}
    </h3>
    <p class="text-xs text-slate-500 mt-1 capitalize">
      {manga.status.replace('_', ' ')}
    </p>
  </div>
</a>
```

### Step 2: Create library page

Create `frontend/src/pages/library.astro`:

```astro
---
import Layout from '../layouts/Layout.astro';
import MangaCard from '../components/MangaCard.astro';
import { api } from '../lib/api';

const allManga = await api.getAllManga();
---

<Layout title="Library - MangaTaro">
  <div>
    <!-- Header with Search -->
    <div class="mb-8">
      <h1 class="text-3xl font-bold text-slate-100">Library</h1>
      <p class="text-slate-400 mt-2">{allManga.length} manga in your collection</p>
    </div>

    <!-- Search Bar -->
    <div class="mb-6" x-data="{ search: '', status: 'all' }">
      <input
        type="text"
        x-model="search"
        placeholder="Search manga..."
        class="w-full max-w-md px-4 py-2 bg-slate-900 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-100"
      />

      <!-- Status Filter Tabs -->
      <div class="flex gap-2 mt-4">
        <button
          @click="status = 'all'"
          :class="status === 'all' ? 'bg-blue-600' : 'bg-slate-800 hover:bg-slate-700'"
          class="px-4 py-2 rounded-md text-sm font-medium transition"
        >
          All
        </button>
        <button
          @click="status = 'reading'"
          :class="status === 'reading' ? 'bg-blue-600' : 'bg-slate-800 hover:bg-slate-700'"
          class="px-4 py-2 rounded-md text-sm font-medium transition"
        >
          Reading
        </button>
        <button
          @click="status = 'completed'"
          :class="status === 'completed' ? 'bg-blue-600' : 'bg-slate-800 hover:bg-slate-700'"
          class="px-4 py-2 rounded-md text-sm font-medium transition"
        >
          Completed
        </button>
        <button
          @click="status = 'on_hold'"
          :class="status === 'on_hold' ? 'bg-blue-600' : 'bg-slate-800 hover:bg-slate-700'"
          class="px-4 py-2 rounded-md text-sm font-medium transition"
        >
          On Hold
        </button>
      </div>

      <!-- Manga Grid -->
      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mt-8">
        {allManga.map((manga) => (
          <div
            x-show="
              (status === 'all' || '{manga.status}' === status) &&
              (search === '' || '{manga.title}'.toLowerCase().includes(search.toLowerCase()))
            "
          >
            <MangaCard manga={manga} />
          </div>
        ))}
      </div>
    </div>
  </div>
</Layout>
```

### Step 3: Create ChapterList component

Create `frontend/src/components/ChapterList.astro`:

```astro
---
import type { Chapter } from '../lib/api';
import { formatTimeAgo } from '../lib/utils';

interface Props {
  chapters: Chapter[];
}

const { chapters } = Astro.props;
---

<div class="space-y-2" x-data="{ readChapters: new Set() }">
  {chapters.map((chapter) => (
    <div
      class="flex items-center justify-between p-3 bg-slate-900/50 rounded-lg hover:bg-slate-800/50 transition"
      :class=`readChapters.has(${chapter.id}) && 'opacity-50'`
    >
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-3">
          <a
            href={chapter.chapter_url}
            target="_blank"
            rel="noopener noreferrer"
            class="text-blue-400 hover:text-blue-300 font-medium"
          >
            Ch. {chapter.chapter_number}
          </a>
          {chapter.chapter_title && (
            <span class="text-slate-300 line-clamp-1">
              {chapter.chapter_title}
            </span>
          )}
        </div>
        <div class="flex items-center gap-2 mt-1 text-xs text-slate-500">
          <span>{chapter.manga_scanlator.scanlator.name}</span>
          <span>•</span>
          <span>{formatTimeAgo(chapter.detected_date)}</span>
        </div>
      </div>

      <label class="flex items-center cursor-pointer">
        <input
          type="checkbox"
          :checked=`readChapters.has(${chapter.id}) || ${chapter.read}`
          @change=`
            if ($event.target.checked) {
              readChapters.add(${chapter.id});
              fetch('http://localhost:8000/api/tracking/chapters/${chapter.id}/mark-read', { method: 'PUT' });
            } else {
              readChapters.delete(${chapter.id});
              fetch('http://localhost:8000/api/tracking/chapters/${chapter.id}/mark-unread', { method: 'PUT' });
            }
          `
          class="w-5 h-5 text-blue-600 bg-slate-800 border-slate-600 rounded focus:ring-2 focus:ring-blue-500"
        />
      </label>
    </div>
  ))}
</div>
```

### Step 4: Create manga detail page

Create `frontend/src/pages/manga/[id].astro`:

```astro
---
import Layout from '../../layouts/Layout.astro';
import ChapterList from '../../components/ChapterList.astro';
import { api } from '../../lib/api';
import { getCoverUrl } from '../../lib/utils';

const { id } = Astro.params;
if (!id) return Astro.redirect('/library');

const mangaId = parseInt(id);
const manga = await api.getManga(mangaId);
const chapters = await api.getMangaChapters(mangaId);

const unreadCount = chapters.filter(c => !c.read).length;
---

<Layout title={`${manga.title} - MangaTaro`}>
  <div class="max-w-6xl mx-auto">
    <!-- Back Button -->
    <a href="/library" class="inline-flex items-center text-slate-400 hover:text-slate-300 mb-6">
      ← Back to Library
    </a>

    <!-- Manga Info -->
    <div class="grid md:grid-cols-[300px,1fr] gap-8 mb-8">
      <!-- Cover -->
      <div>
        <img
          src={getCoverUrl(manga.cover_filename)}
          alt={manga.title}
          class="w-full rounded-lg shadow-xl"
        />
      </div>

      <!-- Details -->
      <div>
        <h1 class="text-4xl font-bold text-slate-100 mb-2">{manga.title}</h1>
        <p class="text-slate-400 capitalize mb-4">{manga.status.replace('_', ' ')}</p>

        {manga.alternative_titles && (
          <div class="mb-4">
            <h3 class="text-sm font-semibold text-slate-400 mb-1">Alternative Titles</h3>
            <p class="text-sm text-slate-300">{manga.alternative_titles}</p>
          </div>
        )}

        <!-- Tracked Scanlators -->
        {manga.manga_scanlators.length > 0 && (
          <div class="mb-4">
            <h3 class="text-sm font-semibold text-slate-400 mb-2">Tracking On</h3>
            <div class="flex flex-wrap gap-2">
              {manga.manga_scanlators.map((ms) => (
                <span class="px-3 py-1 bg-slate-800 rounded-full text-sm">
                  {ms.scanlator.name}
                </span>
              ))}
            </div>
          </div>
        )}

        <!-- Stats -->
        <div class="grid grid-cols-2 gap-4 mt-6">
          <div class="bg-slate-900/50 rounded-lg p-4">
            <div class="text-2xl font-bold text-blue-400">{chapters.length}</div>
            <div class="text-sm text-slate-400">Total Chapters</div>
          </div>
          <div class="bg-slate-900/50 rounded-lg p-4">
            <div class="text-2xl font-bold text-red-400">{unreadCount}</div>
            <div class="text-sm text-slate-400">Unread</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Chapters Section -->
    <div>
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-bold text-slate-100">Chapters</h2>
      </div>

      {chapters.length === 0 ? (
        <div class="text-center py-16 text-slate-400">
          <p>No chapters tracked yet</p>
        </div>
      ) : (
        <ChapterList chapters={chapters} />
      )}
    </div>
  </div>
</Layout>
```

### Step 5: Create placeholder cover image

```bash
# Download or create a simple placeholder image
curl -o frontend/public/placeholder-cover.jpg "https://via.placeholder.com/300x450/1e293b/94a3b8?text=No+Cover"
```

### Step 6: Test all pages

```bash
cd frontend
npm run dev
```

Test:
- Library page displays manga grid
- Search filters manga by title
- Status tabs filter correctly
- Clicking manga navigates to detail page
- Detail page shows chapters
- Mark as read checkboxes work
- Navigation between pages works

### Step 7: Commit library and detail pages

```bash
git add frontend/
git commit -m "feat: implement library and manga detail pages

- Library page with responsive grid layout
- Client-side search and status filtering
- Manga detail page with cover and info
- Chapter list with read/unread checkboxes
- Statistics display (total/unread)
- Placeholder cover for missing images"
```

---

## Final Testing & Polish

### Step 1: Build production version

```bash
cd frontend
npm run build
```

Expected: Clean build with no errors

### Step 2: Test production build

```bash
npm run preview
```

Visit http://localhost:4321 and test all functionality

### Step 3: Update TOMORROW.md

Edit `/data/mangataro/TOMORROW.md` to reflect completed tasks

### Step 4: Final commit

```bash
git add .
git commit -m "feat: complete Astro frontend implementation

Tasks 10-12 complete:
- Astro + TailwindCSS + Alpine.js setup
- Homepage with updates feed
- Library page with search/filter
- Manga detail pages with chapter lists
- Mark as read/unread functionality
- Responsive design for mobile/tablet/desktop

Frontend running on http://localhost:4321
API backend on http://localhost:8000"
```

---

## Success Criteria

**All requirements met:**
- [ ] Homepage displays unread chapters feed
- [ ] Mark as read functionality works
- [ ] Library shows all manga in responsive grid
- [ ] Search and status filtering work
- [ ] Detail pages show chapter lists
- [ ] Navigation works between all pages
- [ ] Mobile responsive on all screen sizes
- [ ] Clean, modern dark theme design
- [ ] Fast page loads (< 2s)

**Code Quality:**
- [ ] TypeScript types for all API responses
- [ ] Reusable components (ChapterItem, MangaCard, etc.)
- [ ] Proper error handling
- [ ] Loading states where needed
- [ ] Clean commits with descriptive messages

---

## Notes

- Frontend runs on port 4321 (Astro default)
- API must be running on port 8000
- Images served from `/data/img/` directory
- Alpine.js provides interactivity without heavy JavaScript
- Static generation possible for production deployment

**Estimated Time:** 3-4 hours for complete implementation
