from django.db import transaction
from django.db.models.functions import Now
from django.db.models import Q
from bookings.models import ShowSeat
import logging

logger = logging.getLogger(__name__)

from bookings.services import broadcast_seat_updates

def release_expired_holds():
    """
    Periodically releases expired seat holds back to 'available'.
    """
    # 1. Find all expired seats
    expired_seats = list(ShowSeat.objects.filter(
        status='held',
        hold_expires_at__lte=Now(),
        is_waitlist_offer=False  # Waitlist offers are resolved by expire_waitlist_offers
    ).values('id', 'show_id'))

    if not expired_seats:
        return 0

    seat_ids = [seat['id'] for seat in expired_seats]
    
    # 2. Update them efficiently in bulk
    updated_count = ShowSeat.objects.filter(id__in=seat_ids).update(
        status='available',
        holder=None,
        hold_expires_at=None
    )
    
    # 3. Broadcast updates to WebSockets grouped by show_id
    show_updates = {}
    for seat in expired_seats:
        show_id = seat['show_id']
        if show_id not in show_updates:
            show_updates[show_id] = []
        show_updates[show_id].append({
            'id': str(seat['id']),
            'status': 'available',
            'hold_expires_at': None
        })
        
    for show_id, updates in show_updates.items():
        broadcast_seat_updates(show_id, updates)
    
    if updated_count > 0:
        logger.info(f"Released {updated_count} expired holds and broadcasted WebSocket updates.")
        
    return updated_count


import io
import qrcode
from django.core.mail import EmailMessage
from django.conf import settings
from bookings.models import Booking


def generate_qr_code_bytes(data: str) -> bytes:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def dispatch_email_for_booking(booking_id, recipient_email=None, recipient_name=None, recipient_phone=None):
    """Send a booking confirmation email with the QR code attached using Django's built-in email."""
    booking = Booking.objects.select_related(
        'user', 'show', 'show__event', 'show__venue',
        'show_seat', 'show_seat__seat', 'show_seat__category'
    ).get(id=booking_id)

    qr_bytes = generate_qr_code_bytes(booking.booking_reference)
    email_target = recipient_email or booking.user.email or f"{booking.user.username}@gmail.com"
    name_target = recipient_name or booking.user.username

    subject = f"CineStream M-Ticket - {booking.booking_reference}"
    body = (
        f"Hello {name_target},\n\n"
        f"Your cinema ticket for '{booking.show.event.title}' is confirmed!\n\n"
        f"BOOKING DETAILS:\n"
        f"- Reference ID: {booking.booking_reference}\n"
        f"- Movie: {booking.show.event.title}\n"
        f"- Venue: {booking.show.venue.name} ({booking.show.venue.location})\n"
        f"- Seat: Row {booking.show_seat.seat.row_name} - Seat {booking.show_seat.seat.col_number} ({booking.show_seat.category.name})\n"
        f"- Amount Paid: ₹{booking.amount}\n\n"
        f"Your QR Code is attached. Show it at the entry gate.\n\n"
        f"Enjoy your movie!\n"
        f"Team CineStream"
    )

    try:
        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'tickets@cinestream.in'),
            to=[email_target],
        )
        email.attach(f"M_Ticket_{booking.booking_reference}.png", qr_bytes, "image/png")
        email.send(fail_silently=False)
        logger.info(f"Confirmation email sent to {email_target} for booking {booking.booking_reference}")

        if booking.email_delivery_failed:
            booking.email_delivery_failed = False
            booking.save(update_fields=['email_delivery_failed'])
        return True
    except Exception as e:
        logger.exception(f"Email delivery failed for booking {booking_id}: {e}")
        Booking.objects.filter(id=booking_id).update(email_delivery_failed=True)
        raise
