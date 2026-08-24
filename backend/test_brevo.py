import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.conf import settings
from bookings.tasks import dispatch_email_for_booking
from bookings.models import Booking

try:
    booking = Booking.objects.last()
    if not booking:
        print("❌ No bookings exist in the local database to test with.")
        sys.exit(1)
        
    print(f"🔄 Attempting to send email for booking ID: {booking.id}")
    print(f"📧 Using BREVO_API_KEY: {'[SET]' if getattr(settings, 'BREVO_API_KEY', None) else '[MISSING]'}")
    
    dispatch_email_for_booking(booking.id, "jainananya2800@gmail.com", "Test User", "1234567890")
    print("✅ Success! Email sent via Brevo.")
except Exception as e:
    print("❌ Error from Brevo API:")
    import traceback
    traceback.print_exc()
