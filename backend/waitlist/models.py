"""
waitlist/models.py — WaitlistEntry model.

When all seats in a category for a show are held or booked,
users can join a waitlist. When a hold expires or a booking
is cancelled, the system promotes the oldest waitlist entry.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model
from events.models import Show
from venues.models import SeatCategory

User = get_user_model()


class WaitlistEntry(models.Model):
    """
    A user's position in the waitlist for a specific show + seat category.
    """
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('offered', 'Offered'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='waitlist_entries')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waitlist_entries')
    category = models.ForeignKey(SeatCategory, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    offer_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the offer to book this seat expires. Must be NULL unless status='offered'."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'waitlist_entries'
        verbose_name_plural = 'waitlist entries'

        # ------------------------------------------------------------------
        # DB-LEVEL CONSTRAINT: One active waitlist entry per user per
        # show + category. Prevents a user from accidentally queuing
        # twice for the same seat tier.
        # ------------------------------------------------------------------
        constraints = [
            models.UniqueConstraint(
                fields=['show', 'user', 'category'],
                condition=models.Q(status='waiting'),
                name='unique_active_waitlist_per_user_show_category',
            ),
            models.CheckConstraint(
                name='offer_expires_at_only_when_offered',
                check=(
                    models.Q(status='offered') 
                    | models.Q(offer_expires_at__isnull=True)
                ),
            ),
        ]

        indexes = [
            models.Index(
                fields=['show', 'category', 'status', 'created_at'],
                name='idx_waitlist_lookup',
            ),
        ]

    def __str__(self):
        return f"Waitlist: {self.user} → {self.show} ({self.category.name}) [{self.status}]"
