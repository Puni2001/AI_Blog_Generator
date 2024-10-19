#!/bin/bash

# Update pip
echo "Updating pip..."
python3 -m pip install --upgrade pip

# Install dependencies
echo "Installing project dependencies..."
python3 -m pip install --upgrade pip
pip install -r requirements.txt

echo "Creating favicon..."
python3 create_favicon.py

# Collect staticfiles
echo "Collecting static files..."
python3 manage.py collectstatic --noinput --clear

echo "Build process completed!"
