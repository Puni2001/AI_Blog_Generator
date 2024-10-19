#!/bin/bash

# Update pip
echo "Updating pip..."
python3.9 pip install -U pip

# Install dependencies

echo "Installing project dependencies..."
pip install -r requirements.txt

# Collect staticfiles
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Build process completed!"
