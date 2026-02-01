from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class MangaStatus(str, enum.Enum):
    reading = "reading"
    completed = "completed"
    on_hold = "on_hold"
    plan_to_read = "plan_to_read"


class Manga(Base):
    __tablename__ = "mangas"

    id = Column(Integer, primary_key=True, index=True)
    mangataro_id = Column(String(50))
    title = Column(String(255), nullable=False, index=True)
    alternative_titles = Column(Text)
    cover_filename = Column(String(255))
    mangataro_url = Column(String(500))
    date_added = Column(DateTime)
    last_checked = Column(DateTime)
    status = Column(Enum(MangaStatus), default=MangaStatus.reading, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    manga_scanlators = relationship("MangaScanlator", back_populates="manga", cascade="all, delete-orphan")


class Scanlator(Base):
    __tablename__ = "scanlators"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    class_name = Column(String(100), nullable=False)
    base_url = Column(String(255))
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    manga_scanlators = relationship("MangaScanlator", back_populates="scanlator", cascade="all, delete-orphan")


class MangaScanlator(Base):
    __tablename__ = "manga_scanlator"

    id = Column(Integer, primary_key=True, index=True)
    manga_id = Column(Integer, ForeignKey("mangas.id", ondelete="CASCADE"), nullable=False, index=True)
    scanlator_id = Column(Integer, ForeignKey("scanlators.id", ondelete="CASCADE"), nullable=False, index=True)
    scanlator_manga_url = Column(String(500), nullable=False)
    manually_verified = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    manga = relationship("Manga", back_populates="manga_scanlators")
    scanlator = relationship("Scanlator", back_populates="manga_scanlators")
    chapters = relationship("Chapter", back_populates="manga_scanlator", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    manga_scanlator_id = Column(Integer, ForeignKey("manga_scanlator.id", ondelete="CASCADE"), nullable=False)
    chapter_number = Column(String(20), nullable=False)
    chapter_title = Column(String(255))
    chapter_url = Column(String(500), nullable=False)
    published_date = Column(DateTime)
    detected_date = Column(DateTime, nullable=False, index=True)
    read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    manga_scanlator = relationship("MangaScanlator", back_populates="chapters")


class ScrapingError(Base):
    __tablename__ = "scraping_errors"

    id = Column(Integer, primary_key=True, index=True)
    manga_scanlator_id = Column(Integer, ForeignKey("manga_scanlator.id", ondelete="CASCADE"))
    error_type = Column(String(50))
    error_message = Column(Text)
    timestamp = Column(DateTime, nullable=False, index=True)
    resolved = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
