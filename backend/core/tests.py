from django.test import TestCase
from django.urls import reverse
from rest_framework import status

class HealthCheckTests(TestCase):
    def test_health_check_endpoint(self):
        url = reverse('health-check')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['service'], 'ticket-booking-backend')
        self.assertEqual(data['database'], 'healthy')
        self.assertIn('accounts', data['apps'])
        self.assertIn('venues', data['apps'])
        self.assertIn('events', data['apps'])
        self.assertIn('bookings', data['apps'])
        self.assertIn('waitlist', data['apps'])
