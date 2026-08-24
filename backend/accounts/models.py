from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model with a role field.
    Passwords are always hashed — never stored in plain text.
    Django's built-in PBKDF2-SHA256 hasher is used automatically via set_password().
    """

    class Role(models.TextChoices):
        CUSTOMER = "customer", "Customer"
        ORGANISER = "organiser", "Organiser"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        help_text="Designates what this user is allowed to do in the system.",
    )

    # Use email as a unique identifier in addition to username
    email = models.EmailField(unique=True)

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.username} ({self.role})"
