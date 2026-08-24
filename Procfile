web: python backend/manage.py migrate --noinput && python backend/manage.py seed_db && cd backend && daphne -b 0.0.0.0 -p $PORT core.asgi:application
