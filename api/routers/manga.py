from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import cast, Float, and_
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


@router.get("/unmapped", response_model=schemas.UnmappedMangaResponse)
async def get_unmapped_manga(
    scanlator_id: Optional[int] = Query(None, description="The scanlator ID to check against"),
    db: Session = Depends(get_db)
):
    """
    Get all manga that do NOT have a verified mapping to the specified scanlator.

    Returns manga that are not in the manga_scanlator table with manually_verified=1
    for the given scanlator_id, ordered by title.

    - **scanlator_id**: The scanlator ID to check against (required)
    """
    # Validate scanlator_id is provided
    if scanlator_id is None:
        raise HTTPException(status_code=400, detail="scanlator_id query parameter is required")

    # Validate scanlator_id is valid integer
    if scanlator_id <= 0:
        raise HTTPException(status_code=400, detail="scanlator_id must be a positive integer")

    # Verify scanlator exists
    scanlator = db.query(models.Scanlator).filter(models.Scanlator.id == scanlator_id).first()
    if not scanlator:
        raise HTTPException(status_code=404, detail=f"Scanlator with ID {scanlator_id} not found")

    # Get all manga IDs that have verified mappings to this scanlator
    verified_manga_ids = db.query(models.MangaScanlator.manga_id).filter(
        and_(
            models.MangaScanlator.scanlator_id == scanlator_id,
            models.MangaScanlator.manually_verified == True
        )
    ).all()

    # Extract IDs from query result
    verified_ids = [manga_id[0] for manga_id in verified_manga_ids]

    # Query manga NOT in the verified list
    query = db.query(models.Manga)
    if verified_ids:
        query = query.filter(models.Manga.id.notin_(verified_ids))

    # Order by title
    unmapped_manga = query.order_by(models.Manga.title).all()

    # Build response
    return {
        "scanlator_id": scanlator.id,
        "scanlator_name": scanlator.name,
        "base_url": scanlator.base_url,
        "unmapped_manga": unmapped_manga,
        "count": len(unmapped_manga)
    }


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


@router.post("/with-scanlator", response_model=schemas.MangaResponse, status_code=201)
async def create_manga_with_scanlator(
    manga_data: schemas.MangaWithScanlatorCreate,
    db: Session = Depends(get_db)
):
    """
    Create manga with scanlator mapping atomically.

    Validates URL by actually scraping, downloads cover image,
    creates manga and mapping in single transaction.

    - **manga_data**: Manga and scanlator mapping data
    """
    from api.logging_config import get_logger
    from api.utils import download_image
    from scanlators import get_scanlator_by_name
    from playwright.async_api import async_playwright

    logger = get_logger("api")

    # Check if manga with same title already exists
    existing_manga = db.query(models.Manga).filter(
        models.Manga.title == manga_data.title
    ).first()

    if existing_manga:
        raise HTTPException(
            status_code=400,
            detail=f"Manga '{manga_data.title}' already exists (ID: {existing_manga.id})"
        )

    # Check if scanlator URL already exists (prevents duplicate mappings)
    existing_url = db.query(models.MangaScanlator).filter(
        models.MangaScanlator.scanlator_manga_url == manga_data.scanlator_manga_url
    ).first()

    if existing_url:
        # Get the manga details for better error message
        manga = db.query(models.Manga).filter(
            models.Manga.id == existing_url.manga_id
        ).first()
        raise HTTPException(
            status_code=400,
            detail=f"This scanlator URL is already mapped to manga '{manga.title}' (ID: {manga.id})"
        )

    # Verify scanlator exists
    scanlator = db.query(models.Scanlator).filter(
        models.Scanlator.id == manga_data.scanlator_id
    ).first()

    if not scanlator:
        raise HTTPException(
            status_code=404,
            detail=f"Scanlator with ID {manga_data.scanlator_id} not found"
        )

    # Validate URL matches scanlator's base URL
    if scanlator.base_url and not manga_data.scanlator_manga_url.startswith(scanlator.base_url):
        raise HTTPException(
            status_code=400,
            detail=f"URL must start with scanlator's base URL: {scanlator.base_url}"
        )

    # Validate URL by actually scraping it
    logger.info(f"Validating URL for manga '{manga_data.title}': {manga_data.scanlator_manga_url}")

    try:
        # Use class_name instead of name for plugin lookup
        plugin_class = get_scanlator_by_name(scanlator.class_name)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                plugin = plugin_class(page)
                # Try to get chapters - if this succeeds, URL is valid
                await plugin.obtener_capitulos(manga_data.scanlator_manga_url)
                logger.info(f"URL validation successful for '{manga_data.title}'")
            finally:
                await page.close()
                await browser.close()

    except Exception as e:
        logger.error(f"URL validation failed for '{manga_data.title}': {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=f"Could not validate scanlator URL: {str(e)}"
        )

    # Download cover image
    cover_filename = None

    try:
        logger.info(f"Downloading cover image from: {manga_data.cover_url}")
        cover_filename = download_image(
            manga_data.cover_url,
            "/data/mangataro/data/img"
        )
        logger.info(f"Cover image downloaded: {cover_filename}")
    except Exception as e:
        logger.warning(f"Cover download failed: {str(e)}")

        # Use fallback filename if provided
        if manga_data.cover_filename:
            cover_filename = manga_data.cover_filename
            logger.info(f"Using fallback cover filename: {cover_filename}")
        else:
            raise HTTPException(
                status_code=500,
                detail="Cover image download failed and no fallback filename provided"
            )

    # Create manga and mapping in transaction
    try:
        # Create manga
        db_manga = models.Manga(
            title=manga_data.title,
            alternative_titles=manga_data.alternative_titles,
            cover_filename=cover_filename,
            status=manga_data.status,
            date_added=datetime.utcnow()
        )

        db.add(db_manga)
        db.flush()  # Get manga.id without committing

        # Create mapping
        db_mapping = models.MangaScanlator(
            manga_id=db_manga.id,
            scanlator_id=manga_data.scanlator_id,
            scanlator_manga_url=manga_data.scanlator_manga_url,
            manually_verified=True
        )

        db.add(db_mapping)
        db.commit()
        db.refresh(db_manga)

        logger.info(f"Successfully created manga '{manga_data.title}' with ID {db_manga.id}")

        return db_manga

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create manga '{manga_data.title}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create manga: {str(e)}"
        )


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
