import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from venues.models import Venue, SeatLayout, SeatCategory, Seat
from events.models import Event, Show
from bookings.models import ShowSeat

User = get_user_model()

class Command(BaseCommand):
    help = 'Seeds default venues, categories, seats, events, and shows for presentation/judging.'

    def handle(self, *args, **options):
        organizer_user, _ = User.objects.get_or_create(
            username='organizer',
            defaults={'email': 'organizer@gmail.com', 'role': 'organiser'}
        )
        if not organizer_user.check_password('12345678'):
            organizer_user.set_password('12345678')
            organizer_user.save()
        
        # Ensure organizer owns all events
        Event.objects.all().update(created_by=organizer_user)

        if Event.objects.filter(title='Interstellar (IMAX 70mm Special)').exists():
            self.stdout.write(self.style.SUCCESS("Database is already seeded. Skipping rest..."))
            return
            
        self.stdout.write(self.style.SUCCESS("Starting database seeding..."))

        # 1. Create Default Users
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@redseats.in', 'role': 'admin'}
        )
        if not admin_user.check_password('admin1234'):
            admin_user.set_password('admin1234')
            admin_user.save()

        organizer_user, _ = User.objects.get_or_create(
            username='organizer',
            defaults={'email': 'organizer@gmail.com', 'role': 'organiser'}
        )
        if not organizer_user.check_password('12345678'):
            organizer_user.set_password('12345678')
            organizer_user.save()

        customer_user, _ = User.objects.get_or_create(
            username='customer',
            defaults={'email': 'customer@redseats.in', 'role': 'customer'}
        )
        if not customer_user.check_password('customer1234'):
            customer_user.set_password('customer1234')
            customer_user.save()

        self.stdout.write(self.style.SUCCESS("Default users ensured (admin/admin1234, organiser/organiser1234, customer/customer1234)"))

        # 2. Default Seat Categories
        cat_standard, _ = SeatCategory.objects.get_or_create(
            name='Standard',
            defaults={'base_price': 250.00, 'description': 'Comfortable standard seating'}
        )
        cat_premium, _ = SeatCategory.objects.get_or_create(
            name='Premium',
            defaults={'base_price': 450.00, 'description': 'Prime viewing area with extra legroom'}
        )
        cat_vip, _ = SeatCategory.objects.get_or_create(
            name='VIP',
            defaults={'base_price': 750.00, 'description': 'Luxury recliner seats with in-seat dining'}
        )

        self.stdout.write(self.style.SUCCESS("Seat categories created (Standard, Premium, VIP)"))

        # 3. Create Venues and Seats
        def create_venue_with_seats(name, location, rows_cnt, cols_cnt):
            venue, created = Venue.objects.get_or_create(
                name=name,
                defaults={'location': location, 'total_capacity': rows_cnt * cols_cnt}
            )
            if created:
                layout = SeatLayout.objects.create(
                    venue=venue,
                    name='Main Screen Layout',
                    total_rows=rows_cnt,
                    total_columns=cols_cnt
                )
                for r in range(rows_cnt):
                    row_name = chr(65 + r) # A, B, C...
                    # Assign category based on row depth
                    category = cat_vip if r == 0 else (cat_premium if r < rows_cnt // 2 else cat_standard)
                    for c in range(1, cols_cnt + 1):
                        Seat.objects.create(
                            venue=venue,
                            layout=layout,
                            category=category,
                            row_name=row_name,
                            col_number=c,
                            coord_x=c * 10,
                            coord_y=r * 10
                        )
            return venue

        venue1 = create_venue_with_seats('PVR Director\'s Cut', 'Vasant Kunj, New Delhi', 5, 10) # 50 seats
        venue2 = create_venue_with_seats('PVR ICON IMAX', 'Versova, Mumbai', 1, 10) # 10 seats

        self.stdout.write(self.style.SUCCESS("Venues and seat layouts created."))

        # 4. Create Events
        e1, _ = Event.objects.get_or_create(
            title='Interstellar (IMAX 70mm Special)',
            defaults={
                'event_type': 'movie',
                'description': 'Mankind was born on Earth. It was never meant to die here. Experience Christopher Nolan’s masterpiece in 70mm IMAX.',
                'banner_url': '/interstellar_wallpaper.jpg',
                'created_by': organizer_user
            }
        )
        if e1.banner_url != '/interstellar_wallpaper.jpg':
            e1.banner_url = '/interstellar_wallpaper.jpg'
            e1.save()

        e2, _ = Event.objects.get_or_create(
            title='Dune: Part Two',
            defaults={
                'event_type': 'movie',
                'description': 'Paul Atreides unites with Chani and the Fremen while seeking revenge against the conspirators who destroyed his family.',
                'banner_url': '/dune_wallpaper.png',
                'created_by': organizer_user
            }
        )
        if e2.banner_url != '/dune_wallpaper.png':
            e2.banner_url = '/dune_wallpaper.png'
            e2.save()

        e3, _ = Event.objects.get_or_create(
            title='Coldplay: Music of the Spheres World Tour',
            defaults={
                'event_type': 'concert',
                'description': 'Live in concert featuring iconic hits, laser light shows, and sustainable stadium stage design.',
                'banner_url': 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=1200&q=80',
                'created_by': organizer_user
            }
        )
        if e3.banner_url != 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=1200&q=80':
            e3.banner_url = 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=1200&q=80'
            e3.save()

        self.stdout.write(self.style.SUCCESS("Events created."))

        # 5. Create Shows & Generate ShowSeats
        now = timezone.now()

        def create_show_and_seats(event, venue, start_dt, end_dt):
            show, created = Show.objects.get_or_create(
                event=event,
                venue=venue,
                start_time=start_dt,
                defaults={'end_time': end_dt}
            )
            if created:
                seats = Seat.objects.filter(venue=venue)
                show_seats = [
                    ShowSeat(
                        show=show,
                        seat=seat,
                        category=seat.category,
                        price=seat.category.base_price,
                        status='available'
                    )
                    for seat in seats
                ]
                ShowSeat.objects.bulk_create(show_seats)
            return show

        # 3 shows for e1 (Interstellar)
        create_show_and_seats(e1, venue1, now + datetime.timedelta(hours=2), now + datetime.timedelta(hours=5))
        create_show_and_seats(e1, venue2, now + datetime.timedelta(days=1, hours=3), now + datetime.timedelta(days=1, hours=6))
        create_show_and_seats(e1, venue1, now + datetime.timedelta(days=2, hours=10), now + datetime.timedelta(days=2, hours=13))

        # 3 shows for e2 (Dune)
        create_show_and_seats(e2, venue1, now + datetime.timedelta(hours=4), now + datetime.timedelta(hours=7))
        create_show_and_seats(e2, venue2, now + datetime.timedelta(days=1, hours=6), now + datetime.timedelta(days=1, hours=9))
        create_show_and_seats(e2, venue1, now + datetime.timedelta(days=2, hours=14), now + datetime.timedelta(days=2, hours=17))

        # Concert event
        create_show_and_seats(e3, venue1, now + datetime.timedelta(days=2, hours=8), now + datetime.timedelta(days=2, hours=11))

        self.stdout.write(self.style.SUCCESS("🎉 Database successfully seeded with default venues, events, shows, and seats!"))
