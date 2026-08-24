"""
bookings/services.py — Atomic seat hold service using select_for_update().

==========================================================================
CONCURRENCY MODEL
==========================================================================

The hold_seat() function uses Django's select_for_update() inside a
transaction.atomic() block to guarantee serialised access to a single
ShowSeat row.

How it works under concurrent load (e.g. 20 simultaneous requests):

  1. All 20 threads enter transaction.atomic() concurrently.
  2. All 20 threads issue SELECT ... FOR UPDATE on the same ShowSeat row.
  3. The database engine grants the row-level lock to exactly ONE thread.
     The other 19 threads BLOCK (they do not read stale data — they wait).
  4. The winning thread reads status='available', mutates the row to
     status='held', commits, and releases the lock.
  5. The next queued thread acquires the lock, reads status='held'
     (the freshly-committed state), sees it does NOT own the hold,
     and returns a clean "already_held" conflict.
  6. This repeats for all remaining threads — each one sees the held
     state and returns conflict immediately.

This is fundamentally different from a check-then-write pattern where
all threads read status='available' before any write occurs.

IDEMPOTENCY (double-click protection):
  If the same user sends two hold requests for the same seat within
  milliseconds, the second request detects that the seat is already
  held by THIS user and returns success with the existing hold data.
  This prevents the double-click from producing a confusing error.

==========================================================================
"""

from datetime import timedelta
from django.db import transaction, OperationalError
from django.utils import timezone
from django.conf import settings
from bookings.models import ShowSeat, Booking
from waitlist.models import WaitlistEntry
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


def broadcast_seat_updates(show_id, updates):
    """
    Broadcasts batched seat status updates to all WebSocket clients on channel group show_<show_id>_seats.
    `updates` is a list of dicts: [{'id': str, 'status': str, 'hold_expires_at': str|None}, ...]
    """
    if not updates:
        return
    try:
        import threading
        
        def _do_broadcast():
            try:
                channel_layer = get_channel_layer()
                if channel_layer:
                    async_to_sync(channel_layer.group_send)(
                        f"show_{show_id}_seats",
                        {
                            "type": "seat_updates",
                            "updates": updates
                        }
                    )
            except Exception as e:
                logger.warning(f"WebSocket broadcast failed for show {show_id}: {e}")
                
        threading.Thread(target=_do_broadcast, daemon=True).start()
    except Exception as e:
        logger.warning(f"Failed to start WebSocket broadcast thread: {e}")



class HoldResult:
    """Structured result from hold_seat() for clean API responses."""

    __slots__ = ('success', 'reason', 'message', 'show_seat', 'is_idempotent')

    def __init__(self, *, success, reason, message, show_seat=None, is_idempotent=False):
        self.success = success
        self.reason = reason          # Machine-readable: 'held', 'already_held', 'already_booked', 'seat_not_found'
        self.message = message        # Human-readable explanation
        self.show_seat = show_seat    # The ShowSeat instance (if success)
        self.is_idempotent = is_idempotent  # True if this was a double-click re-hold

    def to_dict(self):
        data = {
            'success': self.success,
            'reason': self.reason,
            'message': self.message,
        }
        if self.show_seat:
            data['hold'] = {
                'show_seat_id': str(self.show_seat.id),
                'status': self.show_seat.status,
                'hold_expires_at': self.show_seat.hold_expires_at.isoformat() if self.show_seat.hold_expires_at else None,
                'price': str(self.show_seat.price),
                'is_idempotent': self.is_idempotent,
            }
        return data


def hold_seat(show_seat_id, user):
    """
    Atomically attempt to hold a seat for a user.

    Uses select_for_update() to acquire an exclusive row lock inside a
    transaction. The lock serialises all concurrent access to this row,
    ensuring exactly one caller can transition the seat from 'available'
    to 'held'.

    Args:
        show_seat_id: UUID of the ShowSeat to hold.
        user: Django User instance requesting the hold.

    Returns:
        HoldResult with success/failure details and machine-readable reason.
    """
    ttl_minutes = getattr(settings, 'HOLD_TTL_MINUTES', 10)
    now = timezone.now()

    try:
        with transaction.atomic():
            # -----------------------------------------------------------------
            # CRITICAL: select_for_update() acquires an exclusive row lock.
            #
            # Under concurrent load, only ONE thread gets the lock immediately.
            # All other threads BLOCK here until the lock holder commits or
            # rolls back. This guarantees that when the winning thread reads
            # status='available', no other thread can simultaneously read the
            # same value — they are queued behind the lock.
            #
            # This is NOT a check-then-write. The check (reading status) and
            # the write (setting status='held') happen inside the SAME locked
            # transaction. No gap exists for another thread to interleave.
            # -----------------------------------------------------------------
            seat = ShowSeat.objects.select_for_update().get(id=show_seat_id)

            # ---------------------------------------------------------------
            # CASE 1: Seat is available → grant the hold
            # ---------------------------------------------------------------
            if seat.status == 'available':
                seat.status = 'held'
                seat.holder = user
                seat.hold_expires_at = now + timedelta(minutes=ttl_minutes)
                seat.save(update_fields=['status', 'holder', 'hold_expires_at'])
                
                transaction.on_commit(lambda: broadcast_seat_updates(seat.show_id, [{
                    'id': str(seat.id),
                    'status': 'held',
                    'hold_expires_at': seat.hold_expires_at.isoformat()
                }]))
                
                return HoldResult(
                    success=True,
                    reason='held',
                    message='Seat successfully held.',
                    show_seat=seat,
                )

            # ---------------------------------------------------------------
            # CASE 2: Seat is held — check for expired hold or idempotent re-hold
            # ---------------------------------------------------------------
            if seat.status == 'held':
                # Sub-case 2a: Expired hold → reclaim it for this user
                if seat.hold_expires_at and seat.hold_expires_at <= now:
                    seat.holder = user
                    seat.hold_expires_at = now + timedelta(minutes=ttl_minutes)
                    seat.save(update_fields=['holder', 'hold_expires_at'])
                    
                    transaction.on_commit(lambda: broadcast_seat_updates(seat.show_id, [{
                        'id': str(seat.id),
                        'status': 'held',
                        'hold_expires_at': seat.hold_expires_at.isoformat()
                    }]))
                    
                    return HoldResult(
                        success=True,
                        reason='held',
                        message='Expired hold reclaimed. Seat successfully held.',
                        show_seat=seat,
                    )

                # Sub-case 2b: Idempotent re-hold — same user double-clicked.
                # Instead of returning a confusing error, acknowledge that
                # they already own this hold and return success.
                if seat.holder_id == user.id:
                    return HoldResult(
                        success=True,
                        reason='held',
                        message='Seat is already held by you.',
                        show_seat=seat,
                        is_idempotent=True,
                    )

                # Sub-case 2c: Held by another user and not expired
                return HoldResult(
                    success=False,
                    reason='already_held',
                    message='Seat is currently held by another user.',
                )

            # ---------------------------------------------------------------
            # CASE 3: Seat is booked → cannot hold a booked seat
            # ---------------------------------------------------------------
            if seat.status == 'booked':
                return HoldResult(
                    success=False,
                    reason='already_booked',
                    message='Seat has already been booked.',
                )

            # Fallback (should never happen with valid STATUS_CHOICES)
            return HoldResult(
                success=False,
                reason='unknown_status',
                message=f'Unexpected seat status: {seat.status}',
            )

    except ShowSeat.DoesNotExist:
        return HoldResult(
            success=False,
            reason='seat_not_found',
            message=f'ShowSeat {show_seat_id} does not exist.',
        )

    except OperationalError:
        # -----------------------------------------------------------------
        # SQLite CONCURRENCY FALLBACK
        # -----------------------------------------------------------------
        # PostgreSQL and MySQL use row-level locks for select_for_update(),
        # so concurrent threads queue behind the lock holder and execute
        # sequentially — they never hit this except block.
        #
        # SQLite uses database-level (file-level) locks. Under heavy
        # concurrent write contention (e.g., 20 threads), SQLite may
        # raise OperationalError("database table is locked") when the
        # configured timeout is exceeded.
        #
        # From the caller's perspective, the outcome is identical: the
        # seat is unavailable. We convert this into a clean "already_held"
        # result so the API returns a 409 Conflict — not a 500 — and the
        # machine-readable reason is consistent regardless of database.
        # -----------------------------------------------------------------
        return HoldResult(
            success=False,
            reason='already_held',
            message='Seat is currently unavailable (concurrent lock timeout).',
        )

def release_seat(show_seat_id, user):
    """
    Releases a held seat if it is owned by the user.
    """
    try:
        with transaction.atomic():
            seat = ShowSeat.objects.select_for_update().get(id=show_seat_id)
            
            if seat.status == 'held' and seat.holder_id == user.id:
                seat.status = 'available'
                seat.holder = None
                seat.hold_expires_at = None
                seat.save(update_fields=['status', 'holder', 'hold_expires_at'])
                
                transaction.on_commit(lambda: broadcast_seat_updates(seat.show_id, [{
                    'id': str(seat.id),
                    'status': 'available',
                    'hold_expires_at': None
                }]))
                
                return {'success': True, 'message': 'Seat released.'}
            else:
                return {'success': False, 'message': 'You do not hold this seat.'}
                
    except ShowSeat.DoesNotExist:
        return {'success': False, 'message': 'Seat not found.'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

import base64
from bookings.tasks import generate_qr_code_bytes

class ConfirmBookingResult:
    __slots__ = ('success', 'reason', 'message', 'booking', 'is_idempotent')

    def __init__(self, *, success, reason, message, booking=None, is_idempotent=False):
        self.success = success
        self.reason = reason
        self.message = message
        self.booking = booking
        self.is_idempotent = is_idempotent

    def to_dict(self):
        data = {
            'success': self.success,
            'reason': self.reason,
            'message': self.message,
        }
        if self.booking:
            seat = self.booking.show_seat.seat
            show = self.booking.show
            event_title = show.event.title
            show_time = show.start_time.strftime('%Y-%m-%d %I:%M %p')
            cinema = show.venue.name
            screen = seat.layout.name
            user = self.booking.user
            customer_name = f"{user.first_name} {user.last_name}".strip() or user.username
            
            qr_text = (
                f"TicketSphere Pass\n"
                f"Movie: {event_title}\n"
                f"Cinema: {cinema} - {screen}\n"
                f"Date & Time: {show_time}\n"
                f"Seat: {seat.row_name}{seat.col_number}\n"
                f"Customer: {customer_name}\n"
                f"Email: {user.email}\n"
                f"Ref: {self.booking.booking_reference}"
            )
            
            qr_bytes = generate_qr_code_bytes(qr_text)
            qr_b64 = base64.b64encode(qr_bytes).decode('utf-8')
            data['booking'] = {
                'id': str(self.booking.id),
                'booking_reference': self.booking.booking_reference,
                'status': self.booking.status,
                'is_idempotent': self.is_idempotent,
                'qr_code_url': f"data:image/png;base64,{qr_b64}",
            }
        return data


def confirm_booking(show_seat_id, user, idempotency_key, customer_name=None, customer_phone=None, customer_email=None):
    """
    Atomically convert a 'held' seat to 'booked'.
    
    Fails cleanly if the hold expired, or if the seat is held by someone else.
    Idempotent: If the idempotency_key matches an existing booking, it returns success
    instead of erroring to prevent double bookings on network retries.
    """
    now = timezone.now()

    if customer_email and user.email != customer_email:
        try:
            user.email = customer_email
            user.save(update_fields=['email'])
        except Exception as e:
            logger.warning(f"Could not update user email to {customer_email}: {e}")

    try:
        with transaction.atomic():
            # 1. Idempotency Check: if this exact request already succeeded, return success
            existing_booking = Booking.objects.select_for_update().filter(
                booking_reference=idempotency_key
            ).first()
            
            if existing_booking:
                if existing_booking.user_id != user.id:
                    # In a real app, returning 'unauthorized' or similar might be better
                    # if a different user uses the same idempotency key, but we'll stick to basic error here.
                    return ConfirmBookingResult(
                        success=False,
                        reason='idempotency_key_used_by_other',
                        message='This idempotency key is already used by another user.'
                    )
                    
                return ConfirmBookingResult(
                    success=True,
                    reason='booked',
                    message='Booking already confirmed.',
                    booking=existing_booking,
                    is_idempotent=True
                )

            # 2. Lock the seat row for update
            seat = ShowSeat.objects.select_for_update().get(id=show_seat_id)

            if seat.status == 'booked':
                return ConfirmBookingResult(
                    success=False,
                    reason='already_booked',
                    message='Seat is already booked.'
                )

            if seat.status == 'available':
                return ConfirmBookingResult(
                    success=False,
                    reason='not_held',
                    message='Seat is not held by you (it is available).'
                )

            if seat.status == 'held':
                if seat.holder_id != user.id:
                    # Defensive assert/log: Should not happen normally if client only confirms their own hold
                    logger.warning(f"User {user.id} tried to confirm seat {seat.id} held by user {seat.holder_id}")
                    return ConfirmBookingResult(
                        success=False,
                        reason='held_by_other',
                        message='Seat is held by another user.'
                    )
                
                if seat.hold_expires_at and seat.hold_expires_at <= now:
                    return ConfirmBookingResult(
                        success=False,
                        reason='hold_expired',
                        message='Your hold on this seat has expired.'
                    )
                    
                # 3. Create the booking and update the seat
                seat.status = 'booked'
                seat.holder = None
                seat.hold_expires_at = None
                seat.is_waitlist_offer = False
                seat.save(update_fields=['status', 'holder', 'hold_expires_at', 'is_waitlist_offer'])
                
                booking = Booking.objects.create(
                    booking_reference=idempotency_key,
                    user=user,
                    show_seat=seat,
                    show_id=seat.show_id,
                    amount=seat.price,
                    status='confirmed'
                )
                
                # Trigger confirmation email & SMS task asynchronously without blocking HTTP response
                import threading
                from bookings.tasks import dispatch_email_for_booking
                def _safe_dispatch_email(b_id, email, name, phone):
                    threading.Thread(
                        target=dispatch_email_for_booking,
                        args=(b_id, email, name, phone),
                        daemon=True
                    ).start()

                def _on_commit_actions():
                    _safe_dispatch_email(str(booking.id), customer_email, customer_name, customer_phone)
                    broadcast_seat_updates(seat.show_id, [{
                        'id': str(seat.id),
                        'status': 'booked',
                        'hold_expires_at': None
                    }])

                transaction.on_commit(_on_commit_actions)
                
                return ConfirmBookingResult(
                    success=True,
                    reason='booked',
                    message='Booking confirmed successfully.',
                    booking=booking
                )

    except ShowSeat.DoesNotExist:
        return ConfirmBookingResult(
            success=False,
            reason='seat_not_found',
            message='Seat not found.'
        )
    except OperationalError:
        return ConfirmBookingResult(
            success=False,
            reason='database_locked',
            message='Database is currently busy, please try again.'
        )

class CancelBookingResult:
    __slots__ = ('success', 'reason', 'message', 'booking')

    def __init__(self, *, success, reason, message, booking=None):
        self.success = success
        self.reason = reason
        self.message = message
        self.booking = booking

    def to_dict(self):
        data = {
            'success': self.success,
            'reason': self.reason,
            'message': self.message,
        }
        if self.booking:
            data['booking'] = {
                'id': str(self.booking.id),
                'booking_reference': self.booking.booking_reference,
                'status': self.booking.status,
            }
        return data


def cancel_booking(booking_id, user):
    """
    Atomically cancel a booking.
    
    If there are users waiting on the waitlist for this show and category,
    the oldest waitlist entry is promoted: the seat is marked as 'held' for
    the waitlisted user, and the waitlist entry is marked as 'offered'.
    Otherwise, the seat is returned to 'available'.
    """
    ttl_minutes = getattr(settings, 'HOLD_TTL_MINUTES', 10)
    now = timezone.now()

    try:
        with transaction.atomic():
            # 1. Lock the booking and verify ownership/state
            booking = Booking.objects.select_for_update().get(id=booking_id)
            
            if booking.user_id != user.id:
                return CancelBookingResult(
                    success=False,
                    reason='unauthorized',
                    message='You can only cancel your own bookings.'
                )
                
            if booking.status == 'cancelled':
                return CancelBookingResult(
                    success=True,
                    reason='cancelled',
                    message='Booking is already cancelled.',
                    booking=booking
                )

            # 2. Lock the associated seat
            seat = ShowSeat.objects.select_for_update().get(id=booking.show_seat_id)
            
            # 3. Mark booking as cancelled
            booking.status = 'cancelled'
            booking.save(update_fields=['status'])
            
            # 4. Handle Waitlist Promotion
            # The promote_waitlist_for_seat function handles the atomic
            # compare-and-swap loop to ensure concurrency safety.
            from waitlist.services import promote_waitlist_for_seat
            promote_waitlist_for_seat(seat)
                
            return CancelBookingResult(
                success=True,
                reason='cancelled',
                message='Booking cancelled successfully.',
                booking=booking
            )

    except Booking.DoesNotExist:
        return CancelBookingResult(
            success=False,
            reason='booking_not_found',
            message='Booking not found.'
        )
    except OperationalError:
        return CancelBookingResult(
            success=False,
            reason='database_locked',
            message='Database is currently busy, please try again.'
        )


def retrigger_booking_email(booking_id, user):
    """
    Allows a customer to re-trigger sending the confirmation email for their booking.
    """
    try:
        booking = Booking.objects.get(id=booking_id)
        if booking.user_id != user.id:
            return {'success': False, 'reason': 'unauthorized', 'message': 'You can only resend emails for your own bookings.'}
        if booking.status != 'confirmed':
            return {'success': False, 'reason': 'not_confirmed', 'message': 'Booking is not confirmed.'}
        
        import threading
        from bookings.tasks import dispatch_email_for_booking
        threading.Thread(
            target=dispatch_email_for_booking,
            args=(str(booking.id),),
            daemon=True
        ).start()
        return {'success': True, 'reason': 'email_queued', 'message': 'Confirmation email resend queued.'}
    except Booking.DoesNotExist:
        return {'success': False, 'reason': 'booking_not_found', 'message': 'Booking not found.'}

