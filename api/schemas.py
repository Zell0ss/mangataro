from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional, List
from api.models import MangaStatus


# Base schemas
class MangaBase(BaseModel):
    title: str
    alternative_titles: Optional[str] = None
    mangataro_id: Optional[str] = None
    mangataro_url: Optional[str] = None
    cover_filename: Optional[str] = None
    status: MangaStatus = MangaStatus.reading


class MangaCreate(MangaBase):
    """Schema for creating a new manga"""
    pass


class MangaUpdate(BaseModel):
    """Schema for updating a manga"""
    title: Optional[str] = None
    alternative_titles: Optional[str] = None
    mangataro_id: Optional[str] = None
    mangataro_url: Optional[str] = None
    cover_filename: Optional[str] = None
    status: Optional[MangaStatus] = None


class MangaResponse(MangaBase):
    """Schema for manga response"""
    id: int
    date_added: Optional[datetime] = None
    last_checked: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Scanlator schemas
class ScanlatorBase(BaseModel):
    name: str
    class_name: str
    base_url: Optional[str] = None
    active: bool = True


class ScanlatorCreate(ScanlatorBase):
    """Schema for creating a new scanlator"""
    pass


class ScanlatorUpdate(BaseModel):
    """Schema for updating a scanlator"""
    name: Optional[str] = None
    class_name: Optional[str] = None
    base_url: Optional[str] = None
    active: Optional[bool] = None


class ScanlatorResponse(ScanlatorBase):
    """Schema for scanlator response"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Chapter schemas
class ChapterBase(BaseModel):
    chapter_number: str
    chapter_title: Optional[str] = None
    chapter_url: str
    published_date: Optional[datetime] = None
    read: bool = False


class ChapterCreate(ChapterBase):
    """Schema for creating a new chapter"""
    manga_scanlator_id: int
    detected_date: datetime = Field(default_factory=datetime.utcnow)


class ChapterUpdate(BaseModel):
    """Schema for updating a chapter"""
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    chapter_url: Optional[str] = None
    published_date: Optional[datetime] = None
    read: Optional[bool] = None


class ChapterResponse(ChapterBase):
    """Schema for chapter response"""
    id: int
    manga_scanlator_id: int
    detected_date: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# MangaScanlator schemas
class MangaScanlatorBase(BaseModel):
    manga_id: int
    scanlator_id: int
    scanlator_manga_url: str
    manually_verified: bool = False
    notes: Optional[str] = None


class MangaScanlatorCreate(MangaScanlatorBase):
    """Schema for creating a manga-scanlator relationship"""
    pass


class MangaScanlatorUpdate(BaseModel):
    """Schema for updating a manga-scanlator relationship"""
    scanlator_manga_url: Optional[str] = None
    manually_verified: Optional[bool] = None
    notes: Optional[str] = None


class MangaScanlatorResponse(MangaScanlatorBase):
    """Schema for manga-scanlator response"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# MangaScanlator with nested data
class MangaScanlatorWithDetails(MangaScanlatorResponse):
    """Schema for manga-scanlator with nested scanlator and manga details"""
    scanlator: ScanlatorResponse
    manga: MangaResponse

    class Config:
        from_attributes = True


# Chapter with nested data
class ChapterWithDetails(ChapterResponse):
    """Schema for chapter with nested manga-scanlator details"""
    manga_scanlator: MangaScanlatorWithDetails

    class Config:
        from_attributes = True


# Manga with nested relationships
class MangaWithScanlators(MangaResponse):
    """Schema for manga with all scanlators"""
    manga_scanlators: List[MangaScanlatorWithDetails] = []

    class Config:
        from_attributes = True


# ScrapingError schemas
class ScrapingErrorBase(BaseModel):
    manga_scanlator_id: int
    error_type: str
    error_message: str
    resolved: bool = False


class ScrapingErrorCreate(ScrapingErrorBase):
    """Schema for creating a scraping error"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ScrapingErrorUpdate(BaseModel):
    """Schema for updating a scraping error"""
    resolved: Optional[bool] = None


class ScrapingErrorResponse(ScrapingErrorBase):
    """Schema for scraping error response"""
    id: int
    timestamp: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# Pagination schema
class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    items: List
    total: int
    page: int
    page_size: int
    total_pages: int
