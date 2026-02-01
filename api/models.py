"""
SQLAlchemy ORM Models for Manga Tracker
"""
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class MangaStatus(str, PyEnum):
    """Enum for manga publication status"""
    ONGOING = "ongoing"
    COMPLETED = "completed"
    HIATUS = "hiatus"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


class Manga(Base):
    """Manga model - stores manga metadata"""
    __tablename__ = "mangas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False, index=True)
    url = Column(Text, nullable=False)
    cover_image_url = Column(Text, nullable=True)
    status = Column(
        Enum(MangaStatus),
        default=MangaStatus.UNKNOWN,
        nullable=False,
        index=True
    )
    description = Column(Text, nullable=True)
    latest_chapter = Column(String(100), nullable=True)
    last_checked = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    scanlators = relationship(
        "Scanlator",
        secondary="manga_scanlator",
        back_populates="mangas"
    )
    chapters = relationship(
        "Chapter",
        back_populates="manga",
        cascade="all, delete-orphan"
    )
    scraping_errors = relationship(
        "ScrapingError",
        back_populates="manga",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Manga(id={self.id}, title='{self.title}', status='{self.status}')>"


class Scanlator(Base):
    """Scanlator model - stores scanlation group information"""
    __tablename__ = "scanlators"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    mangas = relationship(
        "Manga",
        secondary="manga_scanlator",
        back_populates="scanlators"
    )
    chapters = relationship(
        "Chapter",
        back_populates="scanlator",
        cascade="all, delete-orphan"
    )
    scraping_errors = relationship(
        "ScrapingError",
        back_populates="scanlator",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Scanlator(id={self.id}, name='{self.name}')>"


class MangaScanlator(Base):
    """Association table for many-to-many relationship between Manga and Scanlator"""
    __tablename__ = "manga_scanlator"

    id = Column(Integer, primary_key=True, autoincrement=True)
    manga_id = Column(Integer, ForeignKey("mangas.id", ondelete="CASCADE"), nullable=False)
    scanlator_id = Column(Integer, ForeignKey("scanlators.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("manga_id", "scanlator_id", name="unique_manga_scanlator"),
    )

    def __repr__(self):
        return f"<MangaScanlator(manga_id={self.manga_id}, scanlator_id={self.scanlator_id})>"


class Chapter(Base):
    """Chapter model - stores chapter information"""
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    manga_id = Column(Integer, ForeignKey("mangas.id", ondelete="CASCADE"), nullable=False, index=True)
    scanlator_id = Column(Integer, ForeignKey("scanlators.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_number = Column(String(100), nullable=False)
    title = Column(String(500), nullable=True)
    url = Column(Text, nullable=False)
    release_date = Column(DateTime, nullable=True, index=True)
    notified = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    manga = relationship("Manga", back_populates="chapters")
    scanlator = relationship("Scanlator", back_populates="chapters")

    __table_args__ = (
        UniqueConstraint("manga_id", "scanlator_id", "chapter_number", name="unique_chapter"),
    )

    def __repr__(self):
        return f"<Chapter(id={self.id}, manga_id={self.manga_id}, chapter_number='{self.chapter_number}')>"


class ScrapingError(Base):
    """ScrapingError model - logs scraping errors for debugging"""
    __tablename__ = "scraping_errors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    manga_id = Column(Integer, ForeignKey("mangas.id", ondelete="SET NULL"), nullable=True, index=True)
    scanlator_id = Column(Integer, ForeignKey("scanlators.id", ondelete="SET NULL"), nullable=True, index=True)
    error_type = Column(String(100), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    manga = relationship("Manga", back_populates="scraping_errors")
    scanlator = relationship("Scanlator", back_populates="scraping_errors")

    def __repr__(self):
        return f"<ScrapingError(id={self.id}, error_type='{self.error_type}', created_at='{self.created_at}')>"
