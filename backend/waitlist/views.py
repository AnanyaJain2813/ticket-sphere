from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from waitlist.models import WaitlistEntry
from waitlist.services import cancel_waitlist_entry, join_waitlist


class JoinWaitlistView(APIView):
    """
    POST /api/waitlist/join/

    Adds the authenticated user to the waitlist for a show/category.
    The acting user is derived from the verified JWT (request.user) —
    no user_id is accepted from the request body.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        show_id = request.data.get('show_id')
        category_id = request.data.get('category_id')

        if not show_id or not category_id:
            return Response(
                {'success': False, 'reason': 'missing_params', 'message': 'show_id and category_id are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user  # Always the authenticated user — never from request body
        result = join_waitlist(show_id=show_id, category_id=category_id, user=user)
        return Response(result, status=status.HTTP_200_OK if result['success'] else status.HTTP_400_BAD_REQUEST)


class UserWaitlistView(APIView):
    """
    GET /api/waitlist/

    Returns the authenticated user's waitlist entries.
    No user_id query param — user identity comes from the JWT.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        entries = WaitlistEntry.objects.filter(
            user=request.user
        ).select_related('show', 'show__event', 'category').order_by('-created_at')

        data = [
            {
                'id': str(e.id),
                'show_id': str(e.show_id),
                'event_title': e.show.event.title,
                'category_name': e.category.name,
                'status': e.status,
                'offer_expires_at': e.offer_expires_at.isoformat() if e.offer_expires_at else None,
                'created_at': e.created_at.isoformat(),
            }
            for e in entries
        ]
        return Response(data, status=status.HTTP_200_OK)


class CancelWaitlistView(APIView):
    """
    POST /api/waitlist/<entry_id>/cancel/

    Cancels a waitlist entry. Only the entry owner may cancel their own entry.
    Ownership is verified in the service layer against request.user —
    no user_id is accepted from the request body.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, entry_id):
        user = request.user  # Always the authenticated user — never from request body
        result = cancel_waitlist_entry(entry_id=entry_id, user=user)

        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        elif result.get('reason') == 'unauthorized':
            return Response(result, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(result, status=status.HTTP_409_CONFLICT)
