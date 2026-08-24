"""
venues/views.py — Venue management API (admin-only).

Venue creation and management is a platform-level operation that requires the
'admin' role. Organisers and customers cannot create or modify venues —
they can only use venues that already exist when creating shows.
"""

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from accounts.permissions import IsAdmin
from venues.models import Venue, SeatCategory, SeatLayout, Seat


# =========================================================================
# Venue management — IsAdmin only
# =========================================================================

class VenueListView(APIView):
    """
    GET  /api/admin/venues/ — List all venues with layouts and category details.
    POST /api/admin/venues/ — Create a new venue with seat layout and seat grid.

    Restricted to IsAdmin.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        venues = Venue.objects.all().order_by('name')
        data = [
            {
                'id': str(v.id),
                'name': v.name,
                'location': v.location,
                'total_capacity': v.total_capacity,
                'created_at': v.created_at.isoformat(),
            }
            for v in venues
        ]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        if getattr(request.user, "role", None) != "admin":
            return Response({'detail': 'Access restricted to administrators.'}, status=status.HTTP_403_FORBIDDEN)
            
        name = request.data.get('name')
        location = request.data.get('location')
        total_capacity = request.data.get('total_capacity')

        if not name or not location or total_capacity is None:
            return Response(
                {'success': False, 'message': 'name, location, and total_capacity are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            total_capacity = int(total_capacity)
            if total_capacity <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {'success': False, 'message': 'total_capacity must be a positive integer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        layout_data = request.data.get('layout')

        try:
            with transaction.atomic():
                venue = Venue.objects.create(
                    name=name,
                    location=location,
                    total_capacity=total_capacity,
                )

                if layout_data:
                    layout_name = layout_data.get('name', 'Main Layout')
                    total_rows = layout_data.get('total_rows')
                    total_columns = layout_data.get('total_columns')
                    seats_data = layout_data.get('seats', [])

                    if not total_rows or not total_columns:
                        raise ValueError("layout.total_rows and layout.total_columns are required.")
                    
                    try:
                        total_rows = int(total_rows)
                        total_columns = int(total_columns)
                    except ValueError:
                        raise ValueError("layout.total_rows and layout.total_columns must be integers.")

                    layout = SeatLayout.objects.create(
                        venue=venue,
                        name=layout_name,
                        total_rows=total_rows,
                        total_columns=total_columns
                    )

                    # Pre-fetch categories to validate they exist
                    category_ids = {s.get('category_id') for s in seats_data}
                    categories = {str(c.id): c for c in SeatCategory.objects.filter(id__in=category_ids)}

                    seats_to_create = []
                    for s in seats_data:
                        cat_id = s.get('category_id')
                        if cat_id not in categories:
                            raise ValueError(f"SeatCategory {cat_id} does not exist.")
                        
                        row_name = s.get('row_name')
                        col_number = s.get('col_number')
                        
                        if not row_name or col_number is None:
                            raise ValueError("Seat row_name and col_number are required.")

                        seats_to_create.append(Seat(
                            venue=venue,
                            layout=layout,
                            category=categories[cat_id],
                            row_name=row_name,
                            col_number=int(col_number),
                            coord_x=float(s.get('coord_x', 0.0)),
                            coord_y=float(s.get('coord_y', 0.0)),
                        ))

                    # Bulk create seats for performance
                    Seat.objects.bulk_create(seats_to_create)

        except ValueError as e:
            return Response(
                {'success': False, 'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {'success': False, 'message': 'An error occurred during venue creation.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                'id': str(venue.id),
                'name': venue.name,
                'location': venue.location,
                'total_capacity': venue.total_capacity,
            },
            status=status.HTTP_201_CREATED,
        )


class VenueDetailView(APIView):
    """
    GET    /api/admin/venues/<venue_id>/  — retrieve a venue
    PATCH  /api/admin/venues/<venue_id>/  — update a venue
    DELETE /api/admin/venues/<venue_id>/  — delete a venue

    Restricted to role='admin'.
    """

    permission_classes = [IsAdmin]

    def _get_venue(self, venue_id):
        try:
            return Venue.objects.get(id=venue_id)
        except Venue.DoesNotExist:
            return None

    def get(self, request, venue_id):
        venue = self._get_venue(venue_id)
        if not venue:
            return Response({'detail': 'Venue not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                'id': str(venue.id),
                'name': venue.name,
                'location': venue.location,
                'total_capacity': venue.total_capacity,
                'created_at': venue.created_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, venue_id):
        venue = self._get_venue(venue_id)
        if not venue:
            return Response({'detail': 'Venue not found.'}, status=status.HTTP_404_NOT_FOUND)

        if 'name' in request.data:
            venue.name = request.data['name']
        if 'location' in request.data:
            venue.location = request.data['location']
        if 'total_capacity' in request.data:
            try:
                cap = int(request.data['total_capacity'])
                if cap <= 0:
                    raise ValueError
                venue.total_capacity = cap
            except (TypeError, ValueError):
                return Response(
                    {'success': False, 'message': 'total_capacity must be a positive integer.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        venue.save()
        return Response(
            {
                'id': str(venue.id),
                'name': venue.name,
                'location': venue.location,
                'total_capacity': venue.total_capacity,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, venue_id):
        venue = self._get_venue(venue_id)
        if not venue:
            return Response({'detail': 'Venue not found.'}, status=status.HTTP_404_NOT_FOUND)
        venue.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SeatCategoryListView(APIView):
    """
    GET  /api/admin/seat-categories/ — List all categories.
    POST /api/admin/seat-categories/ — Create a new seat category.

    Restricted to IsAdmin.
    """

    permission_classes = [IsAdmin]

    def get(self, request):
        categories = SeatCategory.objects.all()
        data = [
            {
                'id': str(c.id),
                'name': c.name,
                'base_price': str(c.base_price),
                'description': c.description,
            }
            for c in categories
        ]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        if getattr(request.user, "role", None) != "admin":
            return Response({'detail': 'Access restricted to administrators.'}, status=status.HTTP_403_FORBIDDEN)

        name = request.data.get('name')
        base_price = request.data.get('base_price')

        if not name or base_price is None:
            return Response(
                {'success': False, 'message': 'name and base_price are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if SeatCategory.objects.filter(name=name).exists():
            return Response(
                {'success': False, 'message': f'SeatCategory "{name}" already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category = SeatCategory.objects.create(
            name=name,
            base_price=base_price,
            description=request.data.get('description', ''),
        )
        return Response(
            {
                'id': str(category.id),
                'name': category.name,
                'base_price': str(category.base_price),
                'description': category.description,
            },
            status=status.HTTP_201_CREATED,
        )


class SeatCategoryDetailView(APIView):
    """
    PATCH  /api/admin/seat-categories/<uuid:category_id>/  — update a seat category
    DELETE /api/admin/seat-categories/<uuid:category_id>/  — delete a seat category

    Seat categories are platform-level definitions managed by admins.
    """

    permission_classes = [IsAdmin]

    def _get_category(self, category_id):
        try:
            return SeatCategory.objects.get(id=category_id)
        except SeatCategory.DoesNotExist:
            return None

    def patch(self, request, category_id):
        category = self._get_category(category_id)
        if not category:
            return Response({'detail': 'SeatCategory not found.'}, status=status.HTTP_404_NOT_FOUND)

        if 'name' in request.data:
            new_name = request.data['name']
            if SeatCategory.objects.filter(name=new_name).exclude(id=category.id).exists():
                return Response(
                    {'success': False, 'message': f'SeatCategory "{new_name}" already exists.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            category.name = new_name
            
        if 'base_price' in request.data:
            category.base_price = request.data['base_price']
            
        if 'description' in request.data:
            category.description = request.data['description']

        category.save()
        return Response(
            {
                'id': str(category.id),
                'name': category.name,
                'base_price': str(category.base_price),
                'description': category.description,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, category_id):
        from django.db.models import ProtectedError
        category = self._get_category(category_id)
        if not category:
            return Response({'detail': 'SeatCategory not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            category.delete()
        except ProtectedError:
            return Response(
                {'success': False, 'message': 'Cannot delete SeatCategory because it is currently assigned to seats.'},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
