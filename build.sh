#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Building Tailwind CSS..."
# In Render, we might need to ensure npm is available. Render's standard Python env doesn't have Node by default.
# But we'll configure Render to use a custom build command or use the render.yaml trick (or multiple pre-build steps).
# We can just run the django-tailwind build command. It requires Node.
python manage.py tailwind build

echo "Collecting static files..."
python manage.py collectstatic --no-input

echo "Running database migrations..."
python manage.py migrate
