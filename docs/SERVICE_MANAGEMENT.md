# MangaTaro Service Management

MangaTaro runs as a systemd service that manages both the API backend and frontend dev server.

## Service Name
`mangataro`

## Service Commands

### Start the service
```bash
sudo systemctl start mangataro
```

### Stop the service
```bash
sudo systemctl stop mangataro
```

### Restart the service
```bash
sudo systemctl restart mangataro
```

### Check service status
```bash
sudo systemctl status mangataro
```

### View service logs
```bash
# View recent logs
sudo journalctl -u mangataro -n 50

# Follow logs in real-time
sudo journalctl -u mangataro -f

# View logs since boot
sudo journalctl -u mangataro -b
```

### Enable/Disable auto-start on boot
```bash
# Enable (already enabled by default)
sudo systemctl enable mangataro

# Disable
sudo systemctl disable mangataro
```

## What the Service Does

The `mangataro` service runs two processes:

1. **API Backend** (FastAPI)
   - Port: 8008
   - URL: http://localhost:8008
   - Docs: http://localhost:8008/docs

2. **Frontend** (Astro dev server)
   - Port: 4343
   - URL: http://localhost:4343

## Service Files

- **Service file**: `/etc/systemd/system/mangataro.service`
- **Startup script**: `/data/mangataro/scripts/start_servers.sh`

## Troubleshooting

### Service won't start
```bash
# Check service status for error details
sudo systemctl status mangataro

# Check recent logs
sudo journalctl -u mangataro -n 100
```

### Port already in use
```bash
# Check what's using port 8008
sudo lsof -i :8008

# Check what's using port 4343
sudo lsof -i :4343

# Kill any conflicting processes
sudo pkill -f "uvicorn api.main:app"
sudo pkill -f "astro dev"
```

### Service running but can't connect
```bash
# Verify ports are listening
netstat -tlnp | grep -E ":(8008|4343)"

# Test API
curl http://localhost:8008/health

# Test frontend
curl http://localhost:4343/ | head -10
```

### Restart after code changes
```bash
# API changes are auto-reloaded (uvicorn --reload)
# Frontend changes are auto-reloaded (astro dev)
# No restart needed for code changes!

# Only restart for configuration changes:
sudo systemctl restart mangataro
```

## Manual Start (Without Service)

If you need to run the servers manually without systemd:

### API only
```bash
cd /data/mangataro
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8008 --reload
```

### Frontend only
```bash
cd /data/mangataro/frontend
npm run dev -- --host 0.0.0.0
```

### Both (using the script)
```bash
/data/mangataro/scripts/start_servers.sh
```

## Production Deployment

For production, you should:

1. Use uvicorn with Gunicorn for the API
2. Build the frontend for production (`npm run build`)
3. Serve the built frontend with a web server (Nginx/Apache)
4. Update the systemd service accordingly

See the deployment guide for details.
