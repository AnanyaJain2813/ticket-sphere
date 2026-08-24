"""
bookings/models.py — ShowSeat and Booking models with DB-level constraints.

==========================================================================
WHY CONSTRAINTS LIVE AT THE DATABASE LEVEL, NOT JUST IN SERIALIZER / APP CODE
==========================================================================

1. RACE CONDITIONS BYPASS APP-LEVEL CHECKS:
   Two concurrent HTTP requests can both execute a serializer's
   `.validate()` at the exact same instant. Both see status='available',
   both pass validation, and both issue an UPDATE or INSERT. Without a
   DB-level constraint the database happily writes both — resulting in
   double-booking or orphaned holds.

   Example race condition with app-only validation:
     t=0ms  Request A: serializer.validate() → status is 'available' ✓
     t=0ms  Request B: serializer.validate() → status is 'available' ✓
     t=1ms  Request A: UPDATE show_seats SET status='held' → succeeds
     t=1ms  Request B: UPDATE show_seats SET status='held' → ALSO succeeds ← BUG

   With a DB-level unique constraint on (show_seat, non-cancelled booking),
   the second INSERT raises IntegrityError, which is caught and returned
   as a clean 409 Conflict.

2. MULTIPLE ENTRY POINTS:
   Data can be written via the Django admin, management commands,
   raw SQL migrations, or a future microservice. Serializer
   validation only guards the DRF endpoint — it is trivially bypassed
   by any other writer. DB constraints guard ALL writes.

3. DEFENSE IN DEPTH:
   App-level validation provides fast, user-friendly error messages.
   DB-level constraints are the last line of defense ensuring data
   integrity even when app code has bugs. Both layers complement
   each other; neither alone is sufficient.
==========================================================================
"""

import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from events.models import Show
from venues.models import Seat, SeatCategory

User = get_user_model()


class ShowSeat(models.Model):
    """
    Per-show seat status tracker.

    Each row represents a specific seat for a specific show.
    The `status` field tracks the seat lifecycle:
      available → held → booked
                  held → available  (on expiry or manual release)
    """
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('held', 'Held'),
        ('booked', 'Booked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='show_seats')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='show_seats')
    category = models.ForeignKey(SeatCategory, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    holder = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='held_seats',
        help_text="The user currently holding this seat (null if available or booked)."
    )
    hold_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the hold auto-expires. Must be NULL unless status='held'."
    )
    is_waitlist_offer = models.BooleanField(
        default=False,
        help_text="True if this seat is currently held as a waitlist offer. Ignored by generic release_expired_holds task."
    )

    class Meta:
        db_table = 'show_seats'

        # ------------------------------------------------------------------
        # DB-LEVEL CONSTRAINT 1: One seat per show
        # ------------------------------------------------------------------
        # Prevents the same physical seat from being listed twice for
        # the same show. Without this, a bug in seed data or admin
        # could create duplicate ShowSeat rows, causing double-sells.
        # ------------------------------------------------------------------
        unique_together = [('show', 'seat')]

        # ------------------------------------------------------------------
        # DB-LEVEL CONSTRAINT 2: hold_expires_at consistency
        # ------------------------------------------------------------------
        # Ensures hold_expires_at is NULL when status is NOT 'held'.
        # This prevents stale expiry timestamps from persisting after
        # a seat transitions to 'available' or 'booked', which could
        # cause the TTL cleanup worker to incorrectly release a
        # legitimately booked seat.
        #
        # NOTE: Django translates CheckConstraint into a real SQL
        # CHECK constraint in the migration. This is enforced by
        # the database engine on EVERY write (INSERT, UPDATE),
        # regardless of whether the write came from Django ORM,
        # raw SQL, admin, or a management command. App-level clean()
        # validation alone cannot provide this guarantee.
        # ------------------------------------------------------------------
        constraints = [
            models.CheckConstraint(
                name='hold_expires_at_only_when_held',
                check=(
                    models.Q(status='held')  # status IS held → expiry can be anything
                    | models.Q(hold_expires_at__isnull=True)  # status is NOT held → expiry MUST be null
                ),
            ),
        ]

        indexes = [
            models.Index(fields=['status', 'hold_expires_at'], name='idx_showseat_status_expiry'),
            models.Index(fields=['show', 'status'], name='idx_showseat_show_status'),
        ]

    def clean(self):
        """
        App-level validation (provides user-friendly error messages).

        This is a COMPLEMENT to the DB-level CheckConstraint, not a
        replacement. clean() only runs when explicitly called (e.g.,
        full_clean(), ModelForm, DRF serializer). Direct ORM .save()
        or .update() bypasses clean(). The DB constraint catches those.
        """
        super().clean()
        if self.status != 'held' and self.hold_expires_at is not None:
            raise ValidationError({
                'hold_expires_at': (
                    'hold_expires_at must be NULL when status is not "held". '
                    'Found status=%r with hold_expires_at=%r.'
                    % (self.status, self.hold_expires_at)
                )
            })
        if self.status == 'held' and self.hold_expires_at is None:
            raise ValidationError({
                'hold_expires_at': 'hold_expires_at is required when status is "held".'
            })

    def __str__(self):
        return f"ShowSeat {self.seat.row_name}{self.seat.col_number} [{self.status}]"


class Booking(models.Model):
    """
    A confirmed ticket booking linking a user to a ShowSeat.

    DB-level constraints prevent two non-cancelled bookings from
    referencing the same ShowSeat. See Meta.constraints below.
    """
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking_reference = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='bookings')
    show_seat = models.ForeignKey(ShowSeat, on_delete=models.CASCADE, related_name='bookings')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    email_delivery_failed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'bookings'

        # ------------------------------------------------------------------
        # DB-LEVEL CONSTRAINT 3: No duplicate active bookings per seat
        # ------------------------------------------------------------------
        # This prevents the catastrophic scenario where two users both
        # end up with a confirmed booking for the same ShowSeat.
        #
        # WHY NOT JUST A UNIQUE ON (show_seat)?
        # Because a cancelled booking should not block a new booking
        # for the same seat. We need a "conditional unique" — unique
        # only among non-cancelled rows.
        #
        # IMPLEMENTATION:
        # Django's UniqueConstraint with `condition` generates a
        # PARTIAL UNIQUE INDEX (PostgreSQL) or a filtered unique index.
        # On MySQL/SQLite, Django emulates this using a unique index
        # on a computed expression. In either case, the constraint is
        # enforced by the DATABASE ENGINE on every INSERT/UPDATE.
        #
        # Without this DB constraint, the following race is possible:
        #   t=0ms  Thread A: SELECT count(*) WHERE show_seat=X AND status='confirmed' → 0
        #   t=0ms  Thread B: SELECT count(*) WHERE show_seat=X AND status='confirmed' → 0
        #   t=1ms  Thread A: INSERT booking(show_seat=X, status='confirmed') → OK
        #   t=1ms  Thread B: INSERT booking(show_seat=X, status='confirmed') → ALSO OK ← DOUBLE BOOKING
        #
        # With the DB constraint, Thread B's INSERT raises IntegrityError.
        # ------------------------------------------------------------------
        constraints = [
            models.UniqueConstraint(
                fields=['show_seat'],
                condition=models.Q(status='confirmed'),
                name='unique_active_booking_per_show_seat',
            ),
        ]

    def __str__(self):
        return f"Booking {self.booking_reference} [{self.status}]"
