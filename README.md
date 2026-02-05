# MangaTaro - Manga Chapter Tracker

Track manga chapters across multiple scanlation groups after MangaTaro shutdown.

## Features

- 📚 Import manga collection from MangaTaro
- 🔍 Automatic chapter tracking via scanlator plugins
- 🌐 Modern web interface with Astro + TailwindCSS
- 🛠️ Web-based admin UI for mapping manga to scanlators
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

### 📚 For Users

**Getting Started:**
- **[Setup Guide](docs/SETUP.md)** - Installation and configuration
- **[Quick Start](QUICK_START.md)** - Task-by-task setup walkthrough
- **[User Guide](docs/USER_GUIDE.md)** - How to use the web interface

**Operation:**
- **[Tracking Guide](docs/TRACKING_GUIDE.md)** - Complete chapter tracking guide
- **[Quick Start Tracking](docs/TRACKING_QUICK_START.md)** - 5-minute tracking setup
- **[Service Management](docs/SERVICE_MANAGEMENT.md)** - Systemd service commands
- **[Automation Setup](n8n/README.md)** - n8n workflow configuration

**Reference:**
- **[API Guide](docs/API_GUIDE.md)** - REST API documentation
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment
- **[Project Status](TOMORROW.md)** - Current status (14/14 tasks complete)

### 🛠️ For Developers

**Start Here:**
- **[CLAUDE.md](CLAUDE.md)** - **Primary developer guide** (architecture, critical info, workflows)

**Plugin Development:**
- **[AsuraScans Plugin Guide](ASURASCANS_PLUGIN_USAGE.md)** - Example plugin usage
- **[Scanlator Quick Reference](SCANLATOR_QUICK_REFERENCE.md)** - Create new plugins

**Architecture:**
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Directory organization
- **[Scanlators List](docs/SCANLATORS.md)** - Reference list from MangaTaro

**Historical:**
- **[Legacy Documentation](docs/legacy/)** - Archived docs, test results, implementation plans

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
