# MangaTaro Setup Guide

Complete installation and setup instructions for MangaTaro.

## Prerequisites

- Python 3.10+
- Node.js 18+
- MariaDB/MySQL 10.6+
- Git

---

## Installation

### 1. Clone Repository

```bash
git clone <repository-url>
cd mangataro
```

### 2. Database Setup

**Create database and user:**

```bash
mysql -u root -p

CREATE DATABASE mangataro CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'mangataro_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON mangataro.* TO 'mangataro_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**Import schema:**

```bash
mysql -u mangataro_user -p mangataro < scripts/create_db.sql
```

### 3. Python Environment

**Create virtual environment:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Install Playwright browsers:**

```bash
playwright install chromium
```

### 4. Configuration

**Copy environment template:**

```bash
cp .env.example .env
```

**Edit `.env`:**

```bash
# Database
DB_HOST=localhost
DB_PORT=3306
DB_NAME=mangataro
DB_USER=mangataro_user
DB_PASSWORD=your_secure_password_here

# API
API_HOST=0.0.0.0
API_PORT=8008
API_DEBUG=false
CORS_ORIGINS=http://localhost:3000,http://localhost:4343

# Scraping
PLAYWRIGHT_TIMEOUT=30000
SCRAPING_DELAY_MIN=2
SCRAPING_DELAY_MAX=5

# Notifications (optional)
NOTIFICATION_TYPE=discord
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK
```

### 5. Frontend Setup

**Install dependencies:**

```bash
cd frontend
npm install
```

**Configure frontend:**

```bash
cp .env.example .env
```

Edit `frontend/.env`:

```bash
PUBLIC_API_URL=http://localhost:8008
```

**Build frontend (optional):**

```bash
npm run build
```

---

## Running the Application

### Development Mode

**Terminal 1 - API:**

```bash
cd /data/mangataro
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8008
```

**Terminal 2 - Frontend:**

```bash
cd /data/mangataro/frontend
npm run dev
```

**Access:**
- Frontend: http://localhost:4343
- API Docs: http://localhost:8008/docs

### Production Mode

See `docs/DEPLOYMENT.md` for systemd service setup.

---

## Initial Data Import

### Import from MangaTaro

If you have a MangaTaro export:

```bash
python scripts/extract_mangataro.py
```

This imports:
- Manga metadata
- Cover images
- Scanlator information

### Add Tracking Sources

Map manga to scanlator URLs:

```bash
python scripts/add_manga_source.py
```

Follow the interactive prompts.

---

## Verify Installation

### Test Database Connection

```bash
mysql -u mangataro_user -p mangataro -e "SELECT COUNT(*) FROM mangas;"
```

### Test API

```bash
curl http://localhost:8008/health
```

Expected: `{"status":"healthy","api":"operational"}`

### Test Tracking

```bash
python scripts/track_chapters.py --limit 1 --visible
```

Expected: Browser opens, fetches chapters, inserts into database.

### Test Frontend

```bash
curl http://localhost:4343/
```

Expected: HTML response with page content.

---

## Optional Setup

### Discord Notifications

1. Create Discord webhook (Server Settings > Integrations > Webhooks)
2. Add to `.env`:
   ```
   NOTIFICATION_TYPE=discord
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   ```
3. Test:
   ```bash
   curl -X POST http://localhost:8008/api/tracking/test-notification
   ```

### Automated Tracking

**Option 1: Cron**

```bash
./scripts/setup_cron.sh
```

**Option 2: Systemd Timer**

See `docs/DEPLOYMENT.md`.

**Option 3: n8n**

See `n8n/README.md`.

---

## Troubleshooting

### Database Connection Failed

- Verify credentials in `.env`
- Check MariaDB is running: `sudo systemctl status mariadb`
- Test connection: `mysql -u mangataro_user -p`

### API Won't Start

- Check port 8008 is available: `lsof -i :8008`
- Verify virtual environment is activated
- Check logs for errors

### Playwright Errors

- Install browsers: `playwright install chromium`
- Check system dependencies: `playwright install-deps`

### Frontend Build Errors

- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node version: `node --version` (should be 18+)

---

## Next Steps

1. Import your manga collection
2. Add scanlator mappings
3. Run initial chapter tracking
4. Set up Discord notifications
5. Configure automated tracking
6. Explore the API documentation

See `docs/USER_GUIDE.md` for usage instructions.
