from django.urls import path
from venues.views import VenueListView, VenueDetailView, SeatCategoryListView, SeatCategoryDetailView

urlpatterns = [
    path('admin/venues/', VenueListView.as_view(), name='admin-venue-list'),
    path('admin/venues/<uuid:venue_id>/', VenueDetailView.as_view(), name='admin-venue-detail'),
    path('admin/seat-categories/', SeatCategoryListView.as_view(), name='admin-seat-category-list'),
    path('admin/seat-categories/<uuid:category_id>/', SeatCategoryDetailView.as_view(), name='admin-seat-category-detail'),
]
