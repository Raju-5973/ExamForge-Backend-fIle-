#!/usr/bin/env bash
set -o errexit

echo "=== Starting ExamForge Backend ==="
echo "PORT: $PORT"
echo "DEBUG: $DEBUG"

exec gunicorn examforge_backend.wsgi \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 1 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
