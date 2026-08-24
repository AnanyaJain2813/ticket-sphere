"""
events/tests.py — Permission and data-isolation tests for event and revenue endpoints.

Test coverage:
  1. Public endpoints (EventListView, ShowListView) — accessible without auth
  2. EventCreateView — 403 for customers/unauthenticated, 201 for organisers
  3. ShowSeatMapView — 401 without auth token
  4. VenueListView — 403 for organiser/customer, 201 for admin
  5. OrganiserRevenueSummaryView — data isolation: organiser A cannot see organiser B's events
  6. OrganiserRevenueSummaryView — customer gets 403

All tests run against the full in-memory Django test DB with JWT tokens generated
directly from RefreshToken (no HTTP round-trip to /login/).
"""

from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from venues.models import Venue, SeatLayout, SeatCategory, Seat
from events.models import Event, Show
from bookings.models import ShowSeat, Booking

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _token(user):
    """Return a Bearer token string for the given user (no DB hit)."""
    return str(RefreshToken.for_user(user).access_token)


def _auth(client, user):
    """Attach a JWT credential to an APIClient."""
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {_token(user)}')


class PermissionTestBase(TestCase):
    """
    Shared setUp: creates one user of each role and a minimal venue/event/show
    owned by organiser_a.
    """

    def setUp(self):
        self.client = APIClient()

        self.customer = User.objects.create_user(
            username='customer1', email='customer1@test.invalid',
            password='pass1234', role='customer',
        )
        self.organiser_a = User.objects.create_user(
            username='organiser_a', email='organiser_a@test.invalid',
            password='pass1234', role='organiser',
        )
        self.organiser_b = User.objects.create_user(
            username='organiser_b', email='organiser_b@test.invalid',
            password='pass1234', role='organiser',
        )
        self.admin = User.objects.create_user(
            username='admin1', email='admin1@test.invalid',
            password='pass1234', role='admin',
        )

        # Venue owned at platform level (created by admin seeding, no created_by)
        self.venue = Venue.objects.create(
            name='Grand Arena', location='Downtown', total_capacity=100
        )
        self.layout = SeatLayout.objects.create(
            venue=self.venue, name='Main Floor', total_rows=5, total_columns=10
        )
        self.category = SeatCategory.objects.create(name='VIP', base_price=150.00)
        self.seat = Seat.objects.create(
            venue=self.venue, layout=self.layout, category=self.category,
            row_name='A', col_number=1, coord_x=12.5, coord_y=25.0,
        )

        # Event owned by organiser_a
        self.event_a = Event.objects.create(
            title='Organiser A Concert', event_type='concert',
            created_by=self.organiser_a,
        )
        self.show_a = Show.objects.create(
            event=self.event_a, venue=self.venue,
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=3),
        )
        self.show_seat_a = ShowSeat.objects.create(
            show=self.show_a, seat=self.seat, category=self.category,
            price=150.00, status='booked',
        )
        self.booking_a = Booking.objects.create(
            booking_reference='REV-A-001',
            user=self.customer,
            show=self.show_a,
            show_seat=self.show_seat_a,
            amount=150.00,
            status='confirmed',
        )

        # Separate event owned by organiser_b
        self.seat_b = Seat.objects.create(
            venue=self.venue, layout=self.layout, category=self.category,
            row_name='B', col_number=1, coord_x=13.5, coord_y=25.0,
        )
        self.event_b = Event.objects.create(
            title='Organiser B Movie', event_type='movie',
            created_by=self.organiser_b,
        )
        self.show_b = Show.objects.create(
            event=self.event_b, venue=self.venue,
            start_time=timezone.now() + timedelta(days=3),
            end_time=timezone.now() + timedelta(days=3, hours=2),
        )
        self.show_seat_b = ShowSeat.objects.create(
            show=self.show_b, seat=self.seat_b, category=self.category,
            price=200.00, status='booked',
        )
        self.booking_b = Booking.objects.create(
            booking_reference='REV-B-001',
            user=self.customer,
            show=self.show_b,
            show_seat=self.show_seat_b,
            amount=200.00,
            status='confirmed',
        )


# ===========================================================================
# 1. Public endpoints — no auth required
# ===========================================================================

class PublicEndpointTests(PermissionTestBase):
    """EventListView and ShowListView must return 200 without any auth token."""

    def test_event_list_is_public(self):
        self.client.credentials()  # no auth
        response = self.client.get('/api/events/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_show_list_is_public(self):
        self.client.credentials()
        response = self.client.get('/api/shows/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)


# ===========================================================================
# 2. EventCreateView — IsOrganiser
# ===========================================================================

class EventCreatePermissionTests(PermissionTestBase):
    """Only organisers may create events."""

    URL = '/api/events/create/'
    PAYLOAD = {'title': 'New Festival', 'event_type': 'concert'}

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.post(self.URL, self.PAYLOAD, format='json')
        self.assertEqual(response.status_code, 401,
                         f"Expected 401, got {response.status_code}")

    def test_customer_returns_403(self):
        _auth(self.client, self.customer)
        response = self.client.post(self.URL, self.PAYLOAD, format='json')
        self.assertEqual(response.status_code, 403,
                         f"Customer must be denied event creation, got {response.status_code}")

    def test_admin_returns_403(self):
        """Admins manage infrastructure, not events — creating events is organiser-only."""
        _auth(self.client, self.admin)
        response = self.client.post(self.URL, self.PAYLOAD, format='json')
        self.assertEqual(response.status_code, 403,
                         f"Admin must not create events, got {response.status_code}")

    def test_organiser_returns_201_and_sets_created_by(self):
        _auth(self.client, self.organiser_a)
        response = self.client.post(self.URL, self.PAYLOAD, format='json')
        self.assertEqual(response.status_code, 201,
                         f"Organiser should create event, got {response.status_code}: {response.data}")
        # created_by must be set to the JWT user — never from request body
        event = Event.objects.get(id=response.data['id'])
        self.assertEqual(event.created_by_id, self.organiser_a.id,
                         "created_by must be the authenticated organiser, not a body param")


# ===========================================================================
# 3. ShowSeatMapView — IsAuthenticated
# ===========================================================================

class SeatMapAuthTests(PermissionTestBase):
    """Seat map requires an authenticated user (any role)."""

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(f'/api/shows/{self.show_a.id}/seats/')
        self.assertEqual(response.status_code, 401)

    def test_authenticated_customer_returns_200(self):
        _auth(self.client, self.customer)
        response = self.client.get(f'/api/shows/{self.show_a.id}/seats/')
        self.assertEqual(response.status_code, 200)


# ===========================================================================
# 4. Venue management — IsAdmin only
# ===========================================================================

class VenueAdminPermissionTests(PermissionTestBase):
    """Only admins may list or create venues via the admin endpoint."""

    URL = '/api/admin/venues/'

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 401)

    def test_customer_returns_403(self):
        _auth(self.client, self.customer)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 403)

    def test_organiser_returns_403(self):
        _auth(self.client, self.organiser_a)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list_venues(self):
        _auth(self.client, self.admin)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_admin_can_create_venue(self):
        _auth(self.client, self.admin)
        response = self.client.post(self.URL, {
            'name': 'New Venue', 'location': 'Uptown', 'total_capacity': 500
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Venue.objects.filter(name='New Venue').exists())

    def test_organiser_cannot_create_venue(self):
        _auth(self.client, self.organiser_a)
        response = self.client.post(self.URL, {
            'name': 'Sneaky Venue', 'location': 'Nowhere', 'total_capacity': 100
        }, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Venue.objects.filter(name='Sneaky Venue').exists())


# ===========================================================================
# 5. OrganiserRevenueSummaryView — data isolation
# ===========================================================================

class OrganiserRevenueIsolationTests(PermissionTestBase):
    """
    Core business rule: an organiser must NEVER see another organiser's revenue.

    organiser_a owns event_a → booking_a (£150.00)
    organiser_b owns event_b → booking_b (£200.00)

    When organiser_b calls /api/organiser/revenue/, they must see only
    their own £200.00 — not organiser_a's £150.00.
    """

    URL = '/api/organiser/revenue/'

    def test_customer_returns_403(self):
        _auth(self.client, self.customer)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 403,
                         f"Customer must not access revenue, got {response.status_code}")

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 401)

    def test_organiser_a_sees_only_own_revenue(self):
        """organiser_a's £150.00 is visible; organiser_b's £200.00 is not."""
        _auth(self.client, self.organiser_a)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        # Only organiser_a's data is returned
        self.assertEqual(response.data['total_seats'], 1,
                         "organiser_a should see exactly 1 seat (their own show)")
        self.assertEqual(response.data['total_revenue'], '150.00',
                         "organiser_a revenue must only include their own bookings")

    def test_organiser_b_cannot_see_organiser_a_revenue(self):
        """
        organiser_b creates an event.
        organiser_b calls the revenue endpoint.
        They must see ONLY their own £200.00 — organiser_a's £150.00 must not appear.
        """
        _auth(self.client, self.organiser_b)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)

        # organiser_b has 1 seat and £200 revenue
        self.assertEqual(response.data['total_seats'], 1,
                         "organiser_b should see exactly 1 seat (their own show), not organiser_a's")
        self.assertEqual(response.data['total_revenue'], '200.00',
                         "organiser_b revenue must only include their own bookings, not organiser_a's £150")

    def test_organiser_b_show_id_bypass_is_blocked(self):
        """
        Even if organiser_b passes organiser_a's show_id explicitly,
        the ownership scope must prevent them from seeing the data.
        The response must show 0 seats and 0 revenue (not organiser_a's data).
        """
        _auth(self.client, self.organiser_b)
        response = self.client.get(f'{self.URL}?show_id={self.show_a.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_seats'], 0,
                         "organiser_b must not see organiser_a's show via show_id query param bypass")
        self.assertEqual(response.data['total_revenue'], '0.00',
                         "organiser_b must see 0 revenue for a show they do not own")

    def test_admin_sees_all_revenue(self):
        """Admins have a platform-wide view — they see revenue from all organisers combined."""
        _auth(self.client, self.admin)
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        # Admin sees both shows (2 seats total) and both bookings (£350 total)
        self.assertEqual(response.data['total_seats'], 2,
                         "Admin should see all seats across all organisers")
        self.assertEqual(response.data['total_revenue'], '350.00',
                         "Admin revenue must include all organisers' bookings (150 + 200)")


# ===========================================================================
# 6. ShowCreateView — IsOrganiser
# ===========================================================================

class ShowCreateTests(PermissionTestBase):
    """Tests for the show creation endpoint (which auto-generates seats)."""

    URL = '/api/shows/create/'

    def test_organiser_creates_show_generates_seats(self):
        """Organiser creates a show; seats should be auto-generated based on venue layout."""
        _auth(self.client, self.organiser_a)

        payload = {
            'event_id': str(self.event_a.id),
            'venue_id': str(self.venue.id),
            'start_time': (timezone.now() + timedelta(days=10)).isoformat(),
            'end_time': (timezone.now() + timedelta(days=10, hours=2)).isoformat(),
            'pricing': {
                str(self.category.id): 199.99
            }
        }

        response = self.client.post(self.URL, payload, format='json')
        self.assertEqual(response.status_code, 201, f"Failed to create show: {response.data}")
        
        # Venue has exactly 2 seats in the PermissionTestBase setup (self.seat and self.seat_b)
        self.assertEqual(response.data['total_seats_generated'], 2)

        show_id = response.data['id']
        show_seats = ShowSeat.objects.filter(show_id=show_id)
        self.assertEqual(show_seats.count(), 2)
        
        # Verify custom pricing was applied
        for show_seat in show_seats:
            self.assertEqual(float(show_seat.price), 199.99)
            self.assertEqual(show_seat.status, 'available')

    def test_customer_cannot_create_show(self):
        _auth(self.client, self.customer)
        response = self.client.post(self.URL, {}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_organiser_cannot_create_show_for_others_event(self):
        """Organiser B cannot create a show for Event A."""
        _auth(self.client, self.organiser_b)
        payload = {
            'event_id': str(self.event_a.id),
            'venue_id': str(self.venue.id),
            'start_time': (timezone.now() + timedelta(days=10)).isoformat(),
            'end_time': (timezone.now() + timedelta(days=10, hours=2)).isoformat(),
        }
        response = self.client.post(self.URL, payload, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data['message'], 'You can only create shows for events you own.')
