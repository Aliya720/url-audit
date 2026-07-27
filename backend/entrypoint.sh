#!/bin/sh
set -e

# Run Django database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files if needed
echo "Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

exec "$@"
