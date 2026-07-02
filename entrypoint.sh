#!/bin/bash
set -e

echo "Applying database migrations..."
python backend/manage.py migrate --noinput

echo "Starting server..."
# Execute the CMD passed from the Dockerfile
exec "$@"
