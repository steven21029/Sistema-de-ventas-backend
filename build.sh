#!/usr/bin/env bash
set -o errexit

python -m pip install -r requirements.txt
python manage.py collectstatic --no-input



# Run migrations only after explicit approval.
# python manage.py migrate
