import os
import sys
import django
from datetime import timedelta
from django.utils import timezone
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from events.models import Event, Show
from venues.models import Venue, SeatCategory, Seat
from bookings.models import ShowSeat, Booking

def seed_movies():
    print("Flushing existing data...")
    Booking.objects.all().delete()
    ShowSeat.objects.all().delete()
    Show.objects.all().delete()
    Event.objects.all().delete()
    Venue.objects.all().delete()
    SeatCategory.objects.all().delete()
    Seat.objects.all().delete()
    print("Seeding Default Users...")
    from django.contrib.auth import get_user_model
    User = get_user_model()
    User.objects.get_or_create(username='user_alice')
    User.objects.get_or_create(username='user_bob')
    print("Old data flushed.")

    print("Seeding Seat Categories...")
    vip = SeatCategory.objects.create(name='VIP Recliner', base_price=500.00)
    premium = SeatCategory.objects.create(name='Premium', base_price=300.00)
    standard = SeatCategory.objects.create(name='Standard', base_price=150.00)

    print("Seeding Cinemas (Venues)...")
    cinemas = [
        Venue.objects.create(name='PVR Directors Cut', location='Ambience Mall, Vasant Kunj, New Delhi', total_capacity=100),
        Venue.objects.create(name='PVR INOX IMAX', location='Phoenix Palladium, Lower Parel, Mumbai', total_capacity=100),
        Venue.objects.create(name='Cinepolis VIP', location='Orion Mall, Rajajinagar, Bangalore', total_capacity=100)
    ]
    
    from venues.models import SeatLayout
    
    print("Seeding Cinema Seats (Screen Layout)...")
    for venue in cinemas:
        layout = SeatLayout.objects.create(venue=venue, name='Standard Cinema Layout', total_rows=10, total_columns=10)
        # Standard cinema layout: A-J rows, 1-10 cols
        for r, row_name in enumerate('ABCDEFGHIJ'):
            for col in range(1, 11):
                # Rear rows (I, J) are VIP
                if r >= 8:
                    cat = vip
                # Middle rows (E, F, G, H) are Premium
                elif r >= 4:
                    cat = premium
                # Front rows (A, B, C, D) are Standard
                else:
                    cat = standard
                
                Seat.objects.create(
                    venue=venue,
                    layout=layout,
                    row_name=row_name,
                    col_number=col,
                    category=cat,
                    coord_x=col * 50.0,
                    coord_y=r * 50.0
                )

    print("Seeding Movies (Events)...")
    movies = [
        {
            'title': 'Dune: Part Two',
            'type': 'movie',
            'desc': 'Paul Atreides unites with Chani and the Fremen while on a warpath of revenge against the conspirators who destroyed his family.',
            'banner': '/dune_wallpaper.png'
        }
    ]

    db_movies = []
    for m in movies:
        db_movies.append(Event.objects.create(
            title=m['title'],
            event_type=m['type'],
            description=m['desc'],
            banner_url=m['banner']
        ))

    print("Seeding Showtimes...")
    now = timezone.now()
    shows = []
    for i in range(10):
        movie = random.choice(db_movies)
        cinema = random.choice(cinemas)
        start = now + timedelta(days=random.randint(0, 3), hours=random.randint(10, 22))
        end = start + timedelta(hours=3)
        shows.append(Show.objects.create(
            event=movie,
            venue=cinema,
            start_time=start,
            end_time=end
        ))

    print("Generating Show Seats for all Showtimes (this takes a moment)...")
    show_seats = []
    for show in shows:
        seats = Seat.objects.filter(venue=show.venue)
        for seat in seats:
            price = 500 if seat.category.name == 'VIP Recliner' else (300 if seat.category.name == 'Premium' else 150)
            show_seats.append(ShowSeat(
                show=show,
                seat=seat,
                category=seat.category,
                price=price
            ))
    ShowSeat.objects.bulk_create(show_seats)

    print("Successfully seeded Movies, Cinemas, and Showtimes!")

if __name__ == '__main__':
    seed_movies()
