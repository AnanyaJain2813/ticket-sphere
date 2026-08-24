from django.urls import path
from events.views import EventListView, EventCreateView, ShowListView, ShowCreateView, ShowSeatMapView

urlpatterns = [
    path('events/', EventListView.as_view(), name='event-list'),
    path('events/create/', EventCreateView.as_view(), name='event-create'),
    path('shows/', ShowListView.as_view(), name='show-list'),
    path('shows/create/', ShowCreateView.as_view(), name='show-create'),
    path('shows/<uuid:show_id>/seats/', ShowSeatMapView.as_view(), name='show-seat-map'),
]
