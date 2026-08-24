"""
venues/tests.py — Venue and Seat Layout CRUD API tests.

Test coverage:
  1. VenueListView POST (Create Venue + Layout + Seats in one payload)
  2. SeatCategoryDetailView PATCH (Update base_price, name)
  3. SeatCategoryDetailView DELETE (Protected error handling)
  4. Permission boundary checks (IsAdmin enforcement)
"""

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from venues.models import Venue, SeatLayout, SeatCategory, Seat

User = get_user_model()


def _auth(client, user):
    """Attach a JWT credential to an APIClient."""
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


class VenueAdminTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.customer = User.objects.create_user(
            username='customer1', email='customer1@test.invalid',
            password='pass1234', role='customer',
        )
        self.organiser = User.objects.create_user(
            username='organiser1', email='organiser1@test.invalid',
            password='pass1234', role='organiser',
        )
        self.admin = User.objects.create_user(
            username='admin1', email='admin1@test.invalid',
            password='pass1234', role='admin',
        )

        self.category = SeatCategory.objects.create(name='VIP', base_price=100.00)

    def test_non_admin_gets_403(self):
        """Customers and organisers must be blocked from venue and category CRUD."""
        endpoints = [
            ('GET', '/api/admin/venues/'),
            ('POST', '/api/admin/venues/'),
            ('PATCH', f'/api/admin/seat-categories/{self.category.id}/'),
        ]

        _auth(self.client, self.customer)
        for method, url in endpoints:
            response = getattr(self.client, method.lower())(url)
            self.assertEqual(response.status_code, 403)

        _auth(self.client, self.organiser)
        for method, url in endpoints:
            response = getattr(self.client, method.lower())(url)
            self.assertEqual(response.status_code, 403)

    def test_create_venue_with_layout_success(self):
        """Admin can create a venue, layout, and seats in a single atomic request."""
        _auth(self.client, self.admin)
        
        payload = {
            'name': 'New Grand Theater',
            'location': 'Downtown',
            'total_capacity': 500,
            'layout': {
                'name': 'Standard Configuration',
                'total_rows': 2,
                'total_columns': 2,
                'seats': [
                    {'row_name': 'A', 'col_number': 1, 'category_id': str(self.category.id), 'coord_x': 10, 'coord_y': 10},
                    {'row_name': 'A', 'col_number': 2, 'category_id': str(self.category.id), 'coord_x': 20, 'coord_y': 10},
                ]
            }
        }

        response = self.client.post('/api/admin/venues/', payload, format='json')
        self.assertEqual(response.status_code, 201)

        venue = Venue.objects.get(name='New Grand Theater')
        self.assertEqual(venue.total_capacity, 500)

        layout = SeatLayout.objects.get(venue=venue)
        self.assertEqual(layout.name, 'Standard Configuration')
        self.assertEqual(layout.total_rows, 2)

        seats = Seat.objects.filter(layout=layout)
        self.assertEqual(seats.count(), 2)
        self.assertEqual(seats[0].category_id, self.category.id)

    def test_create_venue_missing_category_fails(self):
        """If a seat references a non-existent category, the entire transaction rolls back."""
        _auth(self.client, self.admin)
        
        payload = {
            'name': 'Bad Theater',
            'location': 'Downtown',
            'total_capacity': 500,
            'layout': {
                'total_rows': 1,
                'total_columns': 1,
                'seats': [
                    {'row_name': 'A', 'col_number': 1, 'category_id': '00000000-0000-0000-0000-000000000000'},
                ]
            }
        }

        response = self.client.post('/api/admin/venues/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('does not exist', response.data['message'])

        # Atomic transaction rollback check: Venue should NOT be created
        self.assertFalse(Venue.objects.filter(name='Bad Theater').exists())

    def test_update_seat_category(self):
        """Admin can update a seat category's price and name."""
        _auth(self.client, self.admin)

        payload = {
            'name': 'Super VIP',
            'base_price': '250.00'
        }
        
        response = self.client.patch(f'/api/admin/seat-categories/{self.category.id}/', payload, format='json')
        self.assertEqual(response.status_code, 200)

        self.category.refresh_from_db()
        self.assertEqual(self.category.name, 'Super VIP')
        self.assertEqual(self.category.base_price, 250.00)

    def test_delete_seat_category_protected(self):
        """Cannot delete a category if seats depend on it."""
        _auth(self.client, self.admin)

        venue = Venue.objects.create(name='T', location='L', total_capacity=10)
        layout = SeatLayout.objects.create(venue=venue, name='L', total_rows=1, total_columns=1)
        Seat.objects.create(venue=venue, layout=layout, category=self.category, row_name='A', col_number=1, coord_x=0, coord_y=0)

        response = self.client.delete(f'/api/admin/seat-categories/{self.category.id}/')
        self.assertEqual(response.status_code, 409)
        self.assertIn('assigned to seats', response.data['message'])

        # Should be able to delete a category with no dependencies
        free_cat = SeatCategory.objects.create(name='Free', base_price=0.0)
        response = self.client.delete(f'/api/admin/seat-categories/{free_cat.id}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(SeatCategory.objects.filter(id=free_cat.id).exists())
