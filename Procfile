web: python backend/manage.py migrate --noinput && python backend/manage.py seed_db && cd backend && daphne -b 0.0.0.0 -p $PORT core.asgi:application
worker: cd backend && C_FORCE_ROOT=1 celery -A core worker -l INFO
beat: cd backend && celery -A core beat -l INFO
