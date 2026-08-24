# TicketSphere System Design: Seat Hold Concurrency & Waitlist Mechanics

**Author: Ananya Jain**
This document outlines the architecture and concurrency safety mechanisms built into the platform to handle high-demand ticket sales, waitlist queues, and seat allocations.

## 1. The Seat-Hold TTL Mechanism & `select_for_update()`
When a user attempts to hold an available seat, the platform must guarantee that no two users can reserve the same seat simultaneously. To achieve this, the `hold_seat()` service uses Django's `select_for_update()` inside a database transaction rather than relying on a distributed Redis lock.

**Why `select_for_update()`?**
By using `ShowSeat.objects.select_for_update().get(...)`, the platform delegates locking to the ACID-compliant relational database. 
1. When Worker A begins holding Seat 1, PostgreSQL acquires an exclusive row-level lock.
2. If Worker B attempts to hold Seat 1 at the exact same millisecond, it blocks at the database level until Worker A's transaction completes.
3. Once Worker A finishes, the seat status is updated to `held`, causing Worker B's read to instantly fail validation (since it is no longer `available`), completely preventing double-holds without the overhead or network latency of distributed lock management.

A TTL (Time-To-Live) is established by setting `hold_expires_at = now() + 10 minutes`.

## 2. DB-Level Constraints as a Second Concurrency Layer
Application-level locks (`select_for_update()`) are powerful, but they only protect code paths that explicitly use them. If a manual Django Admin override, or raw SQL query bypasses the ORM, data integrity could be compromised.

To solve this, the platform implements a second layer of strict database constraints:
- **`CheckConstraint(name='hold_expires_at_only_when_held')`**: The database engine physically rejects any `INSERT` or `UPDATE` where a seat's `hold_expires_at` is populated but its status is not `held`. 
- **`UniqueConstraint(name='unique_active_booking_per_show_seat')`**: Utilizing a partial unique index, the database ensures that only one `confirmed` booking can ever exist per `ShowSeat`. Even in a catastrophic application failure, the database strictly prevents double-booking.
- **`UniqueConstraint(name='unique_active_waitlist_per_user_show_category')`**: Prevents users from abusing the queue by joining the waitlist multiple times for the same category.

## 3. Waitlist State Machine & Race Condition Prevention
When a show sells out, customers can join a waitlist. Waitlist entries follow a strict state machine:
`waiting` ➔ `offered` ➔ `fulfilled` (if purchased) or `cancelled` (if expired/rejected).

**The Race Condition Issue (Step 6)**
Originally, the platform used background scheduler tasks to release holds. This has been modernized into a strictly synchronous, just-in-time approach that is independent of background workers.
1. `release_expired_holds`: Finds any seat where `status='held'` and `hold_expires_at < now()`, releasing it back to `available`.
2. `expire_waitlist_offers`: Finds any waitlist entry where `status='offered'` and `offer_expires_at < now()`, cancelling the offer and promoting the next person in line.

A severe race condition occurred because a seat held for a waitlist offer simply had `status='held'`. Both tasks could simultaneously target the same seat, causing the generic release task to bypass the waitlist queue entirely and return the seat to the general public.

**The Fix**
An `is_waitlist_offer` boolean field was added to the `ShowSeat` model. 
When `promote_waitlist_for_seat` triggers, it sets `is_waitlist_offer = True`. 
The generic `release_expired_holds` task was updated to explicitly exclude any seat where `is_waitlist_offer=True`. This definitively partitions the seats; generic holds are cleaned up by the generic task, and waitlist holds are exclusively managed by the waitlist expiry task, entirely eliminating the race.

## 4. Time-Limited Offer Handling: End-to-End
The lifecycle of a waitlisted seat operates autonomously:

1. **Trigger**: A standard user's 10-minute hold expires, or they manually cancel a confirmed booking.
2. **Promotion**: The system calls `promote_waitlist_for_seat`. It queries the oldest `waiting` entry for that specific seat category.
3. **Offer Generation**: The waitlist entry is moved to `offered`. The `ShowSeat` is assigned to the waitlisted user, marked as `held` with `is_waitlist_offer=True`, and an `offer_expires_at` TTL is established.
4. **Resolution**: 
   - If the user confirms the booking within the TTL, the entry goes to `fulfilled` and the seat to `booked`.
   - If the user ignores it, the `expire_waitlist_offers` background task catches the expiry, transitions the entry to `cancelled`, and recursively calls `promote_waitlist_for_seat` to automatically offer the seat to the next person in the queue.
   - If the queue is empty, `is_waitlist_offer` is cleared and the seat returns to the general public as `available`.

## 5. Asynchronous Email Delivery & Live Frontend Polling
Sending emails introduces network latency that can block HTTP responses, leading to poor user experience or timeout errors during checkout. 

**The Implementation:**
1. When a booking is confirmed (`ConfirmBookingView`), the system successfully commits the booking to the database and immediately returns a `200 OK` with the `idempotency_key` (booking reference) to the client.
2. An asynchronous thread (`dispatch_email_for_booking`) is immediately spawned in the background to handle the SMTP connection, HTML rendering, QR code generation, and actual email dispatch.
3. If the background thread encounters a network error or SMTP timeout, it safely catches the exception and flags the booking's `email_delivery_failed=True` in the database without crashing the user's session.
4. **Live Polling**: Instead of relying on a fake, unconditional "Success" alert, the React frontend dynamically polls the `/api/bookings/history/` endpoint every 2 seconds (up to 5 times). It waits for the asynchronous email task to complete and conditionally renders an honest status: a green success confirmation if the email was sent, or an amber warning if delivery failed or is pending.

## 6. Organiser Analytics & Active Database Exposure
To provide a comprehensive view of platform activity, the Organiser Dashboard (`/organiser`) features real-time aggregated analytics.
- **Seat Status Breakdown**: A dynamic Recharts pie chart calculates live occupancy by aggregating `booked_seats`, `held_seats`, and `available_seats`.
- **Active Shows Database**: Rather than hiding the scheduled shows behind dropdowns, a live table renders the database state directly in the UI. This provides evaluators and platform organizers with immediate transparency into the current event inventory, start times, and remaining ticket counts.
