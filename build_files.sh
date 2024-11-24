#!/bin/bash

# Update pip
echo "Updating pip..."
python3 -m pip install --upgrade pip

# Install project dependencies
echo "Installing project dependencies..."
pip install -r requirements.txt

# Handle the missing PIL issue for favicon creation (make sure Pillow is installed in requirements.txt)
echo "Creating favicon..."
python3 create_favicon.py

# Collect static files for Django project
echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear

echo "Build process completed!"
