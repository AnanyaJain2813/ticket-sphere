import threading
import time
import sys
from django.apps import AppConfig

def run_background_cleanup():
    from bookings.tasks import cleanup_expired_holds_and_offers
    from django.db import connection
    while True:
        try:
            time.sleep(60)
            cleanup_expired_holds_and_offers()
        except Exception as e:
            print(f"Background cleanup error: {e}")
        finally:
            # Ensure we close the DB connection after each run so we don't exhaust connection pools
            connection.close()

class BookingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bookings'

    def ready(self):
        # Prevent starting the background thread multiple times or during tests/migrations
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv or 'daphne' in sys.argv or 'uvicorn' in sys.modules:
            thread = threading.Thread(target=run_background_cleanup, daemon=True)
            thread.start()
