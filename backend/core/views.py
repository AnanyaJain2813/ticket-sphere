from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db import connection
from django.utils import timezone
from django.conf import settings

class HealthCheckView(APIView):
    """
    Health check endpoint returning service status, database connectivity, and configured apps.
    Publicly accessible — no authentication required (used by load balancers and monitoring).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        db_status = "healthy"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"

        data = {
            "status": "ok" if "unhealthy" not in db_status else "degraded",
            "service": "ticket-booking-backend",
            "timestamp": timezone.now().isoformat(),
            "database": db_status,
            "database_engine": settings.DATABASES['default']['ENGINE'].split('.')[-1],
            "apps": [
                "accounts",
                "venues",
                "events",
                "bookings",
                "waitlist"
            ]
        }
        
        http_status = status.HTTP_200_OK if "unhealthy" not in db_status else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(data, status=http_status)
