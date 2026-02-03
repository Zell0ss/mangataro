# MangaTaro Deployment Guide

Production deployment instructions for MangaTaro.

## Systemd Services

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

**Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable mangataro-api
sudo systemctl start mangataro-api
sudo systemctl status mangataro-api
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

**For production, use:**

```bash
npm run build
npm run preview
```

Or serve with nginx (see below).

---

## Nginx Reverse Proxy

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

---

## Automated Tracking

### Systemd Timer

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

**Enable:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable mangataro-tracking.timer
sudo systemctl start mangataro-tracking.timer
sudo systemctl list-timers
```

---

## Security

### Environment Variables

- Never commit `.env` to version control
- Use strong database passwords
- Restrict API access with firewall rules

### CORS

Update `.env` with production domains:

```bash
CORS_ORIGINS=https://your-domain.com
```

### Database

- Use non-root user
- Enable SSL connections
- Regular backups

---

## Monitoring

### Logs

```bash
# API logs
sudo journalctl -u mangataro-api -f

# Frontend logs
sudo journalctl -u mangataro-frontend -f

# Tracking logs
ls -lah /data/mangataro/logs/
```

### Health Checks

```bash
# API health
curl http://localhost:8008/health

# Database
mysql -u mangataro_user -p -e "SELECT COUNT(*) FROM mangataro.chapters;"
```

---

## Backup

### Database Backup

```bash
mysqldump -u mangataro_user -p mangataro > backup_$(date +%Y%m%d).sql
```

### Automated Backups

Add to cron:

```bash
0 2 * * * mysqldump -u mangataro_user -pPASSWORD mangataro | gzip > /backups/mangataro_$(date +\%Y\%m\%d).sql.gz
```

---

## Updates

### Pull Latest Changes

```bash
cd /data/mangataro
git pull
source .venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install
```

### Restart Services

```bash
sudo systemctl restart mangataro-api
sudo systemctl restart mangataro-frontend
```

---

For setup instructions, see `docs/SETUP.md`.
For usage guide, see `docs/USER_GUIDE.md`.
