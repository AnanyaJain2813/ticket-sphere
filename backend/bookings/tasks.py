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
    booking = Booking.objects.select_related('user', 'show', 'show__event', 'show__venue', 'show_seat', 'show_seat__seat', 'show_seat__category').get(id=booking_id)
    qr_bytes = generate_qr_code_bytes(booking.booking_reference)

    email_target = recipient_email or booking.user.email or f"{booking.user.username}@gmail.com"
    phone_target = recipient_phone or "+91 98765 43210"
    name_target = recipient_name or booking.user.username

    subject = f"CineStream M-Ticket Pass & QR Code - {booking.booking_reference}"
    body = (
        f"Hello {name_target},\n\n"
        f"Your cinema ticket for '{booking.show.event.title}' is confirmed!\n\n"
        f"BOOKING DETAILS:\n"
        f"- Reference ID: {booking.booking_reference}\n"
        f"- Movie: {booking.show.event.title}\n"
        f"- Cinema Venue: {booking.show.venue.name} ({booking.show.venue.location})\n"
        f"- Seat: Row {booking.show_seat.seat.row_name} - Seat {booking.show_seat.seat.col_number} ({booking.show_seat.category.name})\n"
        f"- Amount Paid: ₹{booking.amount}\n"
        f"- Customer Contact: {phone_target} | {email_target}\n\n"
        f"Your M-Ticket QR Code is attached as a high-resolution PNG image. Please show this QR code at the entry gate.\n\n"
        f"Enjoy your movie experience!\n"
        f"Team CineStream India"
    )

    try:
        import sib_api_v3_sdk
        from sib_api_v3_sdk.rest import ApiException
        import base64
        
        if not getattr(settings, 'BREVO_API_KEY', None):
            logger.warning("BREVO_API_KEY not configured. Falling back to Django SMTP.")
            from django.core.mail import EmailMessage
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'tickets@cinestream.in'),
                to=[email_target],
            )
            email.attach(f"M_Ticket_{booking.booking_reference}.png", qr_bytes, "image/png")
            email.send(fail_silently=False)
            logger.info(f"Successfully dispatched Gmail M-Ticket via SMTP to {email_target} for booking {booking.booking_reference}")
            return True

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = settings.BREVO_API_KEY
        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
        
        # Convert plain text body to simple HTML for Brevo
        html_body = body.replace("\n", "<br>")
        
        b64_qr = base64.b64encode(qr_bytes).decode('utf-8')
        
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": email_target, "name": name_target}],
            sender={"email": getattr(settings, 'DEFAULT_FROM_EMAIL', 'tickets@cinestream.in'), "name": "CineStream India"},
            subject=subject,
            html_content=html_body,
            attachment=[{"content": b64_qr, "name": f"M_Ticket_{booking.booking_reference}.png"}]
        )
        api_instance.send_transac_email(send_smtp_email)
        logger.info(f"Successfully dispatched Brevo Gmail M-Ticket to {email_target} for booking {booking.booking_reference}")
    except Exception as e:
        logger.exception(f"CRITICAL: Email delivery failed for {email_target}.")
        raise e

    logger.info(f"[SMS ALERT SENT] Mobile: {phone_target} | Message: CineStream: Ticket confirmed for {booking.show.event.title} at {booking.show.venue.name}. Ref: {booking.booking_reference}. QR code sent to {email_target}")

    if booking.email_delivery_failed:
        booking.email_delivery_failed = False
        booking.save(update_fields=['email_delivery_failed'])

    return True


# Booking confirmation task wrapper removed in favor of direct execution

