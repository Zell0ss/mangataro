from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from api.dependencies import get_db
from api import schemas, models
from datetime import datetime

router = APIRouter()


@router.get("/chapters/unread", response_model=List[schemas.ChapterWithDetails])
async def get_unread_chapters(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get all unread chapters across all manga.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    """
    chapters = db.query(models.Chapter).options(
        joinedload(models.Chapter.manga_scanlator).joinedload(models.MangaScanlator.scanlator),
        joinedload(models.Chapter.manga_scanlator).joinedload(models.MangaScanlator.manga)
    ).filter(models.Chapter.read == False).order_by(
        models.Chapter.detected_date.desc()
    ).offset(skip).limit(limit).all()

    return chapters


@router.put("/chapters/{chapter_id}/mark-read", response_model=schemas.ChapterResponse)
async def mark_chapter_read(chapter_id: int, db: Session = Depends(get_db)):
    """
    Mark a chapter as read.

    - **chapter_id**: The ID of the chapter to mark as read
    """
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()

    if not chapter:
        raise HTTPException(status_code=404, detail=f"Chapter with ID {chapter_id} not found")

    chapter.read = True
    chapter.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(chapter)

    return chapter


@router.put("/chapters/{chapter_id}/mark-unread", response_model=schemas.ChapterResponse)
async def mark_chapter_unread(chapter_id: int, db: Session = Depends(get_db)):
    """
    Mark a chapter as unread.

    - **chapter_id**: The ID of the chapter to mark as unread
    """
    chapter = db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()

    if not chapter:
        raise HTTPException(status_code=404, detail=f"Chapter with ID {chapter_id} not found")

    chapter.read = False
    chapter.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(chapter)

    return chapter


@router.post("/manga-scanlators", response_model=schemas.MangaScanlatorResponse, status_code=201)
async def add_manga_scanlator(
    scanlator_data: schemas.MangaScanlatorCreate,
    db: Session = Depends(get_db)
):
    """
    Add a scanlator to track for a manga (create manga-scanlator relationship).

    - **scanlator_data**: Manga-scanlator relationship data
    """
    # Verify manga exists
    manga = db.query(models.Manga).filter(
        models.Manga.id == scanlator_data.manga_id
    ).first()
    if not manga:
        raise HTTPException(
            status_code=404,
            detail=f"Manga with ID {scanlator_data.manga_id} not found"
        )

    # Verify scanlator exists
    scanlator = db.query(models.Scanlator).filter(
        models.Scanlator.id == scanlator_data.scanlator_id
    ).first()
    if not scanlator:
        raise HTTPException(
            status_code=404,
            detail=f"Scanlator with ID {scanlator_data.scanlator_id} not found"
        )

    # Check if relationship already exists
    existing = db.query(models.MangaScanlator).filter(
        models.MangaScanlator.manga_id == scanlator_data.manga_id,
        models.MangaScanlator.scanlator_id == scanlator_data.scanlator_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Manga {scanlator_data.manga_id} is already being tracked on scanlator {scanlator_data.scanlator_id}"
        )

    db_manga_scanlator = models.MangaScanlator(
        manga_id=scanlator_data.manga_id,
        scanlator_id=scanlator_data.scanlator_id,
        scanlator_manga_url=scanlator_data.scanlator_manga_url,
        manually_verified=scanlator_data.manually_verified,
        notes=scanlator_data.notes
    )

    db.add(db_manga_scanlator)
    db.commit()
    db.refresh(db_manga_scanlator)

    return db_manga_scanlator


@router.get("/manga-scanlators/{manga_scanlator_id}", response_model=schemas.MangaScanlatorWithDetails)
async def get_manga_scanlator(manga_scanlator_id: int, db: Session = Depends(get_db)):
    """
    Get a specific manga-scanlator relationship by ID.

    - **manga_scanlator_id**: The ID of the manga-scanlator relationship
    """
    manga_scanlator = db.query(models.MangaScanlator).options(
        joinedload(models.MangaScanlator.scanlator)
    ).filter(models.MangaScanlator.id == manga_scanlator_id).first()

    if not manga_scanlator:
        raise HTTPException(
            status_code=404,
            detail=f"Manga-scanlator relationship with ID {manga_scanlator_id} not found"
        )

    return manga_scanlator


@router.put("/manga-scanlators/{manga_scanlator_id}", response_model=schemas.MangaScanlatorResponse)
async def update_manga_scanlator(
    manga_scanlator_id: int,
    update_data: schemas.MangaScanlatorUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a manga-scanlator relationship.

    - **manga_scanlator_id**: The ID of the relationship to update
    - **update_data**: Fields to update
    """
    manga_scanlator = db.query(models.MangaScanlator).filter(
        models.MangaScanlator.id == manga_scanlator_id
    ).first()

    if not manga_scanlator:
        raise HTTPException(
            status_code=404,
            detail=f"Manga-scanlator relationship with ID {manga_scanlator_id} not found"
        )

    # Update only provided fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(manga_scanlator, field, value)

    manga_scanlator.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(manga_scanlator)

    return manga_scanlator


@router.delete("/manga-scanlators/{manga_scanlator_id}", status_code=204)
async def delete_manga_scanlator(manga_scanlator_id: int, db: Session = Depends(get_db)):
    """
    Delete a manga-scanlator relationship (stops tracking).

    - **manga_scanlator_id**: The ID of the relationship to delete
    """
    manga_scanlator = db.query(models.MangaScanlator).filter(
        models.MangaScanlator.id == manga_scanlator_id
    ).first()

    if not manga_scanlator:
        raise HTTPException(
            status_code=404,
            detail=f"Manga-scanlator relationship with ID {manga_scanlator_id} not found"
        )

    db.delete(manga_scanlator)
    db.commit()

    return None
