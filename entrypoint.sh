#!/bin/sh

set -e

# Function to check if postgres is ready
postgres_ready() {
  python << END
import sys
import psycopg2
try:
    conn = psycopg2.connect(
        dbname="${DB_NAME}",
        user="${DB_USER}",
        password="${DB_PASSWORD}",
        host="${DB_HOST}",
        port="${DB_PORT}",
    )
except psycopg2.OperationalError:
    sys.exit(1)
sys.exit(0)
END
}

# Wait for postgres to become available
until postgres_ready; do
  echo "Waiting for PostgreSQL to become available..."
  sleep 2
done
echo "PostgreSQL is available"

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Check if superuser exists before creating one
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  echo "Checking if superuser exists..."
  python << END
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='${DJANGO_SUPERUSER_USERNAME}').exists():
    print("Creating superuser...")
    User.objects.create_superuser('${DJANGO_SUPERUSER_USERNAME}', '', '${DJANGO_SUPERUSER_PASSWORD}')
    print("Superuser created!")
else:
    print("Superuser already exists!")
END
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the application
echo "Starting application..."
exec "$@" 