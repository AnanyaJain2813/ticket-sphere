"""
events/models.py — Event and Show models.

An Event is the abstract entity (a movie title, a concert tour).
A Show is a specific instance of an Event at a particular Venue,
date, and time.
"""

import uuid
from django.db import models
from django.conf import settings
from venues.models import Venue


class Event(models.Model):
    """A movie, concert, or other bookable event."""
    TYPE_CHOICES = [
        ('movie', 'Movie'),
        ('concert', 'Concert'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField(blank=True, default='')
    banner_url = models.URLField(blank=True, default='')

    # The organiser who created this event.
    # Used to scope revenue queries so organiser A cannot see organiser B's data.
    # null=True / blank=True so that legacy seed data and admin-created events
    # (without a logged-in organiser) remain valid.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='created_events',
        help_text="The organiser who owns this event.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'events'

    def __str__(self):
        return f"{self.title} ({self.get_event_type_display()})"


class Show(models.Model):
    """
    A scheduled showing of an Event at a specific Venue and time.
    Each Show will have its own set of ShowSeats (created when the
    show is published) so that seat availability is tracked per-show.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='shows')
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='shows')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shows'

    def __str__(self):
        return f"{self.event.title} @ {self.venue.name} — {self.start_time:%Y-%m-%d %H:%M}"
