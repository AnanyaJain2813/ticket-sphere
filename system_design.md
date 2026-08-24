# TicketSphere System Design: Seat Hold Concurrency & Waitlist Mechanics

This document outlines the architecture and concurrency safety mechanisms built into the platform to handle high-demand ticket sales, waitlist queues, and seat allocations.

## 1. Seat-Hold TTL & Concurrency Protection
To guarantee that no two users can reserve the same seat simultaneously, the `hold_seat()` service uses Django's `select_for_update()` inside a database transaction instead of a distributed Redis lock.

By using `ShowSeat.objects.select_for_update().get(...)`, the platform delegates locking to the ACID-compliant relational database:
1. When **Worker A** begins holding Seat 1, PostgreSQL acquires an exclusive row-level lock.
2. If **Worker B** attempts to hold the same seat simultaneously, its request blocks at the database level until Worker A's transaction completes.
3. Once Worker A finishes, the seat status updates to `held`. Worker B's transaction unblocks, but the subsequent read immediately fails validation because the seat is no longer `available`. This completely prevents double-holds without network latency or overhead from a lock manager.

A TTL (Time-To-Live) is established by setting `hold_expires_at = now() + 10 minutes`.

## 2. DB-Level Constraints
Application-level locks (`select_for_update()`) only protect code paths that explicitly use them. To prevent data integrity compromises from manual admin edits or raw SQL bypasses, the database enforces strict physical constraints:
- **`CheckConstraint(name='hold_expires_at_only_when_held')`**: Automatically rejects any insert or update where `hold_expires_at` is populated but the status is not `held`.
- **`UniqueConstraint(name='unique_active_booking_per_show_seat')`**: A partial unique index ensuring only one `confirmed` booking can ever exist per `ShowSeat` (preventing double-bookings).
- **`UniqueConstraint(name='unique_active_waitlist_per_user_show_category')`**: Prevents users from abusing the queue by joining a category waitlist multiple times.

## 3. Waitlist State Machine & Promotion Mechanics
When a show sells out, customers can join a waitlist. Waitlist entries follow a strict state machine:
`waiting` ➔ `offered` ➔ `fulfilled` (if booked) or `cancelled` (if expired).

**Preventing Race Conditions**:
The platform utilizes a just-in-time cleanup approach run via background tasks:
1. `release_expired_holds`: Releases standard holds (`status='held'` and `hold_expires_at < now()`) back to `available`.
2. `expire_waitlist_offers`: Cancels expired waitlist offers (`status='offered'` and `offer_expires_at < now()`) and promotes the next customer in line.

Because a waitlist offer hold also uses `status='held'`, a race condition could occur if both tasks targeted the same seat—potentially returning a waitlist-reserved seat to the general public.

To eliminate this, an `is_waitlist_offer` boolean field was added to the `ShowSeat` model. The generic `release_expired_holds` task explicitly excludes any seat where `is_waitlist_offer=True`. This cleanly partitions the logic: standard holds are managed by the release task, and waitlist holds are managed exclusively by the waitlist expiry task.

## 4. Time-Limited Offer Lifecycle
1. **Trigger**: A user's hold expires, or a confirmed booking is cancelled.
2. **Promotion**: The system calls `promote_waitlist_for_seat`, querying the oldest `waiting` entry for that specific seat category.
3. **Offer Generation**: The waitlist entry transitions to `offered`. The `ShowSeat` is assigned to the waitlisted user, marked as `held` with `is_waitlist_offer=True`, and a 10-minute `offer_expires_at` deadline is set.
4. **Resolution**:
   - If the user purchases within the TTL, the entry transitions to `fulfilled` and the seat to `booked`.
   - If the TTL expires, `expire_waitlist_offers` transitions the entry to `cancelled` and recursively calls `promote_waitlist_for_seat` to offer the seat to the next person.
   - If the queue is empty, `is_waitlist_offer` is cleared and the seat returns to `available` for the public.

## 5. Asynchronous Email & Live Polling
Sending emails introduces network latency that can block HTTP responses. 
- **Delivery**: When a booking is confirmed, the server commits the transaction and immediately returns a `200 OK` with the booking reference to the client. An asynchronous thread is spawned in the background to handle HTML rendering, QR code generation (encoding the booking UUID), and SMTP transmission. If transmission fails, it flags `email_delivery_failed=True` without crashing the user session.
- **Live Polling**: The React frontend polls `/api/bookings/history/` every 2 seconds (up to 5 times) to check the background task status, rendering a green success state or an amber warning if delivery fails.

## 6. Organiser Analytics
The Organiser Dashboard displays:
- **Occupancy Charts**: Live visual breakdowns of booked, held, and available seats.
- **Active Database Exposure**: A direct table view of scheduled shows and live inventory tracking to give organizers immediate transparency.
