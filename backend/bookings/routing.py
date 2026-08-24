from django.urls import re_path
from bookings.consumers import SeatMapConsumer

websocket_urlpatterns = [
    re_path(r'ws/shows/(?P<show_id>[0-9a-f-]+)/seats/$', SeatMapConsumer.as_asgi()),
]
