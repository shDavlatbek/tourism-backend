#!/bin/sh

set -e

# Apply database migrations
# echo "Applying database migrations..."
# python manage.py makemigrations main common media resource user

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Check if superuser exists before creating one
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
  echo "Checking if superuser exists..."
  python << END
import django
django.setup()
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='${DJANGO_SUPERUSER_USERNAME}').exists():
    print("Creating superuser...")
    User.objects.create_superuser('${DJANGO_SUPERUSER_USERNAME}', '${DJANGO_SUPERUSER_EMAIL}', '${DJANGO_SUPERUSER_PASSWORD}')
    print("Superuser created!")
else:
    print("Superuser already exists!")
END
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the application
echo "Starting development server..."
exec "$@" 