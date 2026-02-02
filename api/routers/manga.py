from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import cast, Float
from typing import List, Optional
from api.dependencies import get_db
from api import schemas, models
from datetime import datetime

router = APIRouter()


@router.get("/", response_model=List[schemas.MangaResponse])
async def list_manga(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[models.MangaStatus] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all manga with optional filtering.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by manga status (reading, completed, on_hold, plan_to_read)
    - **search**: Search in title and alternative titles
    """
    query = db.query(models.Manga)

    # Filter by status
    if status:
        query = query.filter(models.Manga.status == status)

    # Search in title and alternative titles
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (models.Manga.title.like(search_pattern)) |
            (models.Manga.alternative_titles.like(search_pattern))
        )

    # Order by last checked (most recently checked first, nulls last)
    # MariaDB doesn't support NULLS LAST, so we order by (last_checked IS NULL), last_checked DESC
    query = query.order_by(
        models.Manga.last_checked.is_(None),
        models.Manga.last_checked.desc()
    )

    # Apply pagination
    manga = query.offset(skip).limit(limit).all()

    return manga


@router.get("/{manga_id}", response_model=schemas.MangaWithScanlators)
async def get_manga(manga_id: int, db: Session = Depends(get_db)):
    """
    Get a specific manga by ID with all its scanlators.

    - **manga_id**: The ID of the manga to retrieve
    """
    manga = db.query(models.Manga).options(
        joinedload(models.Manga.manga_scanlators).joinedload(models.MangaScanlator.scanlator)
    ).filter(models.Manga.id == manga_id).first()

    if not manga:
        raise HTTPException(status_code=404, detail=f"Manga with ID {manga_id} not found")

    return manga


@router.post("/", response_model=schemas.MangaResponse, status_code=201)
async def create_manga(manga: schemas.MangaCreate, db: Session = Depends(get_db)):
    """
    Create a new manga entry.

    - **manga**: Manga data to create
    """
    # Check if manga with same title already exists
    existing = db.query(models.Manga).filter(models.Manga.title == manga.title).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Manga with title '{manga.title}' already exists")

    db_manga = models.Manga(
        title=manga.title,
        alternative_titles=manga.alternative_titles,
        mangataro_id=manga.mangataro_id,
        mangataro_url=manga.mangataro_url,
        cover_filename=manga.cover_filename,
        status=manga.status,
        date_added=datetime.utcnow()
    )

    db.add(db_manga)
    db.commit()
    db.refresh(db_manga)

    return db_manga


@router.put("/{manga_id}", response_model=schemas.MangaResponse)
async def update_manga(
    manga_id: int,
    manga_update: schemas.MangaUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a manga's information.

    - **manga_id**: The ID of the manga to update
    - **manga_update**: Fields to update
    """
    manga = db.query(models.Manga).filter(models.Manga.id == manga_id).first()

    if not manga:
        raise HTTPException(status_code=404, detail=f"Manga with ID {manga_id} not found")

    # Update only provided fields
    update_data = manga_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(manga, field, value)

    manga.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(manga)

    return manga


@router.delete("/{manga_id}", status_code=204)
async def delete_manga(manga_id: int, db: Session = Depends(get_db)):
    """
    Delete a manga (and all related data due to cascade).

    - **manga_id**: The ID of the manga to delete
    """
    manga = db.query(models.Manga).filter(models.Manga.id == manga_id).first()

    if not manga:
        raise HTTPException(status_code=404, detail=f"Manga with ID {manga_id} not found")

    db.delete(manga)
    db.commit()

    return None


@router.get("/{manga_id}/chapters", response_model=List[schemas.ChapterWithDetails])
async def get_manga_chapters(
    manga_id: int,
    unread_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get all chapters for a specific manga across all scanlators.

    - **manga_id**: The ID of the manga
    - **unread_only**: Only return unread chapters
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    # Verify manga exists
    manga = db.query(models.Manga).filter(models.Manga.id == manga_id).first()
    if not manga:
        raise HTTPException(status_code=404, detail=f"Manga with ID {manga_id} not found")

    # Get all manga_scanlator IDs for this manga
    manga_scanlator_ids = db.query(models.MangaScanlator.id).filter(
        models.MangaScanlator.manga_id == manga_id
    ).all()

    ms_ids = [ms_id[0] for ms_id in manga_scanlator_ids]

    # Query chapters
    query = db.query(models.Chapter).options(
        joinedload(models.Chapter.manga_scanlator).joinedload(models.MangaScanlator.scanlator)
    ).filter(models.Chapter.manga_scanlator_id.in_(ms_ids))

    if unread_only:
        query = query.filter(models.Chapter.read == False)

    # Order by chapter number (descending, numeric sort)
    query = query.order_by(cast(models.Chapter.chapter_number, Float).desc())

    chapters = query.offset(skip).limit(limit).all()

    return chapters
