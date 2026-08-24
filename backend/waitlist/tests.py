from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from venues.models import Venue, SeatLayout, SeatCategory, Seat
from events.models import Event, Show
from bookings.models import ShowSeat
from waitlist.models import WaitlistEntry
from waitlist.tasks import expire_waitlist_offers
from waitlist.services import cancel_waitlist_entry

User = get_user_model()

class WaitlistTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username='alice', email='alice@waitlist.invalid', password='pwd')
        self.user_b = User.objects.create_user(username='bob', email='bob@waitlist.invalid', password='pwd')
        self.user_c = User.objects.create_user(username='charlie', email='charlie@waitlist.invalid', password='pwd')

        self.venue = Venue.objects.create(name='Arena', location='City', total_capacity=100)
        self.layout = SeatLayout.objects.create(venue=self.venue, name='Main', total_rows=5, total_columns=10)
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
            price=100.00, status='held', holder=self.user_a,
            hold_expires_at=timezone.now() + timedelta(minutes=10),
            is_waitlist_offer=True
        )
        
        # User A has an offer that has expired
        self.entry_a = WaitlistEntry.objects.create(
            show=self.show, user=self.user_a, category=self.category,
            status='offered', offer_expires_at=timezone.now() - timedelta(minutes=1)
        )
        
        # User B is next in line
        self.entry_b = WaitlistEntry.objects.create(
            show=self.show, user=self.user_b, category=self.category,
            status='waiting'
        )
        
        # User C is after User B
        self.entry_c = WaitlistEntry.objects.create(
            show=self.show, user=self.user_c, category=self.category,
            status='waiting'
        )

    def test_expire_waitlist_offers_chains_correctly(self):
        """
        When User A's offer expires, the seat should be immediately offered to User B.
        """
        processed = expire_waitlist_offers()
        self.assertEqual(processed, 1)
        
        self.entry_a.refresh_from_db()
        self.assertEqual(self.entry_a.status, 'expired')
        
        self.entry_b.refresh_from_db()
        self.assertEqual(self.entry_b.status, 'offered')
        self.assertIsNotNone(self.entry_b.offer_expires_at)
        
        self.entry_c.refresh_from_db()
        self.assertEqual(self.entry_c.status, 'waiting')
        
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'held')
        self.assertEqual(self.show_seat.holder, self.user_b)
        self.assertEqual(self.show_seat.hold_expires_at, self.entry_b.offer_expires_at)
        
        # Now if we expire User B's offer artificially
        self.entry_b.offer_expires_at = timezone.now() - timedelta(minutes=1)
        self.entry_b.save()
        
        processed = expire_waitlist_offers()
        self.assertEqual(processed, 1)
        
        self.entry_b.refresh_from_db()
        self.assertEqual(self.entry_b.status, 'expired')
        
        self.entry_c.refresh_from_db()
        self.assertEqual(self.entry_c.status, 'offered')
        self.assertIsNotNone(self.entry_c.offer_expires_at)

        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'held')
        self.assertEqual(self.show_seat.holder, self.user_c)
        self.assertEqual(self.show_seat.hold_expires_at, self.entry_c.offer_expires_at)

    def test_cancel_waitlist_entry_promotes_next_in_line(self):
        """
        If User A cancels their entry while the offer is pending,
        it should immediately be offered to User B.
        """
        # First fix User A's offer so it's not expired
        self.entry_a.offer_expires_at = timezone.now() + timedelta(minutes=10)
        self.entry_a.save()
        
        result = cancel_waitlist_entry(self.entry_a.id, self.user_a)
        self.assertTrue(result['success'])
        
        self.entry_a.refresh_from_db()
        self.assertEqual(self.entry_a.status, 'expired') # Or cancelled, depending on implementation
        
        self.entry_b.refresh_from_db()
        self.assertEqual(self.entry_b.status, 'offered')
        
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'held')
        self.assertEqual(self.show_seat.holder, self.user_b)


    def test_waitlist_offer_avoids_generic_release_race_condition(self):
        """
        Generic release_expired_holds should ignore waitlist offers, ensuring
        they are only processed by expire_waitlist_offers which promotes the next user.
        """
        from bookings.tasks import release_expired_holds
        
        # User A's offer is expired
        self.show_seat.hold_expires_at = timezone.now() - timedelta(minutes=1)
        self.show_seat.save()
        self.entry_a.offer_expires_at = timezone.now() - timedelta(minutes=1)
        self.entry_a.save()

        # RUN THE GENERIC HOLD CLEANUP FIRST
        # This simulates the generic cleanup racing and firing before waitlist cleanup
        processed = release_expired_holds()
        
        # It should ignore this seat entirely because is_waitlist_offer=True
        self.assertEqual(processed, 0)
        
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'held', "Seat must remain held despite being expired")
        self.assertEqual(self.show_seat.holder, self.user_a)
        
        # NOW RUN THE WAITLIST CLEANUP
        processed_waitlist = expire_waitlist_offers()
        self.assertEqual(processed_waitlist, 1)
        
        # Now it should be correctly promoted to User B
        self.entry_b.refresh_from_db()
        self.assertEqual(self.entry_b.status, 'offered')
        
        self.show_seat.refresh_from_db()
        self.assertEqual(self.show_seat.status, 'held')
        self.assertEqual(self.show_seat.holder, self.user_b)
        self.assertTrue(self.show_seat.is_waitlist_offer)
