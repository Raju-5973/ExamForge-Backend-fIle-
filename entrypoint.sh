#!/bin/bash
set -e

echo "=== Running database migrations ==="
python manage.py migrate --no-input

echo "=== Starting Gunicorn on port ${PORT:-8000} ==="
exec gunicorn examforge_backend.wsgi \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 1 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
