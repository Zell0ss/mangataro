from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from api.dependencies import get_db
from api import schemas, models
from datetime import datetime

router = APIRouter()


@router.get("/", response_model=List[schemas.ScanlatorResponse])
async def list_scanlators(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    active_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    List all scanlators.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **active_only**: Only return active scanlators
    """
    query = db.query(models.Scanlator)

    if active_only:
        query = query.filter(models.Scanlator.active == True)

    query = query.order_by(models.Scanlator.name)

    scanlators = query.offset(skip).limit(limit).all()

    return scanlators


@router.get("/{scanlator_id}", response_model=schemas.ScanlatorResponse)
async def get_scanlator(scanlator_id: int, db: Session = Depends(get_db)):
    """
    Get a specific scanlator by ID.

    - **scanlator_id**: The ID of the scanlator to retrieve
    """
    scanlator = db.query(models.Scanlator).filter(
        models.Scanlator.id == scanlator_id
    ).first()

    if not scanlator:
        raise HTTPException(status_code=404, detail=f"Scanlator with ID {scanlator_id} not found")

    return scanlator


@router.post("/", response_model=schemas.ScanlatorResponse, status_code=201)
async def create_scanlator(
    scanlator: schemas.ScanlatorCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new scanlator.

    - **scanlator**: Scanlator data to create
    """
    # Check if scanlator with same name already exists
    existing = db.query(models.Scanlator).filter(
        models.Scanlator.name == scanlator.name
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Scanlator with name '{scanlator.name}' already exists"
        )

    db_scanlator = models.Scanlator(
        name=scanlator.name,
        class_name=scanlator.class_name,
        base_url=scanlator.base_url,
        active=scanlator.active
    )

    db.add(db_scanlator)
    db.commit()
    db.refresh(db_scanlator)

    return db_scanlator


@router.put("/{scanlator_id}", response_model=schemas.ScanlatorResponse)
async def update_scanlator(
    scanlator_id: int,
    scanlator_update: schemas.ScanlatorUpdate,
    db: Session = Depends(get_db)
):
    """
    Update a scanlator's information.

    - **scanlator_id**: The ID of the scanlator to update
    - **scanlator_update**: Fields to update
    """
    scanlator = db.query(models.Scanlator).filter(
        models.Scanlator.id == scanlator_id
    ).first()

    if not scanlator:
        raise HTTPException(status_code=404, detail=f"Scanlator with ID {scanlator_id} not found")

    # Update only provided fields
    update_data = scanlator_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(scanlator, field, value)

    scanlator.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(scanlator)

    return scanlator


@router.delete("/{scanlator_id}", status_code=204)
async def delete_scanlator(scanlator_id: int, db: Session = Depends(get_db)):
    """
    Delete a scanlator (and all related data due to cascade).

    - **scanlator_id**: The ID of the scanlator to delete
    """
    scanlator = db.query(models.Scanlator).filter(
        models.Scanlator.id == scanlator_id
    ).first()

    if not scanlator:
        raise HTTPException(status_code=404, detail=f"Scanlator with ID {scanlator_id} not found")

    db.delete(scanlator)
    db.commit()

    return None
