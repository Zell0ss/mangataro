from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import manga, scanlators, tracking
import os
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

app = FastAPI(
    title="Manga Tracker API",
    description="API for tracking manga chapters across scanlation groups",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:4321,http://localhost:4343").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging configuration
logger.info("Starting Manga Tracker API")


# Health check endpoints
@app.get("/", tags=["health"])
async def root():
    """Root endpoint - API status check"""
    return {
        "status": "ok",
        "message": "Manga Tracker API",
        "version": "1.0.0"
    }


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "api": "operational"
    }


# Include routers (will be implemented in Tasks 8-9)
app.include_router(manga.router, prefix="/api/manga", tags=["manga"])
app.include_router(scanlators.router, prefix="/api/scanlators", tags=["scanlators"])
app.include_router(tracking.router, prefix="/api/tracking", tags=["tracking"])


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Manga Tracker API started successfully")
    logger.info(f"API Documentation available at: /docs")
    logger.info(f"CORS enabled for origins: {cors_origins}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Manga Tracker API shutting down")
