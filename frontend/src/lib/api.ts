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
    manga: {
      id: number;
      title: string;
      cover_filename: string | null;
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

export interface UnmappedMangaResponse {
  scanlator_id: number;
  scanlator_name: string;
  base_url: string | null;
  unmapped_manga: Array<{
    id: number;
    title: string;
    cover_filename: string | null;
    status: string;
  }>;
  count: number;
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

  async getUnmappedManga(scanlatorId: number): Promise<UnmappedMangaResponse> {
    const response = await fetch(`${API_BASE}/api/manga/unmapped?scanlator_id=${scanlatorId}`);
    if (!response.ok) throw new Error('Failed to fetch unmapped manga');
    return response.json();
  },
};
