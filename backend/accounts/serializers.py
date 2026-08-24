from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Accepts password in write-only mode and hashes it via set_password().
    Plain-text passwords are NEVER persisted to the database.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={"input_type": "password"},
        help_text="Minimum 8 characters.",
    )

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "role")
        read_only_fields = ("id",)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        # set_password hashes via Django's PBKDF2-SHA256 hasher — never plain-text
        user.set_password(password)
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    """Read-only serializer for the currently authenticated user."""

    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "date_joined", "first_name", "last_name")
        read_only_fields = fields


class CustomTokenObtainPairSerializer(serializers.Serializer):
    """
    Thin wrapper — we rely on SimpleJWT's TokenObtainPairSerializer internally
    but surface it here so custom fields (role) can be injected into the response.
    """

    username = serializers.CharField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
