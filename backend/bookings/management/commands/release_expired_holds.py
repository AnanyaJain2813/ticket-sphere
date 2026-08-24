from django.core.management.base import BaseCommand
from bookings.tasks import cleanup_expired_holds_and_offers

class Command(BaseCommand):
    help = 'Cleans up expired holds and waitlist offers.'

    def handle(self, *args, **options):
        self.stdout.write('Starting cleanup of expired holds and waitlist offers...')
        cleanup_expired_holds_and_offers()
        self.stdout.write(self.style.SUCCESS('Successfully cleaned up expired holds and offers.'))
