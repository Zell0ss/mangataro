#!/bin/bash

# Setup cron job for scheduled tracking

SCRIPT_PATH="/data/mangataro/scripts/run_scheduled_tracking.sh"
CRON_SCHEDULE="0 9,21 * * *"  # 9 AM and 9 PM daily

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "$SCRIPT_PATH"; then
  echo "Cron job already exists"
  exit 0
fi

# Add cron job
(crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $SCRIPT_PATH") | crontab -

echo "Cron job added successfully!"
echo "Schedule: Daily at 9:00 AM and 9:00 PM"
echo "Command: $SCRIPT_PATH"
echo ""
echo "To view cron jobs: crontab -l"
echo "To remove cron job: crontab -e (then delete the line)"
