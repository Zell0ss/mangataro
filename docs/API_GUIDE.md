# Manga Tracker API Guide

## Overview

The Manga Tracker API is a FastAPI-based REST API for tracking manga chapters across multiple scanlation groups. It provides endpoints for managing manga, scanlators, chapters, and tracking relationships.

## Getting Started

### Prerequisites

- Python 3.8+
- MySQL database
- Virtual environment with all dependencies installed

### Starting the API Server

#### Option 1: Using the run script (recommended)

```bash
./scripts/run_api.sh
```

#### Option 2: Manual start

```bash
# Activate virtual environment
source .venv/bin/activate

# Run uvicorn
uvicorn api.main:app --reload --host 0.0.0.0 --port 8008
```

### Accessing the API

Once started, the API will be available at:

- **API Base URL**: http://localhost:8008
- **Interactive API Docs (Swagger UI)**: http://localhost:8008/docs
- **Alternative Docs (ReDoc)**: http://localhost:8008/redoc
- **Health Check**: http://localhost:8008/health

## API Structure

### Directory Layout

```
api/
├── __init__.py           # Package initialization
├── main.py               # FastAPI application entry point
├── database.py           # Database connection and session management
├── models.py             # SQLAlchemy ORM models
├── schemas.py            # Pydantic request/response models
├── dependencies.py       # FastAPI dependency injection
├── utils.py              # Utility functions
└── routers/              # API route modules
    ├── __init__.py
    ├── manga.py          # Manga CRUD endpoints
    ├── scanlators.py     # Scanlator management endpoints
    └── tracking.py       # Chapter tracking endpoints
```

### Architecture

The API follows a clean architecture pattern:

1. **Models (models.py)**: SQLAlchemy ORM models defining database schema
2. **Schemas (schemas.py)**: Pydantic models for request validation and response serialization
3. **Dependencies (dependencies.py)**: Shared dependencies like database sessions
4. **Routers**: Modular route handlers organized by domain
5. **Main (main.py)**: Application configuration and router registration

## Schemas Documentation

### Manga Schemas

#### MangaCreate
Request schema for creating a new manga.

```python
{
    "title": "string",              # Required
    "alternative_titles": "string", # Optional
    "mangataro_id": "string",      # Optional
    "mangataro_url": "string",     # Optional
    "cover_filename": "string",    # Optional
    "status": "reading"            # Optional: reading|completed|on_hold|plan_to_read
}
```

#### MangaUpdate
Request schema for updating an existing manga (all fields optional).

```python
{
    "title": "string",
    "alternative_titles": "string",
    "mangataro_id": "string",
    "mangataro_url": "string",
    "cover_filename": "string",
    "status": "reading"
}
```

#### MangaResponse
Response schema for a manga.

```python
{
    "id": 1,
    "title": "string",
    "alternative_titles": "string",
    "mangataro_id": "string",
    "mangataro_url": "string",
    "cover_filename": "string",
    "status": "reading",
    "date_added": "2026-02-01T12:00:00",
    "last_checked": "2026-02-01T12:00:00",
    "created_at": "2026-02-01T12:00:00",
    "updated_at": "2026-02-01T12:00:00"
}
```

#### MangaWithScanlators
Extended manga response with nested scanlator relationships.

```python
{
    ...MangaResponse fields,
    "manga_scanlators": [
        {
            "id": 1,
            "manga_id": 1,
            "scanlator_id": 1,
            "scanlator_manga_url": "string",
            "manually_verified": false,
            "notes": "string",
            "created_at": "2026-02-01T12:00:00",
            "updated_at": "2026-02-01T12:00:00",
            "scanlator": {
                "id": 1,
                "name": "Asura Scans",
                "class_name": "AsuraScansExtractor",
                "base_url": "https://asura.gg",
                "active": true,
                "created_at": "2026-02-01T12:00:00",
                "updated_at": "2026-02-01T12:00:00"
            }
        }
    ]
}
```

### Scanlator Schemas

#### ScanlatorCreate
```python
{
    "name": "string",        # Required
    "class_name": "string",  # Required - Extractor class name
    "base_url": "string",    # Optional
    "active": true           # Optional, default: true
}
```

#### ScanlatorResponse
```python
{
    "id": 1,
    "name": "string",
    "class_name": "string",
    "base_url": "string",
    "active": true,
    "created_at": "2026-02-01T12:00:00",
    "updated_at": "2026-02-01T12:00:00"
}
```

### Chapter Schemas

#### ChapterCreate
```python
{
    "manga_scanlator_id": 1,           # Required
    "chapter_number": "123.5",         # Required
    "chapter_title": "string",         # Optional
    "chapter_url": "string",           # Required
    "published_date": "2026-02-01T12:00:00",  # Optional
    "detected_date": "2026-02-01T12:00:00",   # Auto-set if not provided
    "read": false                      # Optional, default: false
}
```

#### ChapterResponse
```python
{
    "id": 1,
    "manga_scanlator_id": 1,
    "chapter_number": "123.5",
    "chapter_title": "string",
    "chapter_url": "string",
    "published_date": "2026-02-01T12:00:00",
    "detected_date": "2026-02-01T12:00:00",
    "read": false,
    "created_at": "2026-02-01T12:00:00",
    "updated_at": "2026-02-01T12:00:00"
}
```

#### ChapterWithDetails
Extended chapter response with nested manga-scanlator and scanlator details.

### MangaScanlator Schemas

#### MangaScanlatorCreate
```python
{
    "manga_id": 1,                    # Required
    "scanlator_id": 1,                # Required
    "scanlator_manga_url": "string",  # Required
    "manually_verified": false,       # Optional, default: false
    "notes": "string"                 # Optional
}
```

## Configuration

### Environment Variables

The API uses the following environment variables (defined in `.env`):

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mangataro
DB_USER=mangataro_user
DB_PASSWORD=mangataro_password

# API Configuration
API_HOST=0.0.0.0
API_PORT=8008
API_DEBUG=true

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:4343
```

### CORS Configuration

The API is configured to allow cross-origin requests from specified origins. By default:
- http://localhost:3000 (for React/Next.js frontends)
- http://localhost:4343 (for Astro frontends)

To modify allowed origins, update the `CORS_ORIGINS` variable in `.env`.

## Development Workflow

### 1. Making Changes

When adding new features or modifying the API:

1. **Models**: Update `api/models.py` if database schema changes
2. **Schemas**: Add/update Pydantic models in `api/schemas.py`
3. **Routes**: Implement endpoints in appropriate router files
4. **Dependencies**: Add shared dependencies to `api/dependencies.py`

### 2. Testing Changes

```bash
# Start the API in development mode (auto-reload enabled)
./scripts/run_api.sh

# In another terminal, test endpoints
curl http://localhost:8008/health
curl http://localhost:8008/docs  # Open in browser

# open the swager directly
http://localhost:8008/docs

```

### 3. API Documentation

The API automatically generates interactive documentation:

- **Swagger UI** (`/docs`): Interactive API testing interface
- **ReDoc** (`/redoc`): Clean, readable API documentation

These are automatically updated when you modify route handlers or schemas.

### 4. Adding New Endpoints

Example of adding a new endpoint to a router:

```python
# In api/routers/manga.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from api.dependencies import get_db
from api import schemas, models

router = APIRouter()

@router.get("/", response_model=List[schemas.MangaResponse])
async def list_manga(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all manga with pagination"""
    manga = db.query(models.Manga).offset(skip).limit(limit).all()
    return manga
```

### 5. Database Migrations

When you modify models:

1. Update the model in `api/models.py`
2. Create migration SQL or use Alembic (if configured)
3. Apply migrations to the database
4. Update corresponding Pydantic schemas in `api/schemas.py`

## API Endpoints (To Be Implemented)

### Manga Endpoints (`/api/manga`)

- `GET /api/manga` - List all manga
- `GET /api/manga/{id}` - Get specific manga
- `POST /api/manga` - Create new manga
- `PUT /api/manga/{id}` - Update manga
- `DELETE /api/manga/{id}` - Delete manga

### Scanlator Endpoints (`/api/scanlators`)

- `GET /api/scanlators` - List all scanlators
- `GET /api/scanlators/{id}` - Get specific scanlator
- `POST /api/scanlators` - Create new scanlator

### Tracking Endpoints (`/api/tracking`)

- `GET /api/tracking/chapters/unread` - Get unread chapters
- `PUT /api/tracking/chapters/{id}/mark-read` - Mark chapter as read
- `PUT /api/tracking/chapters/{id}/mark-unread` - Mark chapter as unread
- `POST /api/tracking/manga/{id}/scanlators` - Add scanlator to manga

## Error Handling

The API uses standard HTTP status codes:

- `200 OK` - Successful request
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

Error responses follow this format:

```json
{
    "detail": "Error message description"
}
```

## Best Practices

1. **Always use Pydantic schemas** for request/response validation
2. **Use dependency injection** for database sessions
3. **Keep routers focused** - one domain per router file
4. **Document endpoints** - add docstrings to all route handlers
5. **Use proper HTTP methods** - GET, POST, PUT, DELETE
6. **Validate input** - let Pydantic handle validation
7. **Handle errors gracefully** - use HTTPException with appropriate status codes

## Troubleshooting

### API won't start

- Check that the database is running and accessible
- Verify `.env` file exists with correct credentials
- Ensure virtual environment is activated
- Check for port conflicts (default: 8008)

### Database connection errors

- Verify MySQL is running
- Check database credentials in `.env`
- Ensure database exists (run `scripts/create_db.sql` if needed)

### CORS errors

- Add your frontend URL to `CORS_ORIGINS` in `.env`
- Restart the API after changing environment variables

### Module import errors

- Ensure you're running from the project root directory
- Check that all dependencies are installed: `pip install -r requirements.txt`
- Verify virtual environment is activated

## Next Steps

- **Task 8**: Implement manga and scanlator CRUD endpoints
- **Task 9**: Implement chapter tracking endpoints
- **Task 10**: Add authentication and authorization
- **Task 11**: Implement automated chapter detection
- **Task 12**: Build frontend dashboard

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
