"""
bookings/tests.py — DB-level constraint tests + 20-thread concurrency test.

The concurrency test uses TransactionTestCase (required for real DB
transactions in threads) and concurrent.futures.ThreadPoolExecutor to
fire 20 simultaneous hold_seat() calls at the exact same ShowSeat row.

Expected result:
  - Exactly 1 thread gets success (reason='held')
  - Exactly 19 threads get failure (reason='already_held')
  - Zero unhandled exceptions or 500-style errors
"""

import concurrent.futures
from datetime import timedelta

from django.test import TestCase, TransactionTestCase, override_settings
from django.db import IntegrityError, transaction, connection
from django.utils import timezone
from django.contrib.auth import get_user_model

from venues.models import Venue, SeatLayout, SeatCategory, Seat
from events.models import Event, Show
from bookings.models import ShowSeat, Booking
from bookings.services import hold_seat

User = get_user_model()


# ======================================================================
# Shared fixture mixin
# ======================================================================

class DBConstraintTestMixin:
    """Creates shared test fixtures for constraint and concurrency tests."""

    def _create_fixtures(self):
        self.user_a = User.objects.create_user(username='alice', email='alice@test.invalid', password='pass1234')
        self.user_b = User.objects.create_user(username='bob', email='bob@test.invalid', password='pass1234')

        self.venue = Venue.objects.create(name='Arena', location='City', total_capacity=100)
        self.layout = SeatLayout.objects.create(
            venue=self.venue, name='Main', total_rows=5, total_columns=10
        )
        self.category = SeatCategory.objects.create(name='VIP', base_price=100.00)
        self.seat = Seat.objects.create(
            venue=self.venue, layout=self.layout, category=self.category,
            row_name='A', col_number=1, coord_x=10.0, coord_y=10.0,
        )
        self.event = Event.objects.create(title='Concert', event_type='concert')
        self.show = Show.objects.create(
            event=self.event, venue=self.venue,
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3),
        )
        self.show_seat = ShowSeat.objects.create(
            show=self.show, seat=self.seat, category=self.category,
            price=100.00, status='available',
        )


# ======================================================================
# 1. DB-Level Constraint Tests (from earlier, kept intact)
# ======================================================================

class HoldExpiresAtConstraintTest(DBConstraintTestMixin, TestCase):
    """Verify the CHECK constraint: hold_expires_at must be NULL unless status='held'."""

    def setUp(self):
        self._create_fixtures()

    def test_available_with_expiry_raises_integrity_error(self):
        self.show_seat.status = 'available'
        self.show_seat.hold_expires_at = timezone.now() + timedelta(minutes=10)
        with self.assertRaises(IntegrityError):
            self.show_seat.save()

    def test_booked_with_expiry_raises_integrity_error(self):
        self.show_seat.status = 'booked'
        self.show_seat.hold_expires_at = timezone.now() + timedelta(minutes=10)
        with self.assertRaises(IntegrityError):
            self.show_seat.save()

    def test_held_with_expiry_succeeds(self):
        self.show_seat.status = 'held'
        self.show_seat.holder = self.user_a
        self.show_seat.hold_expires_at = timezone.now() + timedelta(minutes=10)
        self.show_seat.save()
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'held')

    def test_available_with_null_expiry_succeeds(self):
        self.show_seat.status = 'available'
        self.show_seat.hold_expires_at = None
        self.show_seat.save()
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'available')


class UniqueActiveBookingConstraintTest(DBConstraintTestMixin, TestCase):
    """Verify the conditional UNIQUE constraint on active bookings."""

    def setUp(self):
        self._create_fixtures()
        self.show_seat.status = 'booked'
        self.show_seat.hold_expires_at = None
        self.show_seat.save()

    def test_two_confirmed_bookings_same_seat_raises_integrity_error(self):
        Booking.objects.create(
            booking_reference='BK-001',
            user=self.user_a, show=self.show, show_seat=self.show_seat,
            amount=100.00, status='confirmed',
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Booking.objects.create(
                    booking_reference='BK-002',
                    user=self.user_b, show=self.show, show_seat=self.show_seat,
                    amount=100.00, status='confirmed',
                )

    def test_confirmed_after_cancelled_succeeds(self):
        Booking.objects.create(
            booking_reference='BK-001',
            user=self.user_a, show=self.show, show_seat=self.show_seat,
            amount=100.00, status='cancelled',
        )
        new_booking = Booking.objects.create(
            booking_reference='BK-002',
            user=self.user_b, show=self.show, show_seat=self.show_seat,
            amount=100.00, status='confirmed',
        )
        self.assertEqual(new_booking.status, 'confirmed')

    def test_two_cancelled_bookings_same_seat_succeeds(self):
        Booking.objects.create(
            booking_reference='BK-001',
            user=self.user_a, show=self.show, show_seat=self.show_seat,
            amount=100.00, status='cancelled',
        )
        b2 = Booking.objects.create(
            booking_reference='BK-002',
            user=self.user_b, show=self.show, show_seat=self.show_seat,
            amount=100.00, status='cancelled',
        )
        self.assertEqual(b2.status, 'cancelled')


# ======================================================================
# 2. Seat Hold Service Unit Tests
# ======================================================================

class HoldSeatServiceTest(DBConstraintTestMixin, TestCase):
    """Unit tests for hold_seat() service function."""

    def setUp(self):
        self._create_fixtures()

    def test_hold_available_seat_succeeds(self):
        result = hold_seat(self.show_seat.id, self.user_a)
        self.assertTrue(result.success)
        self.assertEqual(result.reason, 'held')
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'held')
        self.assertEqual(self.show_seat.holder, self.user_a)
        self.assertIsNotNone(self.show_seat.hold_expires_at)

    def test_hold_already_held_by_other_returns_conflict(self):
        hold_seat(self.show_seat.id, self.user_a)
        result = hold_seat(self.show_seat.id, self.user_b)
        self.assertFalse(result.success)
        self.assertEqual(result.reason, 'already_held')

    def test_hold_idempotent_same_user(self):
        """Double-click: same user holds the same seat twice → success, not error."""
        result1 = hold_seat(self.show_seat.id, self.user_a)
        result2 = hold_seat(self.show_seat.id, self.user_a)
        self.assertTrue(result1.success)
        self.assertTrue(result2.success)
        self.assertTrue(result2.is_idempotent)
        self.assertEqual(result2.reason, 'held')

    def test_hold_booked_seat_returns_conflict(self):
        self.show_seat.status = 'booked'
        self.show_seat.hold_expires_at = None
        self.show_seat.save()
        result = hold_seat(self.show_seat.id, self.user_a)
        self.assertFalse(result.success)
        self.assertEqual(result.reason, 'already_booked')

    def test_hold_expired_hold_reclaimed(self):
        """An expired hold should be reclaimable by any user."""
        self.show_seat.status = 'held'
        self.show_seat.holder = self.user_a
        self.show_seat.hold_expires_at = timezone.now() - timedelta(minutes=1)
        self.show_seat.save()

        result = hold_seat(self.show_seat.id, self.user_b)
        self.assertTrue(result.success)
        self.assertEqual(result.reason, 'held')
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.holder, self.user_b)

    def test_hold_nonexistent_seat_returns_not_found(self):
        import uuid
        result = hold_seat(uuid.uuid4(), self.user_a)
        self.assertFalse(result.success)
        self.assertEqual(result.reason, 'seat_not_found')


# ======================================================================
# 3. CONCURRENCY TEST — 20 threads, 1 seat, exactly 1 winner
# ======================================================================

class ConcurrentHoldTest(DBConstraintTestMixin, TransactionTestCase):
    """
    Integration test: 20 threads fire hold_seat() at the exact same
    ShowSeat simultaneously.

    TransactionTestCase is required (not TestCase) because:
      - TestCase wraps each test in a transaction, which means threads
        would share the same transaction and select_for_update() would
        not actually block.
      - TransactionTestCase uses real database commits, so each thread
        gets its own transaction and the row lock works correctly.

    SQLite note: SQLite uses database-level locks (not row-level), so
    concurrent threads will serialize at the database level. The
    django backend has a 20s timeout configured to prevent
    OperationalError. The test still validates the same invariant:
    exactly 1 hold succeeds, 19 fail cleanly.
    """

    def setUp(self):
        self._create_fixtures()

    def test_20_concurrent_holds_exactly_one_wins(self):
        NUM_THREADS = 20
        show_seat_id = self.show_seat.id

        # Create 20 distinct users for the test
        users = []
        for i in range(NUM_THREADS):
            u = User.objects.create_user(username=f'racer_{i}', email=f'racer_{i}@test.invalid', password='pass1234')
            users.append(u)

        def attempt_hold(user):
            """
            Each thread gets its own DB connection in Django.
            We call hold_seat() which internally uses
            transaction.atomic() + select_for_update().
            """
            try:
                result = hold_seat(show_seat_id, user)
                return {
                    'success': result.success,
                    'reason': result.reason,
                    'message': result.message,
                    'user': user.username,
                }
            except Exception as e:
                return {
                    'success': False,
                    'reason': 'exception',
                    'message': str(e),
                    'user': user.username,
                }
            finally:
                connection.close()

        # Fire all 20 threads simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = [executor.submit(attempt_hold, u) for u in users]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Classify results
        successes = [r for r in results if r['success'] is True]
        conflicts = [r for r in results if r['success'] is False and r['reason'] == 'already_held']
        exceptions = [r for r in results if r['reason'] == 'exception']

        # Print results report
        print("\n" + "=" * 64)
        print("  CONCURRENCY TEST RESULTS — 20 THREADS × 1 SEAT")
        print("=" * 64)
        print(f"  Total threads fired          : {len(results)}")
        print(f"  Successful holds (200)       : {len(successes)}")
        print(f"  Clean conflicts (409)        : {len(conflicts)}")
        print(f"  Unhandled exceptions (500)   : {len(exceptions)}")
        if successes:
            print(f"  Winner                       : {successes[0]['user']}")
        if conflicts:
            print(f"  Conflict reasons             : {set(r['reason'] for r in conflicts)}")
        if exceptions:
            print(f"  Exception details            : {[r['message'] for r in exceptions]}")
        print("=" * 64 + "\n")

        # ---------------------------------------------------------------
        # ASSERTIONS
        # ---------------------------------------------------------------
        self.assertEqual(len(results), NUM_THREADS, "All 20 threads must return a result")
        self.assertEqual(len(successes), 1, "Exactly 1 thread must succeed")
        self.assertEqual(len(conflicts), 19, "Exactly 19 threads must get 'already_held'")
        self.assertEqual(len(exceptions), 0, "Zero unhandled exceptions allowed")

        # Verify every conflict has the machine-readable reason
        for conflict in conflicts:
            self.assertEqual(conflict['reason'], 'already_held',
                             "Every failed hold must return reason='already_held'")

        # Verify DB state: seat is held by the winning user
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'held')
        self.assertEqual(self.show_seat.holder.username, successes[0]['user'])
        self.assertIsNotNone(self.show_seat.hold_expires_at)


# ======================================================================
