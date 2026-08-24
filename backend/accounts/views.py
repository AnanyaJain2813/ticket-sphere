from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()


class RegisterView(APIView):
    """
    POST /api/auth/register/

    Creates a new user account and returns a JWT access/refresh pair.
    Passwords are hashed via Django's built-in PBKDF2-SHA256 hasher —
    plain-text passwords are never persisted.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Issue JWT tokens immediately after registration
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class CustomLoginSerializer(TokenObtainPairSerializer):
    """Extends the default login serializer to include the user's role in the response."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Embed role claim directly into the JWT payload
        token["role"] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Augment the token response with user metadata
        data["role"] = self.user.role
        data["user"] = UserSerializer(self.user).data
        return data


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/

    Accepts { username, password } and returns:
      { access, refresh, role, user }

    Returns 401 if credentials are invalid.
    """

    serializer_class = CustomLoginSerializer


class MeView(APIView):
    """
    GET /api/auth/me/

    Returns the profile of the currently authenticated user.
    Requires a valid JWT Bearer token in the Authorization header.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
