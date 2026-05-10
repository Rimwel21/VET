#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# You can add other build steps here like:
# python manage.py migrate
