#!/bin/bash
set -e

echo "Applying database migrations..."
cd backend
python manage.py migrate --noinput

echo "Starting server..."
# Execute the CMD passed from the Dockerfile
exec "$@"
