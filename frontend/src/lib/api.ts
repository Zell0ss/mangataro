const API_BASE = import.meta.env.PUBLIC_API_URL || 'http://localhost:8008';

export interface Manga {
  id: number;
  title: string;
  alternative_titles: string | null;
  cover_filename: string | null;
  mangataro_url: string | null;
  status: string;
  nsfw: boolean;
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
    manga: {
      id: number;
      title: string;
      cover_filename: string | null;
      nsfw: boolean;
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

export interface Scanlator {
  id: number;
  name: string;
  class_name: string;
  base_url: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UnmappedMangaResponse {
  scanlator_id: number;
  scanlator_name: string;
  base_url: string | null;
  unmapped_manga: Array<{
    id: number;
    title: string;
    cover_filename: string | null;
    status: string;
    nsfw: boolean;
  }>;
  count: number;
}

export interface CreateMangaScanlatorRequest {
  manga_id: number;
  scanlator_id: number;
  scanlator_manga_url: string;
  manually_verified: boolean;
  notes?: string;
}

export interface CreateMangaWithScanlatorRequest {
  title: string;
  alternative_titles?: string;
  scanlator_id: number;
  scanlator_manga_url: string;
  cover_url: string;
  cover_filename?: string;
  status?: string;
}

export const api = {
  async getUnreadChapters(limit = 50): Promise<Chapter[]> {
    const response = await fetch(`${API_BASE}/api/tracking/chapters/unread?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch unread chapters');
    return response.json();
  },

  async getLatestChapters(limit = 100): Promise<Chapter[]> {
    const response = await fetch(`${API_BASE}/api/tracking/chapters/latest?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch latest chapters');
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

  async getUnmappedManga(scanlatorId: number): Promise<UnmappedMangaResponse> {
    const response = await fetch(`${API_BASE}/api/manga/unmapped?scanlator_id=${scanlatorId}`);
    if (!response.ok) throw new Error('Failed to fetch unmapped manga');
    return response.json();
  },

  async getScanlators(): Promise<Scanlator[]> {
    const response = await fetch(`${API_BASE}/api/scanlators?active_only=true`);
    if (!response.ok) throw new Error('Failed to fetch scanlators');
    return response.json();
  },

  async createMangaScanlator(data: CreateMangaScanlatorRequest): Promise<void> {
    const response = await fetch(`${API_BASE}/api/tracking/manga-scanlators`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create manga-scanlator mapping');
    }
  },

  async createMangaWithScanlator(data: CreateMangaWithScanlatorRequest): Promise<Manga> {
    const response = await fetch(`${API_BASE}/api/manga/with-scanlator`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create manga');
    }
    return response.json();
  },
};
