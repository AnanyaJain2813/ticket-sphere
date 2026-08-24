from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from bookings.models import Booking, ShowSeat
from bookings.services import hold_seat, confirm_booking, cancel_booking, retrigger_booking_email, release_seat
from accounts.permissions import IsCustomer, IsOrganiserOrAdmin


class SeatHoldView(APIView):
    """
    POST /api/shows/<show_id>/seats/<seat_id>/hold/

    Attempts to atomically hold a seat for the authenticated user.
    Returns 200 on success, 409 on conflict with a machine-readable `reason`.

    The acting user is derived from the verified JWT (request.user).
    No user_id is accepted from the request body — that was the specific
    hole that allowed anyone to act as any user.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, show_id, seat_id):
        user = request.user  # Always the authenticated user — never from request body
        result = hold_seat(show_seat_id=seat_id, user=user)
        if result.success:
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        else:
            return Response(result.to_dict(), status=status.HTTP_409_CONFLICT)

    def delete(self, request, show_id, seat_id):
        user = request.user
        result = release_seat(show_seat_id=seat_id, user=user)
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class ConfirmBookingView(APIView):
    """
    POST /api/shows/<show_id>/seats/<seat_id>/book/

    Attempts to atomically confirm a booking for a seat that is currently held.
    Requires an Idempotency-Key header to prevent duplicate bookings on retries.
    Returns 200 on success, 409 on conflict (e.g., hold expired).

    The acting user is derived from the verified JWT (request.user).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, show_id, seat_id):
        idempotency_key = request.headers.get('Idempotency-Key')

        if not idempotency_key:
            return Response(
                {'success': False, 'reason': 'missing_idempotency_key', 'message': 'Idempotency-Key header is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user  # Always the authenticated user — never from request body

        customer_name = request.data.get('customer_name')
        customer_phone = request.data.get('customer_phone')
        customer_email = request.data.get('customer_email')

        result = confirm_booking(
            show_seat_id=seat_id,
            user=user,
            idempotency_key=idempotency_key,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
        )
        if result.success:
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        else:
            return Response(result.to_dict(), status=status.HTTP_409_CONFLICT)


class CancelBookingView(APIView):
    """
    POST /api/bookings/<booking_id>/cancel/

    Cancels a booking. Only the booking owner may cancel their own booking.
    Attempting to cancel another user's booking returns 403 Forbidden — not
    a successful cancel, and not a silent 404 that leaks existence info.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        user = request.user  # Always the authenticated user — never from request body

        # Ownership check before delegating to the service layer.
        # We surface 403 here (at the view layer) so it is distinct from the
        # service layer's 'unauthorized' reason which maps to 409 in the old code.
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return Response(
                {'success': False, 'reason': 'booking_not_found', 'message': 'Booking not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if booking.user_id != user.id:
            return Response(
                {'success': False, 'reason': 'forbidden', 'message': 'You do not have permission to cancel this booking.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        result = cancel_booking(booking_id=booking_id, user=user)
        if result.success:
            return Response(result.to_dict(), status=status.HTTP_200_OK)
        else:
            return Response(result.to_dict(), status=status.HTTP_409_CONFLICT)


class ResendBookingEmailView(APIView):
    """
    POST /api/bookings/<booking_id>/resend-email/

    Re-triggers sending the confirmation email for a confirmed booking.
    Only the booking owner may request a resend.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        user = request.user  # Always the authenticated user — never from request body
        result = retrigger_booking_email(booking_id=booking_id, user=user)

        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        elif result.get('reason') == 'unauthorized':
            return Response(result, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class UserBookingHistoryView(APIView):
    """
    GET /api/bookings/history/

    Returns the authenticated user's booking history with seat, show,
    and email status details.

    No user_id query param — the user identity comes from the JWT.
    Admins may optionally pass ?user_id= to inspect another user's history.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Admins can inspect any user's history via ?user_id=; everyone else sees only their own.
        target_user_id = request.query_params.get('user_id')
        if target_user_id and request.user.role == 'admin':
            bookings = Booking.objects.filter(user_id=target_user_id)
        else:
            bookings = Booking.objects.filter(user=request.user)

        bookings = bookings.select_related(
            'show', 'show__event', 'show__venue',
            'show_seat', 'show_seat__seat', 'show_seat__category',
        ).order_by('-created_at')

        data = [
            {
                'id': str(b.id),
                'booking_reference': b.booking_reference,
                'show_id': str(b.show_id),
                'event_title': b.show.event.title,
                'event_type': b.show.event.event_type,
                'venue_name': b.show.venue.name,
                'start_time': b.show.start_time.isoformat(),
                'seat': {
                    'row_name': b.show_seat.seat.row_name,
                    'col_number': b.show_seat.seat.col_number,
                    'category_name': b.show_seat.category.name,
                },
                'amount': str(b.amount),
                'status': b.status,
                'email_delivery_failed': b.email_delivery_failed,
                'created_at': b.created_at.isoformat(),
            }
            for b in bookings
        ]
        return Response(data, status=status.HTTP_200_OK)


class OrganiserRevenueSummaryView(APIView):
    """
    GET /api/organiser/revenue/
    GET /api/organiser/revenue/?show_id=<show_id>

    Returns revenue, occupancy rate, and seat distribution statistics.

    Access control:
      - Organisers see ONLY their own events (scoped by Event.created_by == request.user).
        An organiser must never see another organiser's revenue data.
      - Admins see all events (platform-wide view).

    Ownership scoping is applied at the DB query level, not as a post-filter,
    so there is no risk of an organiser leaking data by guessing a show_id.
    """

    permission_classes = [IsOrganiserOrAdmin]

    def get(self, request):
        show_id = request.query_params.get('show_id')
        user = request.user

        # ----------------------------------------------------------------
        # Ownership scoping
        # Admins have a global view. Organisers are scoped to events they own.
        # The filter is applied before any show_id narrowing so an organiser
        # cannot bypass the ownership check by providing a foreign show_id.
        # ----------------------------------------------------------------
        from django.db.models import Q
        if user.role == 'admin':
            show_seats = ShowSeat.objects.all()
            confirmed_bookings = Booking.objects.filter(status='confirmed')
        else:
            # role == 'organiser': scope to events where created_by == user or default system events
            show_seats = ShowSeat.objects.filter(
                Q(show__event__created_by=user) | Q(show__event__created_by__isnull=True)
            )
            confirmed_bookings = Booking.objects.filter(
                status='confirmed'
            ).filter(
                Q(show__event__created_by=user) | Q(show__event__created_by__isnull=True)
            )

        if show_id:
            # Further narrow to a specific show, still bounded by the ownership scope above.
            show_seats = show_seats.filter(show_id=show_id)
            confirmed_bookings = confirmed_bookings.filter(show_id=show_id)

        total_seats = show_seats.count()
        available_seats = show_seats.filter(status='available').count()
        held_seats = show_seats.filter(status='held').count()
        booked_seats = show_seats.filter(status='booked').count()

        total_revenue = confirmed_bookings.aggregate(total=Sum('amount'))['total'] or 0.00
        occupancy_rate = round((booked_seats / total_seats * 100), 2) if total_seats > 0 else 0.00

        data = {
            'total_seats': total_seats,
            'booked_seats': booked_seats,
            'held_seats': held_seats,
            'available_seats': available_seats,
            'total_revenue': f"{float(total_revenue):.2f}",
            'occupancy_rate_percent': occupancy_rate,
        }
        return Response(data, status=status.HTTP_200_OK)
