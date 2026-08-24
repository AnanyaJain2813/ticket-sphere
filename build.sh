#!/usr/bin/env bash
# exit on error
set -o errexit

echo "=== Building Backend on Render ==="
pip install -r requirements.txt

echo "=== Running Migrations ==="
python backend/manage.py migrate --noinput

echo "=== Seeding Database ==="
python backend/manage.py seed_db
