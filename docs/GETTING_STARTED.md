# Getting Started with MangaTaro

Get MangaTaro running in 15 minutes. This guide covers installation, first run, and optional production setup.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [First Run](#first-run)
- [Adding Your First Manga](#adding-your-first-manga)
- [Setting Up Tracking](#setting-up-tracking)
- [Production Deployment (Optional)](#production-deployment-optional)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- **Python 3.10+** - Check: `python3 --version`
- **Node.js 18+** - Check: `node --version`
- **MariaDB/MySQL 10.6+** - Check: `mysql --version`
- **Git** - Check: `git --version`

---

## Installation

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd mangataro
```

### Step 2: Database Setup

**Create database and user:**

```bash
mysql -u root -p
```

```sql
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

### Step 3: Python Environment

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

### Step 4: Configuration

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

### Step 5: Frontend Setup

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

---

## First Run

### Start the API Server

Open a terminal and run:

```bash
cd /data/mangataro
source .venv/bin/activate
uvicorn api.main:app --reload --host 0.0.0.0 --port 8008
```

**Verify API is running:**

```bash
curl http://localhost:8008/health
```

Expected response: `{"status":"healthy","api":"operational"}`

### Start the Frontend

Open a **new terminal** and run:

```bash
cd /data/mangataro/frontend
npm run dev
```

### Access the Web Interface

Open your browser and navigate to: **http://localhost:4343**

You should see the MangaTaro homepage:

![Homepage](images/homepage_updates.png)

**What you can access:**
- **Frontend:** http://localhost:4343
- **API Docs:** http://localhost:8008/docs (Interactive Swagger UI)

---

## Adding Your First Manga

### Using the Web UI

Navigate to: **http://localhost:4343/admin/add-manga**

![Add Manga Form](images/add-manga-empty.png)

**Fill in the form:**

1. **Title** (required) - Manga name
   - Example: "Solo Leveling"
   - Checked for duplicates

2. **Alternative Titles** (optional) - Comma-separated
   - Example: "나 혼자만 레벨업, I Level Up Alone"

3. **Scanlator** (required) - Select from dropdown
   - Must have a plugin implemented (AsuraScans, RavenScans, etc.)

4. **Scanlator URL** (required) - Direct URL to manga on scanlator site
   - Example: "https://asuracomic.net/series/solo-leveling"
   - **Validated by actually scraping!** If the URL is invalid, you'll get an error

5. **Cover URL** (optional) - Direct link to cover image
   - Will be downloaded to `data/img/`
   - Leave blank to use scanlator's cover

6. **Cover Filename** (optional) - Use local file instead
   - If you already have the cover in `data/img/`
   - Example: "solo-leveling.jpg"

**Submit:**

- Click "Add Manga"
- The system will:
  1. Validate the scanlator URL by scraping it
  2. Download the cover image
  3. Create manga entry and scanlator mapping atomically
  4. Redirect you to the manga detail page

![Manga Detail Page](images/manga-detail.png)

---

## Setting Up Tracking

### Manual Tracking Test

Test chapter tracking with one manga:

```bash
cd /data/mangataro
source .venv/bin/activate
python scripts/track_chapters.py --limit 1 --visible
```

**What happens:**
1. Browser window opens (you can watch it work!)
2. Navigates to scanlator website
3. Scrapes chapter list
4. Saves chapters to database
5. Shows summary of new chapters found

### Mapping More Manga

If you have existing manga that need scanlator mappings:

Navigate to: **http://localhost:4343/admin/map-sources**

![Map Sources](images/map-sources.png)

**Steps:**
1. Select a scanlator from dropdown (defaults to AsuraScans)
2. See list of unmapped manga for that scanlator
3. Enter the scanlator URL for each manga
4. URL is validated automatically
5. Click "Add" - row fades out on success
6. Switch scanlators to map more manga

### Automated Tracking

Choose one of these methods to run tracking automatically:

#### Option 1: Cron Job (Simple)

Add to your crontab:

```bash
# Edit crontab
crontab -e

# Add this line (runs every 6 hours)
0 */6 * * * cd /data/mangataro && .venv/bin/python scripts/track_chapters.py >> logs/cron.log 2>&1
```

#### Option 2: Systemd Timer (Recommended for Production)

Create tracking service:

**File:** `/etc/systemd/system/mangataro-tracking.service`

```ini
[Unit]
Description=MangaTaro Chapter Tracking
After=network.target mangataro-api.service

[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/data/mangataro
Environment="PATH=/data/mangataro/.venv/bin"
ExecStart=/data/mangataro/scripts/run_scheduled_tracking.sh
```

Create tracking timer:

**File:** `/etc/systemd/system/mangataro-tracking.timer`

```ini
[Unit]
Description=Run MangaTaro tracking twice daily

[Timer]
OnCalendar=09:00
OnCalendar=21:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable mangataro-tracking.timer
sudo systemctl start mangataro-tracking.timer

# Check status
sudo systemctl status mangataro-tracking.timer
```

#### Option 3: n8n Workflow (Advanced)

See `n8n/README.md` for n8n workflow configuration.

### Testing Discord Notifications

If you configured `DISCORD_WEBHOOK_URL` in `.env`:

```bash
# Trigger tracking with notification
curl -X POST http://localhost:8008/api/tracking/trigger \
  -H "Content-Type: application/json" \
  -d '{"notify": true}'
```

Check your Discord channel for new chapter notifications!

---

## Production Deployment (Optional)

For production use, set up systemd services for auto-start and process management.

### API Service

**File:** `/etc/systemd/system/mangataro-api.service`

```ini
[Unit]
Description=MangaTaro API
After=network.target mariadb.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/data/mangataro
Environment="PATH=/data/mangataro/.venv/bin"
ExecStart=/data/mangataro/.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8008
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Frontend Service

**File:** `/etc/systemd/system/mangataro-frontend.service`

```ini
[Unit]
Description=MangaTaro Frontend
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/data/mangataro/frontend
ExecStart=/usr/bin/npm run dev
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Note:** For true production, use `npm run build && npm run preview` or serve with Nginx.

### Enable and Start Services

```bash
sudo systemctl daemon-reload
sudo systemctl enable mangataro-api mangataro-frontend
sudo systemctl start mangataro-api mangataro-frontend
```

### Service Management Commands

```bash
# Start services
sudo systemctl start mangataro-api mangataro-frontend

# Stop services
sudo systemctl stop mangataro-api mangataro-frontend

# Restart services
sudo systemctl restart mangataro-api

# Check status
sudo systemctl status mangataro-api

# View logs
sudo journalctl -u mangataro-api -f
sudo journalctl -u mangataro-frontend -n 50
```

### Nginx Reverse Proxy (Optional)

Serve everything on port 80 with Nginx:

**File:** `/etc/nginx/sites-available/mangataro`

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:4343;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8008/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API docs
    location /docs {
        proxy_pass http://localhost:8008/docs;
    }
}
```

**Enable:**

```bash
sudo ln -s /etc/nginx/sites-available/mangataro /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL with Let's Encrypt (Optional)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
```

---

## Troubleshooting

### Database Connection Failed

**Symptoms:** API won't start, database errors in logs

**Solutions:**
- Verify credentials in `.env` match database user
- Check MariaDB is running: `sudo systemctl status mariadb`
- Test connection: `mysql -u mangataro_user -p`
- Check database exists: `mysql -u mangataro_user -p -e "SHOW DATABASES;"`

### API Won't Start

**Symptoms:** Can't access http://localhost:8008

**Solutions:**
- Check port 8008 is available: `lsof -i :8008`
- Kill conflicting process: `pkill -f "uvicorn"`
- Verify virtual environment activated: `which python` should show `.venv/bin/python`
- Check logs for detailed error message

### Playwright Errors

**Symptoms:** "Browser not found" or scraping fails

**Solutions:**
```bash
# Install browsers
playwright install chromium

# Install system dependencies
playwright install-deps chromium

# Check installation
playwright install --dry-run
```

### Frontend Build Errors

**Symptoms:** `npm run dev` fails

**Solutions:**
```bash
# Clear cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Check Node version (need 18+)
node --version

# Update npm
npm install -g npm@latest
```

### Chapters Not Appearing

**Symptoms:** Tracking runs but no chapters in database

**Solutions:**
- Verify manga-scanlator mapping has `manually_verified=1`:
  ```sql
  SELECT * FROM manga_scanlator WHERE manga_id = X;
  UPDATE manga_scanlator SET manually_verified=1 WHERE id = Y;
  ```
- Check scanlator class_name matches plugin:
  ```sql
  SELECT id, name, class_name FROM scanlators;
  ```
- Run tracking with visible browser to debug:
  ```bash
  python scripts/track_chapters.py --manga-id X --visible
  ```

### Frontend Can't Connect to API

**Symptoms:** "Network error" in browser console

**Solutions:**
- Verify API is running: `curl http://localhost:8008/health`
- Check `CORS_ORIGINS` in `.env` includes `http://localhost:4343`
- Check `PUBLIC_API_URL` in `frontend/.env` is correct
- Restart both API and frontend after config changes

### Permission Denied Errors

**Symptoms:** Can't write to logs, can't create files

**Solutions:**
```bash
# Fix ownership
sudo chown -R ubuntu:ubuntu /data/mangataro

# Fix permissions
chmod -R 755 /data/mangataro
chmod -R 775 /data/mangataro/logs
chmod -R 775 /data/mangataro/data
```

---

## Next Steps

Congratulations! MangaTaro is now running. 🎉

**Recommended next steps:**

1. **Explore the web interface** - Browse your library at http://localhost:4343
2. **Add more manga** - Use the /admin/add-manga page
3. **Set up Discord notifications** - Get alerts for new chapters
4. **Configure automation** - Let tracking run automatically
5. **Read the User Guide** - Learn all the features: [USER_GUIDE.md](USER_GUIDE.md)
6. **Explore the API** - Check out http://localhost:8008/docs

**For developers:**
- [Developer Guide](DEVELOPER_GUIDE.md) - Extend the system
- [Plugin Quick Reference](PLUGIN_QUICK_REFERENCE.md) - Add new scanlators

Enjoy tracking your manga! 📚
