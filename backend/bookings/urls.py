from django.urls import path
from bookings.views import (
    SeatHoldView, ConfirmBookingView, CancelBookingView,
    ResendBookingEmailView, UserBookingHistoryView, OrganiserRevenueSummaryView,
    OrganiserBookingsListView
)

urlpatterns = [
    path('shows/<uuid:show_id>/seats/<uuid:seat_id>/hold/', SeatHoldView.as_view(), name='seat-hold'),
    path('shows/<uuid:show_id>/seats/<uuid:seat_id>/book/', ConfirmBookingView.as_view(), name='seat-book'),
    path('bookings/<uuid:booking_id>/cancel/', CancelBookingView.as_view(), name='booking-cancel'),
    path('bookings/<uuid:booking_id>/resend-email/', ResendBookingEmailView.as_view(), name='resend-booking-email'),
    path('bookings/history/', UserBookingHistoryView.as_view(), name='booking-history'),
    path('organiser/revenue/', OrganiserRevenueSummaryView.as_view(), name='organiser-revenue'),
    path('organiser/bookings/', OrganiserBookingsListView.as_view(), name='organiser-bookings'),
]
