#!/bin/bash

# Scheduled Chapter Tracking Script
# Run this via cron for automated chapter tracking
#
# Example crontab entry (daily at 9 AM and 9 PM):
# 0 9,21 * * * /data/mangataro/scripts/run_scheduled_tracking.sh

set -e

# Configuration
API_URL="http://localhost:8008"
LOG_DIR="/data/mangataro/logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="$LOG_DIR/scheduled_tracking_$TIMESTAMP.log"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

echo "=== MangaTaro Scheduled Tracking ===" | tee -a "$LOG_FILE"
echo "Started at: $(date)" | tee -a "$LOG_FILE"

# Trigger tracking
echo "Triggering tracking job..." | tee -a "$LOG_FILE"
RESPONSE=$(curl -s -X POST "$API_URL/api/tracking/trigger" \
  -H "Content-Type: application/json" \
  -d '{"notify": true}')

JOB_ID=$(echo "$RESPONSE" | grep -o '"job_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$JOB_ID" ]; then
  echo "ERROR: Failed to trigger tracking job" | tee -a "$LOG_FILE"
  echo "Response: $RESPONSE" | tee -a "$LOG_FILE"
  exit 1
fi

echo "Job ID: $JOB_ID" | tee -a "$LOG_FILE"

# Poll for completion (max 10 minutes)
MAX_ATTEMPTS=60
ATTEMPT=0
STATUS="pending"

while [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ] && [ "$STATUS" != "completed" ] && [ "$STATUS" != "failed" ]; do
  sleep 10
  ATTEMPT=$((ATTEMPT + 1))

  STATUS_RESPONSE=$(curl -s "$API_URL/api/tracking/jobs/$JOB_ID")
  STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*' | cut -d'"' -f4)

  echo "Attempt $ATTEMPT: Status = $STATUS" | tee -a "$LOG_FILE"
done

# Get final status
FINAL_STATUS=$(curl -s "$API_URL/api/tracking/jobs/$JOB_ID")
echo "=== Final Status ===" | tee -a "$LOG_FILE"
echo "$FINAL_STATUS" | tee -a "$LOG_FILE"

NEW_CHAPTERS=$(echo "$FINAL_STATUS" | grep -o '"new_chapters_found":[0-9]*' | cut -d':' -f2)

echo "Completed at: $(date)" | tee -a "$LOG_FILE"
echo "New chapters found: $NEW_CHAPTERS" | tee -a "$LOG_FILE"

if [ "$STATUS" = "completed" ]; then
  echo "SUCCESS: Tracking completed successfully" | tee -a "$LOG_FILE"
  exit 0
else
  echo "ERROR: Tracking failed or timed out" | tee -a "$LOG_FILE"
  exit 1
fi
