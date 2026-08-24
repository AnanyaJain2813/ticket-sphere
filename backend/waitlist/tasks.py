from django.db import transaction
from django.db.models.functions import Now
from waitlist.models import WaitlistEntry
from bookings.models import ShowSeat
from waitlist.services import promote_waitlist_for_seat
import logging

logger = logging.getLogger(__name__)

def expire_waitlist_offers():
    """
    Periodically scans for expired 'offered' waitlist entries.
    When an offer expires, the waitlist entry is marked as 'expired',
    the seat hold is released, and the seat is immediately offered to 
    the next person in the waitlist.
    """
    # 1. Find all expired offers
    # We do not use bulk update here initially because we need to process
    # each expired offer one by one to trigger the next waitlist promotion.
    
    expired_entries = WaitlistEntry.objects.filter(
        status='offered',
        offer_expires_at__lte=Now()
    ).values_list('id', flat=True)
    
    processed_count = 0
    
    for entry_id in expired_entries:
        try:
            with transaction.atomic():
                # Lock the specific waitlist entry
                entry = WaitlistEntry.objects.select_for_update().get(
                    id=entry_id, 
                    status='offered',
                    offer_expires_at__lte=Now()
                )
                
                # Mark as expired
                entry.status = 'expired'
                entry.offer_expires_at = None
                entry.save(update_fields=['status', 'offer_expires_at'])
                
                # Find the seat that was held for this user
                seat = ShowSeat.objects.select_for_update().filter(
                    show_id=entry.show_id,
                    category_id=entry.category_id,
                    status='held',
                    holder_id=entry.user_id
                ).first()
                
                if seat:
                    # Promote the next person in line for this seat
                    promote_waitlist_for_seat(seat)
                    
                processed_count += 1
                logger.info(f"Expired waitlist offer {entry.id} for user {entry.user_id}")
                
        except WaitlistEntry.DoesNotExist:
            # Another worker might have processed it already, safe to ignore
            continue
            
    return processed_count

from django.conf import settings

def dispatch_waitlist_offer_email(user_email, seat_label, show_title, expires_in_minutes):
    """
    Sends an email notifying a user that a waitlist seat is now available for them.
    """
    html_content = f"""
    <html>
        <body>
            <h1 style="color: #06b6d4;">Great News! A Seat Freed Up!</h1>
            <p>You were on the waitlist for <strong>{show_title}</strong>.</p>
            <p>We've successfully reserved seat <strong>{seat_label}</strong> for you!</p>
            <p style="color: #ef4444; font-weight: bold;">
                You have {expires_in_minutes} minutes to open the app and checkout before this offer expires and is passed to the next person.
            </p>
            <p>Open CineStream now to complete your booking!</p>
        </body>
    </html>
    """

    from django.core.mail import EmailMessage
    
    email = EmailMessage(
        subject="Your CineStream Waitlist Offer is Ready!",
        body=html_content,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'tickets@cinestream.in'),
        to=[user_email],
    )
    email.content_subtype = "html"
    try:
        email.send(fail_silently=False)
        logger.info(f"Waitlist offer email sent to {user_email}.")
    except Exception as e:
        logger.error(f"Failed to send waitlist email to {user_email}: {e}")

