from datetime import timedelta
from django.db import transaction, OperationalError
from django.utils import timezone
from django.conf import settings
from waitlist.models import WaitlistEntry
from bookings.models import ShowSeat
import logging
import threading

logger = logging.getLogger(__name__)

def promote_waitlist_for_seat(seat):
    """
    Given an available seat, atomically finds the oldest waiting WaitlistEntry
    for the same show and category, and promotes it to 'offered'.
    The seat status is set to 'held' for that user.
    If no waiting entry is found, the seat is marked as 'available'.
    
    Returns the WaitlistEntry if promoted, else None.
    Assumes `seat` is already locked (select_for_update) by the caller,
    or that this is called in a safe transaction context where the seat
    won't be concurrently modified by other bookings.
    """
    ttl_minutes = getattr(settings, 'HOLD_TTL_MINUTES', 10)
    now = timezone.now()

    while True:
        entry_id = WaitlistEntry.objects.filter(
            show_id=seat.show_id,
            category_id=seat.category_id,
            status='waiting'
        ).order_by('created_at').values_list('id', flat=True).first()
        
        if not entry_id:
            # Waitlist is empty -> Seat becomes available normally
            seat.status = 'available'
            seat.holder = None
            seat.hold_expires_at = None
            seat.is_waitlist_offer = False
            seat.save(update_fields=['status', 'holder', 'hold_expires_at', 'is_waitlist_offer'])
            
            from bookings.services import broadcast_seat_updates
            transaction.on_commit(lambda: broadcast_seat_updates(seat.show_id, [{
                'id': str(seat.id),
                'status': 'available',
                'hold_expires_at': None
            }]))
            
            return None
            
        # Try to atomically grab this entry
        offer_expiry = now + timedelta(minutes=ttl_minutes)
        updated = WaitlistEntry.objects.filter(
            id=entry_id, 
            status='waiting'
        ).update(
            status='offered',
            offer_expires_at=offer_expiry
        )
        
        if updated == 1:
            # We successfully grabbed the waitlist entry
            entry = WaitlistEntry.objects.get(id=entry_id)
            seat.status = 'held'
            seat.holder_id = entry.user_id
            seat.hold_expires_at = offer_expiry
            seat.is_waitlist_offer = True
            seat.save(update_fields=['status', 'holder', 'hold_expires_at', 'is_waitlist_offer'])
            
            from bookings.services import broadcast_seat_updates
            from waitlist.tasks import dispatch_waitlist_offer_email
            
            def _on_commit():
                broadcast_seat_updates(seat.show_id, [{
                    'id': str(seat.id),
                    'status': 'held',
                    'hold_expires_at': offer_expiry.isoformat()
                }])
                threading.Thread(
                    target=dispatch_waitlist_offer_email,
                    args=(
                        entry.user.email,
                        f"{seat.seat.row_name}{seat.seat.col_number}",
                        seat.show.event.title,
                        ttl_minutes,
                        seat.show_id
                    ),
                    daemon=True
                ).start()
                
            transaction.on_commit(_on_commit)
            
            logger.info(f"Promoted user {entry.user_id} from waitlist for seat {seat.id}")
            return entry
        # If updated == 0, another concurrent thread grabbed this entry. Loop and try next.

def cancel_waitlist_entry(entry_id, user):
    """
    Cancels a waitlist entry for a user.
    If the entry was currently 'offered', the seat it was holding is freed
    and we immediately run the promotion logic again for the next user in line.
    """
    try:
        with transaction.atomic():
            entry = WaitlistEntry.objects.select_for_update().get(id=entry_id)
            
            if entry.user_id != user.id:
                return {'success': False, 'reason': 'unauthorized', 'message': 'You can only cancel your own waitlist entries.'}
                
            if entry.status == 'expired' or entry.status == 'cancelled':
                # Assuming we might want to add 'cancelled' state, but currently we have 'expired', 'waiting', 'offered'.
                # Let's just set it to 'expired' for now, or we can add 'cancelled' to models.
                # The user asked to "cancel their own waitlist entry", so 'expired' works or 'cancelled' if we add it.
                pass
                
            old_status = entry.status
            entry.status = 'expired' # Using expired as equivalent to cancelled for the entry lifecycle
            entry.offer_expires_at = None
            entry.save(update_fields=['status', 'offer_expires_at'])
            
            # If the user was holding an offer, we must release the seat and offer it to the next person
            if old_status == 'offered':
                # The seat is currently held by this user, and its hold_expires_at matches the offer_expires_at
                seat = ShowSeat.objects.select_for_update().filter(
                    show_id=entry.show_id,
                    category_id=entry.category_id,
                    status='held',
                    holder_id=entry.user_id
                ).first()
                
                if seat:
                    # Seat found, promote next waitlist user
                    promote_waitlist_for_seat(seat)
                    
            return {'success': True, 'reason': 'cancelled', 'message': 'Waitlist entry cancelled successfully.'}
    except WaitlistEntry.DoesNotExist:
        return {'success': False, 'reason': 'not_found', 'message': 'Waitlist entry not found.'}
    except OperationalError:
        return {'success': False, 'reason': 'database_locked', 'message': 'Database busy.'}


def join_waitlist(show_id, category_id, user):
    """
    Allows a user to join the waitlist for a show and seat category.
    Waitlist can ONLY be joined if all seats for that category are sold out / held / booked.
    """
    try:
        with transaction.atomic():
            # Check if there are available seats in this category
            available_count = ShowSeat.objects.filter(
                show_id=show_id,
                category_id=category_id,
                status='available'
            ).count()

            if available_count > 0:
                return {
                    'success': False,
                    'reason': 'seats_available',
                    'message': 'Seats are still available for this class! Please select an available seat from the map above.'
                }

            existing = WaitlistEntry.objects.filter(
                show_id=show_id, category_id=category_id, user=user, status__in=['waiting', 'offered']
            ).first()
            if existing:
                return {'success': True, 'reason': 'already_joined', 'entry_id': str(existing.id), 'status': existing.status}
            
            entry = WaitlistEntry.objects.create(
                show_id=show_id,
                category_id=category_id,
                user=user,
                status='waiting'
            )
            return {'success': True, 'reason': 'joined', 'entry_id': str(entry.id), 'status': 'waiting'}
    except Exception as e:
        return {'success': False, 'reason': 'error', 'message': str(e)}

