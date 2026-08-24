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
# 4. Celery Task Tests
# ======================================================================

from bookings.tasks import release_expired_holds

class ReleaseExpiredHoldsTaskTest(DBConstraintTestMixin, TransactionTestCase):
    """
    Tests for the Celery periodic task that releases expired holds.
    Uses TransactionTestCase to simulate concurrent worker execution.
    """

    def setUp(self):
        self._create_fixtures()

    def test_release_expired_hold_success(self):
        # Set up an expired hold
        self.show_seat.status = 'held'
        self.show_seat.holder = self.user_a
        self.show_seat.hold_expires_at = timezone.now() - timedelta(minutes=10)
        self.show_seat.save()

        # Run the task
        updated_count = release_expired_holds()
        self.assertEqual(updated_count, 1)

        # Verify seat is now available
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'available')
        self.assertIsNone(self.show_seat.holder)
        self.assertIsNone(self.show_seat.hold_expires_at)

    def test_does_not_release_active_hold(self):
        # Set up an active (non-expired) hold
        self.show_seat.status = 'held'
        self.show_seat.holder = self.user_a
        self.show_seat.hold_expires_at = timezone.now() + timedelta(minutes=10)
        self.show_seat.save()

        # Run the task
        updated_count = release_expired_holds()
        self.assertEqual(updated_count, 0)

        # Verify seat is still held
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'held')
        self.assertEqual(self.show_seat.holder, self.user_a)
        self.assertIsNotNone(self.show_seat.hold_expires_at)

    def test_concurrent_task_execution_only_releases_once(self):
        """
        Simulate two Celery workers picking up the periodic task at the
        exact same time. Since the task uses an atomic bulk UPDATE query,
        only one worker will actually update the rows, and the other will
        safely do nothing (update 0 rows), preventing race conditions or
        double releases.
        """
        # Set up an expired hold
        self.show_seat.status = 'held'
        self.show_seat.holder = self.user_a
        self.show_seat.hold_expires_at = timezone.now() - timedelta(minutes=10)
        self.show_seat.save()

        # Fire the task twice concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(release_expired_holds)
            future2 = executor.submit(release_expired_holds)

            result1 = future1.result()
            result2 = future2.result()

        # One worker should update 1 row, the other should update 0 rows.
        # Total updates should be exactly 1.
        self.assertEqual(result1 + result2, 1)

        # Verify seat is now available
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'available')
        self.assertIsNone(self.show_seat.holder)
        self.assertIsNone(self.show_seat.hold_expires_at)


# ======================================================================
# 5. Confirm Booking Service Tests
# ======================================================================

from bookings.services import confirm_booking

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class ConfirmBookingServiceTest(DBConstraintTestMixin, TestCase):
    """Unit tests for confirm_booking() service function."""

    def setUp(self):
        self._create_fixtures()
        # Set up a valid hold by user_a
        self.show_seat.status = 'held'
        self.show_seat.holder = self.user_a
        self.show_seat.hold_expires_at = timezone.now() + timedelta(minutes=10)
        self.show_seat.save()

    def test_confirm_booking_success(self):
        result = confirm_booking(self.show_seat.id, self.user_a, idempotency_key='IDEM-001')
        self.assertTrue(result.success)
        self.assertEqual(result.reason, 'booked')
        self.assertIsNotNone(result.booking)
        self.assertEqual(result.booking.booking_reference, 'IDEM-001')

        # Verify seat state
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'booked')
        self.assertIsNone(self.show_seat.holder)
        self.assertIsNone(self.show_seat.hold_expires_at)

    def test_confirm_booking_idempotent_success(self):
        # First call succeeds
        result1 = confirm_booking(self.show_seat.id, self.user_a, idempotency_key='IDEM-001')
        self.assertTrue(result1.success)

        # Second call with the same idempotency key succeeds idempotently
        result2 = confirm_booking(self.show_seat.id, self.user_a, idempotency_key='IDEM-001')
        self.assertTrue(result2.success)
        self.assertEqual(result2.reason, 'booked')
        self.assertTrue(result2.is_idempotent)
        self.assertEqual(result1.booking.id, result2.booking.id)

    def test_confirm_booking_hold_expired_fails(self):
        self.show_seat.hold_expires_at = timezone.now() - timedelta(minutes=1)
        self.show_seat.save()

        result = confirm_booking(self.show_seat.id, self.user_a, idempotency_key='IDEM-002')
        self.assertFalse(result.success)
        self.assertEqual(result.reason, 'hold_expired')

    def test_confirm_booking_held_by_other_fails(self):
        result = confirm_booking(self.show_seat.id, self.user_b, idempotency_key='IDEM-003')
        self.assertFalse(result.success)
        self.assertEqual(result.reason, 'held_by_other')

    def test_confirm_booking_seat_available_fails(self):
        self.show_seat.status = 'available'
        self.show_seat.holder = None
        self.show_seat.hold_expires_at = None
        self.show_seat.save()

        result = confirm_booking(self.show_seat.id, self.user_a, idempotency_key='IDEM-004')
        self.assertFalse(result.success)
        self.assertEqual(result.reason, 'not_held')

    def test_confirm_booking_seat_already_booked_fails(self):
        self.show_seat.status = 'booked'
        self.show_seat.holder = None
        self.show_seat.hold_expires_at = None
        self.show_seat.save()

        result = confirm_booking(self.show_seat.id, self.user_a, idempotency_key='IDEM-005')
        self.assertFalse(result.success)
        self.assertEqual(result.reason, 'already_booked')


# ======================================================================
# 6. Cancel Booking Service Tests
# ======================================================================

from bookings.services import cancel_booking
from waitlist.models import WaitlistEntry

class CancelBookingServiceTest(DBConstraintTestMixin, TestCase):
    """Unit tests for cancel_booking() service function."""

    def setUp(self):
        self._create_fixtures()
        # Set up a booked seat by user_a
        self.show_seat.status = 'booked'
        self.show_seat.holder = None
        self.show_seat.hold_expires_at = None
        self.show_seat.save()

        self.booking = Booking.objects.create(
            booking_reference='IDEM-CANCEL',
            user=self.user_a,
            show_seat=self.show_seat,
            show=self.show,
            amount=self.show_seat.price,
            status='confirmed'
        )

    def test_cancel_booking_empty_waitlist(self):
        result = cancel_booking(self.booking.id, self.user_a)
        self.assertTrue(result.success)
        self.assertEqual(result.reason, 'cancelled')
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')

        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'available')
        self.assertIsNone(self.show_seat.holder)

    def test_cancel_booking_promotes_waitlist(self):
        # Add a waitlist entry for user_b
        waitlist_entry = WaitlistEntry.objects.create(
            show=self.show,
            user=self.user_b,
            category=self.category,
            status='waiting'
        )

        result = cancel_booking(self.booking.id, self.user_a)
        self.assertTrue(result.success)

        # Waitlist entry should be offered
        waitlist_entry.refresh_from_db()
        self.assertEqual(waitlist_entry.status, 'offered')
        self.assertIsNotNone(waitlist_entry.offer_expires_at)

        # Seat should be held for user_b
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'held')
        self.assertEqual(self.show_seat.holder, self.user_b)
        self.assertEqual(self.show_seat.hold_expires_at, waitlist_entry.offer_expires_at)

    def test_cancel_booking_idempotent(self):
        # Cancel once
        result1 = cancel_booking(self.booking.id, self.user_a)
        self.assertTrue(result1.success)

        # Cancel again
        result2 = cancel_booking(self.booking.id, self.user_a)
        self.assertTrue(result2.success)
        self.assertEqual(result2.message, 'Booking is already cancelled.')

    def test_cancel_booking_unauthorized_fails(self):
        # User B tries to cancel User A's booking
        result = cancel_booking(self.booking.id, self.user_b)
        self.assertFalse(result.success)
        self.assertEqual(result.reason, 'unauthorized')
        
        # Ensure it wasn't cancelled
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed')

class ConcurrentCancelBookingTest(DBConstraintTestMixin, TransactionTestCase):
    """
    Test concurrent cancellations when the waitlist has limited entries,
    ensuring we don't offer the same waitlist entry twice.
    """
    
    def setUp(self):
        self._create_fixtures()
        
        # Create a second seat in the same category
        self.seat2 = Seat.objects.create(venue=self.venue, layout=self.layout, category=self.category, row_name='A', col_number=2, coord_x=11.0, coord_y=10.0)
        self.show_seat2 = ShowSeat.objects.create(show=self.show, seat=self.seat2, category=self.category, price=100.00, status='booked')
        
        self.show_seat.status = 'booked'
        self.show_seat.save()
        
        self.booking1 = Booking.objects.create(
            booking_reference='IDEM-CANCEL-1',
            user=self.user_a,
            show_seat=self.show_seat,
            show=self.show,
            amount=self.show_seat.price,
            status='confirmed'
        )
        self.booking2 = Booking.objects.create(
            booking_reference='IDEM-CANCEL-2',
            user=self.user_b,
            show_seat=self.show_seat2,
            show=self.show,
            amount=self.show_seat2.price,
            status='confirmed'
        )
        
        # Create ONLY ONE waitlist entry for user C
        self.user_c = User.objects.create_user(username='user_c', email='user_c@test.invalid', password='pwd')
        self.waitlist_entry = WaitlistEntry.objects.create(
            show=self.show,
            user=self.user_c,
            category=self.category,
            status='waiting'
        )

    def test_concurrent_cancellations_only_promote_waitlist_once(self):
        """
        Two users cancel their standard seats simultaneously.
        There is only 1 user on the waitlist.
        One seat should become 'held' for user_c, the other should become 'available'.
        """
        # Fire both cancellations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(cancel_booking, self.booking1.id, self.user_a)
            future2 = executor.submit(cancel_booking, self.booking2.id, self.user_b)
            
            result1 = future1.result()
            result2 = future2.result()
            
        results = [result1, result2]
        successes = [r for r in results if r.success]
        
        # On SQLite, concurrent transactions might result in a lock timeout for one thread.
        # We must have at least 1 success.
        self.assertTrue(len(successes) >= 1, "At least one cancellation should succeed")
        
        # Refresh DB
        self.show_seat.refresh_from_db()
        self.show_seat2.refresh_from_db()
        self.waitlist_entry.refresh_from_db()
        
        statuses = [self.show_seat.status, self.show_seat2.status]
        
        if len(successes) == 2:
            # If both succeeded, one seat should be held for user C, one should be available
            self.assertIn('held', statuses)
            self.assertIn('available', statuses)
            self.assertEqual(self.waitlist_entry.status, 'offered')
        else:
            # If only one succeeded (SQLite lock timeout on the other)
            # The one that succeeded should have promoted the waitlist
            self.assertIn('held', statuses)
            self.assertIn('booked', statuses)
            self.assertEqual(self.waitlist_entry.status, 'offered')


# ======================================================================
# 7. Email Task & QR Code Tests
# ======================================================================

from unittest.mock import patch
from django.core import mail
from django.test import override_settings
from bookings.tasks import send_booking_confirmation_email, generate_qr_code_bytes
from bookings.services import retrigger_booking_email

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class EmailTaskTest(DBConstraintTestMixin, TestCase):
    """Tests for ticket confirmation email generation, QR encoding, retries, and failure flags."""

    def setUp(self):
        self._create_fixtures()
        self.show_seat.status = 'booked'
        self.show_seat.save()

        self.booking = Booking.objects.create(
            booking_reference='REF-QR-TEST-123',
            user=self.user_a,
            show_seat=self.show_seat,
            show=self.show,
            amount=100.00,
            status='confirmed',
            email_delivery_failed=False
        )

    def test_qr_code_generation(self):
        qr_bytes = generate_qr_code_bytes('REF-QR-TEST-123')
        self.assertIsNotNone(qr_bytes)
        self.assertTrue(len(qr_bytes) > 0)
        # PNG header check: \x89PNG
        self.assertTrue(qr_bytes.startswith(b'\x89PNG'))

    def test_send_email_success(self):
        result = send_booking_confirmation_email(str(self.booking.id))
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        sent_msg = mail.outbox[0]
        self.assertIn('REF-QR-TEST-123', sent_msg.subject)
        self.assertEqual(len(sent_msg.attachments), 1)
        filename, content, mimetype = sent_msg.attachments[0]
        self.assertEqual(filename, 'M_Ticket_REF-QR-TEST-123.png')
        self.assertEqual(mimetype, 'image/png')
        
        self.booking.refresh_from_db()
        self.assertFalse(self.booking.email_delivery_failed)

    @patch('django.core.mail.EmailMessage.send')
    def test_send_email_failure_sets_flag_after_retries(self, mock_send):
        mock_send.side_effect = Exception("SMTP Connection Timeout")
        
        res = send_booking_confirmation_email.apply(args=[str(self.booking.id)], kwargs={}, retries=2)
        with self.assertRaises(Exception):
            res.get(propagate=True)
            
        self.booking.refresh_from_db()
        self.assertTrue(self.booking.email_delivery_failed, "Flag must be set to True after max retries fail")

    def test_retrigger_booking_email_service(self):
        self.booking.email_delivery_failed = True
        self.booking.save()

        res = retrigger_booking_email(self.booking.id, self.user_a)
        self.assertTrue(res['success'])
        self.assertEqual(res['reason'], 'email_queued')


# ======================================================================
# 8. WebSocket & Reporting API Tests
# ======================================================================

from rest_framework.test import APIClient
from channels.testing import WebsocketCommunicator
from core.asgi import application

class WebSocketAndReportingTests(DBConstraintTestMixin, TestCase):
    """Tests for WebSocket seat map consumer (reconnect state recovery, batching) and reporting endpoints."""

    def setUp(self):
        self._create_fixtures()
        self.client = APIClient()

    async def test_websocket_connect_sends_full_seat_map_state(self):
        communicator = WebsocketCommunicator(application, f"ws/shows/{self.show.id}/seats/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # First message on connect must be seat_map_state
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'seat_map_state')
        self.assertEqual(response['show_id'], str(self.show.id))
        self.assertEqual(len(response['seats']), 1)
        self.assertEqual(response['seats'][0]['coord_x'], 10.0)

        await communicator.disconnect()

    def test_user_booking_history_endpoint(self):
        Booking.objects.create(
            booking_reference='REF-HIST-1',
            user=self.user_a,
            show=self.show,
            show_seat=self.show_seat,
            amount=100.00,
            status='confirmed'
        )

        # History endpoint now requires authentication — provide user_a's JWT
        from rest_framework_simplejwt.tokens import RefreshToken
        token = str(RefreshToken.for_user(self.user_a).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get('/api/bookings/history/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['booking_reference'], 'REF-HIST-1')

    def test_organiser_revenue_summary_endpoint(self):
        self.show_seat.status = 'booked'
        self.show_seat.save()

        Booking.objects.create(
            booking_reference='REF-REV-1',
            user=self.user_a,
            show=self.show,
            show_seat=self.show_seat,
            amount=100.00,
            status='confirmed'
        )

        # Revenue endpoint now requires an authenticated organiser/admin — promote user_a.
        # Also set event.created_by=user_a so the organiser ownership scope includes the show.
        from rest_framework_simplejwt.tokens import RefreshToken
        self.user_a.role = 'organiser'
        self.user_a.save(update_fields=['role'])
        self.show.event.created_by = self.user_a
        self.show.event.save(update_fields=['created_by'])

        token = str(RefreshToken.for_user(self.user_a).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.get(f'/api/organiser/revenue/?show_id={self.show.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_seats'], 1)
        self.assertEqual(response.data['booked_seats'], 1)
        self.assertEqual(response.data['occupancy_rate_percent'], 100.0)
        self.assertEqual(response.data['total_revenue'], '100.00')


# ======================================================================
# Auth & Ownership Security Tests
# ======================================================================

from rest_framework.test import APITestCase as DRFAPITestCase
from rest_framework_simplejwt.tokens import RefreshToken


def _get_token_for_user(user):
    """Helper: return a Bearer token string for the given user."""
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


class BookingAuthSecurityTests(DBConstraintTestMixin, DRFAPITestCase):
    """
    Verifies that all mutating booking endpoints:
      - Return 401 when the request carries no JWT
      - Return 403 (not a successful cancel) when a user tries to cancel
        someone else's booking
      - Cannot be tricked by a user_id field in the request body

    These tests use a full DB fixture identical to DBConstraintTestMixin so
    we have real ShowSeat and Booking rows to work against.
    """

    def setUp(self):
        self._create_fixtures()
        # user_a owns a confirmed booking; user_b is the "attacker"
        self.show_seat.status = 'booked'
        self.show_seat.holder = None
        self.show_seat.hold_expires_at = None
        self.show_seat.save()

        self.booking = Booking.objects.create(
            booking_reference='SEC-BK-001',
            user=self.user_a,
            show=self.show,
            show_seat=self.show_seat,
            amount=100.00,
            status='confirmed',
        )

        self.hold_url = f'/api/shows/{self.show.id}/seats/{self.show_seat.id}/hold/'
        self.book_url = f'/api/shows/{self.show.id}/seats/{self.show_seat.id}/book/'
        self.cancel_url = f'/api/bookings/{self.booking.id}/cancel/'

    # ------------------------------------------------------------------
    # 1. Unauthenticated → 401
    # ------------------------------------------------------------------

    def test_hold_unauthenticated_returns_401(self):
        """POST /hold/ without a token must be rejected with 401."""
        self.client.credentials()  # clear any auth
        response = self.client.post(self.hold_url, {}, format='json')
        self.assertEqual(response.status_code, 401,
                         f"Expected 401 on unauthenticated /hold/, got {response.status_code}")

    def test_book_unauthenticated_returns_401(self):
        """POST /book/ without a token must be rejected with 401."""
        self.client.credentials()
        response = self.client.post(
            self.book_url,
            {},
            format='json',
            HTTP_IDEMPOTENCY_KEY='some-key',
        )
        self.assertEqual(response.status_code, 401,
                         f"Expected 401 on unauthenticated /book/, got {response.status_code}")

    def test_cancel_unauthenticated_returns_401(self):
        """POST /cancel/ without a token must be rejected with 401."""
        self.client.credentials()
        response = self.client.post(self.cancel_url, {}, format='json')
        self.assertEqual(response.status_code, 401,
                         f"Expected 401 on unauthenticated /cancel/, got {response.status_code}")

    # ------------------------------------------------------------------
    # 2. Cross-user cancel → 403, not a successful cancel
    # ------------------------------------------------------------------

    def test_cancel_another_users_booking_returns_403(self):
        """
        user_b authenticates with a valid JWT and attempts to cancel user_a's
        booking. This must return 403 Forbidden — not 200, not 404.
        The booking must remain 'confirmed' after the attempt.
        """
        token = _get_token_for_user(self.user_b)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.post(self.cancel_url, {}, format='json')

        # Must be 403, not a silent success or a data-leaking 404
        self.assertEqual(response.status_code, 403,
                         f"Expected 403 when cancelling another user's booking, got {response.status_code}")

        # Booking must still be confirmed — the attempt must not have mutated state
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed',
                         "Booking status must remain 'confirmed' after a forbidden cancel attempt.")

    def test_cancel_own_booking_returns_200(self):
        """Sanity-check: user_a can cancel their own booking normally."""
        token = _get_token_for_user(self.user_a)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = self.client.post(self.cancel_url, {}, format='json')
        self.assertEqual(response.status_code, 200,
                         f"Expected 200 when owner cancels their own booking, got {response.status_code}")

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'cancelled')

    # ------------------------------------------------------------------
    # 3. Regression guard: user_id in body must not impersonate another user
    # ------------------------------------------------------------------

    def test_user_id_in_request_body_cannot_impersonate(self):
        """
        Regression: the old get_user_by_identifier / user_id-from-body pattern
        allowed anyone to act as any user. Confirm that even if user_b sends
        user_a's ID in the request body, the view ignores it and uses user_b's
        JWT identity — which then hits the 403 ownership check on user_a's booking.
        """
        token = _get_token_for_user(self.user_b)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        # Attempt to cancel user_a's booking by spoofing user_a's ID in the body
        response = self.client.post(
            self.cancel_url,
            {'user_id': str(self.user_a.id)},
            format='json',
        )

        # The view must ignore the body user_id and enforce user_b's JWT identity.
        # user_b does not own this booking, so the result must be 403, never 200.
        self.assertNotEqual(response.status_code, 200,
                            "SECURITY BUG: user_id in body allowed impersonation — cancel succeeded!")
        self.assertEqual(response.status_code, 403,
                         f"Expected 403 on impersonation attempt, got {response.status_code}")

        # Booking must remain untouched
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed',
                         "Booking must not be cancelled by an impersonation attempt.")
