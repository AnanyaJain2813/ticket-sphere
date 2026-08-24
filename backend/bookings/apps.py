from django.apps import AppConfig


class BookingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bookings'

    def ready(self):
        import sys
        # Prevent running in management commands, migrations, or tests
        if any(arg in sys.argv for arg in ['runserver', 'core.asgi', 'gunicorn']) or 'wsgi' in sys.argv:
            if 'test' not in sys.argv:
                from bookings.tasks import start_background_cleanup_thread
                start_background_cleanup_thread()
