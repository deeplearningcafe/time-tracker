#!/bin/bash

# Configuration
echo "--- Starting Time Tracker ---"

# 1. Load and Sanitize .env
if [ -f .env ]; then
  source .env
  DEBUG=$(echo "$DEBUG" | tr -d '\r' | tr -d ' ')
fi

echo "Checking if the drive directory ${LOCAL_MOUNT} exists"
mkdir -p "$LOCAL_MOUNT"

# 1. DOWNLOAD (Sync Down)
echo "Checking for updates from cloud..."
if command -v rclone &>/dev/null; then
  rclone copy "$REMOTE_NAME:$REMOTE_PATH" "$LOCAL_MOUNT"
  echo "Skip"
else
  echo "Warning: rclone not found. Skipping cloud download."
fi

export SYNC_DRIVE_PATH=$(realpath "$LOCAL_MOUNT")

source ~/miniforge3/bin/activate track

echo "Launching App..."
echo "Debug status: [${DEBUG,,}]"

if [[ "${DEBUG,,}" == "true" ]]; then
  echo "DEBUG mode detected: Launching Backend and Frontend in separate terminals..."

  gnome-terminal --title="Django Backend" -- bash -c "source ~/miniforge3/bin/activate track && python backend/manage.py runserver"

  gnome-terminal --title="Vue Frontend" -- bash -c "cd frontend && npm run dev"

  echo "---------------------------------------------------"
  echo "  App is running in debug mode in separate windows."
  echo "  Press [ENTER] in this terminal to STOP and SYNC."
  echo "---------------------------------------------------"
  read -p ""

  echo "Closing instances..."
  fuser -k 8000/tcp >/dev/null 2>&1

  fuser -k 5173/tcp >/dev/null 2>&1

else
  python backend/manage.py runserver
fi

echo ""
echo "--- App Stopped. Synchronizing Data... ---"

# Trigger Django to export the latest DB state to the encrypted file
python backend/manage.py export_sync_data

if command -v rclone &>/dev/null; then
  rclone sync "$LOCAL_MOUNT" "$REMOTE_NAME:$REMOTE_PATH"
  echo "Sync complete."
else
  echo "Warning: rclone not found. Changes saved locally but not uploaded."
fi

echo "--- Goodbye! ---"
