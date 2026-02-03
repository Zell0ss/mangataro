# MangaTaro - Manga Chapter Tracker

Track manga chapters across multiple scanlation groups after MangaTaro shutdown.

## Features

- 📚 Import manga collection from MangaTaro
- 🔍 Automatic chapter tracking via scanlator plugins
- 🌐 Modern web interface with Astro + TailwindCSS
- 🔔 Discord notifications for new chapters
- 📊 REST API with OpenAPI documentation
- ⚡ Automated tracking via cron/n8n
- 🧩 Extensible scanlator plugin architecture

## Quick Start

```bash
# Setup (see docs/SETUP.md for details)
cp .env.example .env
# Edit .env with your database credentials

# Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# Run API
uvicorn api.main:app --reload

# Run frontend (new terminal)
cd frontend && npm run dev

# Access at http://localhost:4343
```

## Documentation

- **[Setup Guide](docs/SETUP.md)** - Installation and configuration
- **[User Guide](docs/USER_GUIDE.md)** - How to use the system
- **[API Guide](docs/api_guide.md)** - API documentation
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment

## Architecture

- **Backend:** FastAPI + SQLAlchemy + MariaDB
- **Frontend:** Astro + TailwindCSS + Alpine.js
- **Scraping:** Playwright + Plugin Architecture
- **Automation:** n8n / Cron

## Status

✅ Phase 1: Data Extraction (100%)
✅ Phase 2: Tracking System (100%)
✅ Phase 3: API (100%)
✅ Phase 4: Frontend (100%)
✅ Phase 5: Automation (100%)
✅ Phase 6: Documentation (100%)

**Project Status:** Production Ready 🎉

## License

MIT

## Support

For issues and questions, see the documentation or open an issue.
