import os
import threading
import time
import logging

logger = logging.getLogger(__name__)

def run_scheduler_loop():
    # Wait for Django to complete setup
    time.sleep(3)
    logger.info("Background scheduler thread started successfully.")
    
    # Lazy imports to ensure Django is fully loaded
    from bookings.tasks import release_expired_holds
    from waitlist.tasks import expire_waitlist_offers
    
    while True:
        try:
            release_expired_holds()
        except Exception as e:
            logger.error(f"Error running release_expired_holds: {e}")
            
        try:
            expire_waitlist_offers()
        except Exception as e:
            logger.error(f"Error running expire_waitlist_offers: {e}")
            
        time.sleep(30)

def start_scheduler():
    # Only run in the active process (reloader main, or production container)
    run_main = os.environ.get('RUN_MAIN')
    if run_main == 'true' or not run_main:
        if not getattr(start_scheduler, '_started', False):
            start_scheduler._started = True
            thread = threading.Thread(target=run_scheduler_loop, name="TicketSphereScheduler", daemon=True)
            thread.start()
