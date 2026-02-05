# n8n Workflow Automation

This directory contains n8n workflows for automating MangaTaro chapter tracking and notifications.

## Installation

N8n is installed via a dockerfile in the `/data/n8n` directory.

Access n8n at: http://localhost:5678

## Workflows

### 1. Scheduled Chapter Tracking

**File:** `scheduled_tracking.json`

**Purpose:** Runs chapter tracking daily and sends notifications for new chapters.

**Schedule:** Every day at 9:00 AM and 9:00 PM

**Steps:**
1. Trigger on schedule (cron: `0 9,21 * * *`)
2. HTTP Request: POST to `/api/tracking/trigger`
3. Wait 30 seconds
4. HTTP Request: GET job status
5. Loop until job completes
6. Log results

**Setup:**
1. Import workflow from `scheduled_tracking.json`
2. Update "MangaTaro API Base URL" to `http://localhost:8008`
3. Activate workflow

### 2. Discord Notifications Webhook

**File:** `discord_notifications.json`

**Purpose:** Receives webhook notifications and forwards to Discord with rich formatting.

**Trigger:** Webhook `/webhook/manga-updates`

**Steps:**
1. Receive webhook with chapter data
2. Format Discord message with embeds
3. Send to Discord webhook
4. Log notification

**Setup:**
1. Import workflow from `discord_notifications.json`
2. Update Discord webhook URL in "Send to Discord" node
3. Activate workflow
4. Note the webhook URL (shown in Webhook node)

## Configuration

### Environment Variables

Add to `.env`:

```bash
# n8n Webhook (if using webhook-based notifications)
N8N_WEBHOOK_URL=http://localhost:5678/webhook/manga-updates
```

## Testing

### Test Scheduled Tracking

```bash
# Manually execute the workflow in n8n UI
# Or trigger via API:
curl -X POST http://localhost:5678/webhook/trigger-tracking
```

### Test Discord Notifications

```bash
# Send test notification via API
curl -X POST http://localhost:8008/api/tracking/test-notification
```

## Troubleshooting

**Issue:** Workflows not executing

**Solution:**
- Check n8n is running: `docker ps | grep n8n`
- Check workflow is activated (toggle in n8n UI)
- Check logs: `docker logs n8n`

**Issue:** Notifications not sending

**Solution:**
- Verify Discord webhook URL is correct
- Test webhook: `curl -X POST DISCORD_WEBHOOK_URL -H "Content-Type: application/json" -d '{"content":"test"}'`
- Check n8n execution logs

## Advanced: Systemd Service

To run n8n as a system service:

```bash
sudo cp ../systemd/n8n.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable n8n
sudo systemctl start n8n
```
