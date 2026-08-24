from django.contrib import admin
from django.urls import path, include
from core.views import HealthCheckView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', HealthCheckView.as_view(), name='health-check'),
    path('api/', include('accounts.urls')),
    path('api/', include('bookings.urls')),
    path('api/', include('waitlist.urls')),
    path('api/', include('events.urls')),
    path('api/', include('venues.urls')),
]

