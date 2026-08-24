from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from events.models import Event, Show
from venues.models import Venue, Seat
from bookings.models import ShowSeat
from accounts.permissions import IsOrganiser, IsOrganiserOrAdmin


class EventListView(APIView):
    """
    GET /api/events/
    Returns a list of all events. Public — no authentication required.
    Browsing events is intentionally open so unauthenticated users can
    discover what's on before registering.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        events = Event.objects.all().order_by('-created_at')
        data = [
            {
                'id': str(e.id),
                'title': e.title,
                'event_type': e.event_type,
                'description': e.description,
                'banner_url': e.banner_url,
            }
            for e in events
        ]
        return Response(data, status=status.HTTP_200_OK)


class EventCreateView(APIView):
    """
    POST /api/events/create/

    Creates a new Event. Restricted to organisers only.
    The created_by field is automatically set to request.user — an organiser
    cannot create events on behalf of another organiser.
    """

    permission_classes = [IsOrganiser]

    def post(self, request):
        title = request.data.get('title')
        event_type = request.data.get('event_type')
        description = request.data.get('description', '')
        banner_url = request.data.get('banner_url', '')

        if not title or not event_type:
            return Response(
                {'success': False, 'message': 'title and event_type are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_types = [choice[0] for choice in Event.TYPE_CHOICES]
        if event_type not in valid_types:
            return Response(
                {'success': False, 'message': f'event_type must be one of: {valid_types}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event = Event.objects.create(
            title=title,
            event_type=event_type,
            description=description,
            banner_url=banner_url,
            created_by=request.user,  # Always set from JWT — never from request body
        )

        return Response(
            {
                'id': str(event.id),
                'title': event.title,
                'event_type': event.event_type,
                'description': event.description,
                'banner_url': event.banner_url,
                'created_by': event.created_by_id,
            },
            status=status.HTTP_201_CREATED,
        )


class ShowListView(APIView):
    """
    GET /api/shows/
    Returns a list of all shows with venue details and available seat counts.
    Public — same rationale as EventListView.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        from bookings.tasks import cleanup_expired_holds_and_offers
        cleanup_expired_holds_and_offers()
        
        shows = Show.objects.select_related('event', 'venue').annotate(
            total_seats=Count('show_seats'),
            available_seats=Count('show_seats', filter=Q(show_seats__status='available'))
        ).order_by('start_time')

        data = [
            {
                'id': str(s.id),
                'event_id': str(s.event_id),
                'event_title': s.event.title,
                'event_type': s.event.event_type,
                'venue_id': str(s.venue_id),
                'venue_name': s.venue.name,
                'venue_location': s.venue.location,
                'start_time': s.start_time.isoformat(),
                'end_time': s.end_time.isoformat(),
                'total_seats': s.total_seats,
                'available_seats': s.available_seats,
                'banner_url': s.event.banner_url,
            }
            for s in shows
        ]
        return Response(data, status=status.HTTP_200_OK)


class ShowCreateView(APIView):
    """
    POST /api/shows/create/

    Creates a new Show for an Event at a Venue, and automatically generates
    ShowSeat rows for every seat in the venue's layout.
    Restricted to IsOrganiser.
    
    The organiser must own the Event being scheduled.
    """

    permission_classes = [IsOrganiser]

    def post(self, request):
        event_id = request.data.get('event_id')
        venue_id = request.data.get('venue_id')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        pricing = request.data.get('pricing', {})  # dict of category_id -> price

        if not all([event_id, venue_id, start_time, end_time]):
            return Response(
                {'success': False, 'message': 'event_id, venue_id, start_time, and end_time are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            return Response({'success': False, 'message': 'Event not found.'}, status=status.HTTP_404_NOT_FOUND)

        if event.created_by_id != request.user.id:
            return Response(
                {'success': False, 'message': 'You can only create shows for events you own.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            venue = Venue.objects.get(id=venue_id)
        except Venue.DoesNotExist:
            return Response({'success': False, 'message': 'Venue not found.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                show = Show.objects.create(
                    event=event,
                    venue=venue,
                    start_time=start_time,
                    end_time=end_time,
                )

                seats = Seat.objects.filter(venue=venue).select_related('category')
                
                show_seats = []
                for seat in seats:
                    cat_id_str = str(seat.category_id)
                    # Use organiser-provided price if available, else fallback to category base price
                    price = pricing.get(cat_id_str, seat.category.base_price)
                    
                    show_seats.append(ShowSeat(
                        show=show,
                        seat=seat,
                        category=seat.category,
                        price=price,
                        status='available'
                    ))

                ShowSeat.objects.bulk_create(show_seats)
                
        except Exception as e:
            return Response(
                {'success': False, 'message': f'An error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                'id': str(show.id),
                'event_id': str(show.event_id),
                'venue_id': str(show.venue_id),
                'start_time': show.start_time.isoformat() if hasattr(show.start_time, 'isoformat') else show.start_time,
                'end_time': show.end_time.isoformat() if hasattr(show.end_time, 'isoformat') else show.end_time,
                'total_seats_generated': len(show_seats)
            },
            status=status.HTTP_201_CREATED,
        )



class ShowSeatMapView(APIView):
    """
    GET /api/shows/<show_id>/seats/
    Returns the complete seat map for a show, including seat layout x/y coordinates.
    Requires authentication — seat status (held/booked) must not be exposed to
    anonymous scrapers who could abuse the real-time availability data.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, show_id):
        from bookings.tasks import cleanup_expired_holds_and_offers
        cleanup_expired_holds_and_offers()

        seats = ShowSeat.objects.filter(show_id=show_id).select_related(
            'seat', 'category', 'show', 'show__venue'
        )

        if not seats.exists():
            return Response(
                {'error': 'No seats found for this show.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = [
            {
                'id': str(s.id),
                'seat_id': str(s.seat_id),
                'row_name': s.seat.row_name,
                'col_number': s.seat.col_number,
                'coord_x': float(s.seat.coord_x) if s.seat.coord_x is not None else 0.0,
                'coord_y': float(s.seat.coord_y) if s.seat.coord_y is not None else 0.0,
                'category_id': str(s.category_id),
                'category_name': s.category.name,
                'price': str(s.price),
                'status': s.status,
                'is_held_by_me': s.status == 'held' and s.holder_id == request.user.id,
                'hold_expires_at': s.hold_expires_at.isoformat() if s.hold_expires_at else None,
            }
            for s in seats
        ]
        return Response(data, status=status.HTTP_200_OK)
