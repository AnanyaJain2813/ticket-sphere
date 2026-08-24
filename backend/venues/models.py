"""
venues/models.py — Venue, SeatLayout, SeatCategory, and Seat models.

These represent the physical infrastructure: a venue has a layout grid,
the layout has rows/columns, and each cell is a Seat with a category
(Premium, Standard, etc.) and physical coordinates for rendering.
"""

import uuid
from django.db import models


class Venue(models.Model):
    """A physical venue (theater, stadium, arena) where shows are hosted."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    total_capacity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'venues'

    def __str__(self):
        return f"{self.name} ({self.location})"


class SeatLayout(models.Model):
    """
    Defines the seating grid dimensions for a venue.
    A venue may have multiple layouts (e.g., different configurations
    for concerts vs. theater-in-the-round).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='layouts')
    name = models.CharField(max_length=100, help_text="e.g. 'Main Hall', 'Balcony'")
    total_rows = models.PositiveIntegerField()
    total_columns = models.PositiveIntegerField()

    class Meta:
        db_table = 'seat_layouts'

    def __str__(self):
        return f"{self.name} @ {self.venue.name} ({self.total_rows}×{self.total_columns})"


class SeatCategory(models.Model):
    """
    Pricing tier for seats (e.g., Standard, Premium, VIP).
    Stored as a separate model so venues can share category definitions.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'seat_categories'
        verbose_name_plural = 'seat categories'

    def __str__(self):
        return self.name


class Seat(models.Model):
    """
    A physical seat inside a venue layout.

    Each seat has a grid position (row_name + col_number) and
    rendering coordinates (coord_x, coord_y) for the seat-map UI.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='seats')
    layout = models.ForeignKey(SeatLayout, on_delete=models.CASCADE, related_name='seats')
    category = models.ForeignKey(SeatCategory, on_delete=models.PROTECT, related_name='seats')
    row_name = models.CharField(max_length=10, help_text="e.g. 'A', 'B', 'AA'")
    col_number = models.PositiveIntegerField()
    coord_x = models.FloatField(help_text="X-coordinate for seat-map rendering")
    coord_y = models.FloatField(help_text="Y-coordinate for seat-map rendering")

    class Meta:
        db_table = 'seats'
        # ------------------------------------------------------------------
        # DB-LEVEL CONSTRAINT: unique_together
        # ------------------------------------------------------------------
        # This constraint is enforced by the database engine via a UNIQUE index,
        # not just by Django's model validation. This is critical because:
        #
        # Two concurrent requests could both pass Django's .validate_unique()
        # check in the same instant (both see no conflict), then both attempt
        # INSERT — without a DB-level unique index, BOTH would succeed,
        # creating duplicate seats at the same position.
        #
        # With the DB-level constraint, the second INSERT raises
        # IntegrityError, which Django surfaces cleanly.
        # ------------------------------------------------------------------
        unique_together = [('venue', 'row_name', 'col_number')]

    def __str__(self):
        return f"{self.venue.name} — {self.row_name}{self.col_number} ({self.category.name})"
