# TicketSphere — High-Concurrency Ticket Booking System

A production-ready, full-stack event & movie ticket booking platform built with **Python (Django REST Framework & ASGI Channels)** for the backend API and **React 19 + TypeScript + Vite** for the dynamic web frontend.

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend API** | **Python 3.9+ (Django 4.2 & DRF)** | REST API, role-based JWT auth, seat-hold TTL engine, waitlist queue |
| **Real-Time WebSockets** | **Django Channels (Daphne / ASGI)** | Real-time seat map updates & live hold/booking broadcasting |
| **Frontend Web App** | **React 19, TypeScript, Vite** | Single-page application with responsive interactive seat map grid |
| **Styling & Icons** | **Tailwind CSS & Lucide Icons** | Custom glassmorphism dark theme with cursor ambient spotlight |
| **Database** | **PostgreSQL (Production) / SQLite (Local Dev)** | Relational DB with row-level `select_for_update` locking & unique constraints (Railway Managed PostgreSQL in production; SQLite for local dev) |
| **Task Queue & Cache** | **Celery 5 & Redis 7** | Asynchronous background hold release & waitlist offer expiration |
| **Email Delivery** | **Brevo SMTP (Sendinblue)** | Live M-Ticket email delivery with embedded QR code passes |

*(Note: Node.js 18+ is used locally as the JavaScript development environment to compile and bundle the React frontend).*

---

## 📦 Deliverables Summary

1. **Source Code Zip**: `TicketSphere.zip`
2. **Setup & API Guide**: `README.md` (this file) & `.env.example`
3. **System Design Document**: `system_design.md` (800-word design write-up)
4. **Deployment Blueprints**: `render.yaml` (Render Backend Blueprint) & Vercel deployment guide

---

## ✨ Key Features

- 🎟️ **Interactive Seat Layout Map**: Visual layout grid with real-time status indicators (Available, Held, Booked).
- ⏱️ **Atomic Seat Hold & TTL Engine**: Configurable 10-minute hold timer with animated countdown ring and automatic background hold release.
- 🔒 **Concurrency & Double-Booking Protection**: Database row locking via `select_for_update()` inside atomic transactions; Idempotency header protection on booking requests.
- 📲 **M-Ticket QR Code Generation**: Instant QR code pass generation encoding booking reference with Brevo SMTP email integration.
- ⏳ **Automated Category Waitlist**: When an event sells out, users can join a waitlist per seat category (`VIP`, `Premium`, `Standard`). When a booking is cancelled, seats are automatically assigned to the next waitlisted customer with a time-limited offer window.
- 📊 **Organiser Revenue Analytics**: Real-time revenue summary, total bookings count, and occupancy rate metrics scoped per organiser.
- 🛠️ **Admin Venue & Layout Builder**: Interactive 2D grid builder for creating complex seating layouts (rows, columns, categories).

---

## ⚡ Quickstart & Local Setup

### Database Configuration & Driver Setup
- **Production Deployment**: Uses Railway's managed **PostgreSQL**. The backend connects using standard `psycopg2-binary` via the `DATABASE_URL` environment variable:
  ```
  DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname>
  ```
- **Local Development**: Defaults to **SQLite** (`db.sqlite3`) for instant zero-config setup. You can also connect to a local PostgreSQL instance or Docker container (`docker-compose up -d`) by setting `DATABASE_URL` or standard PostgreSQL environment variables in `.env`.

### Prerequisites
- **Python 3.9+** (For Django Backend)
- **Node.js 18+** (For React Frontend compilation)
- **PostgreSQL or SQLite** (SQLite used by default for zero-config local dev; PostgreSQL driver `psycopg2-binary` included in `requirements.txt`)

### 1. Backend Setup (Python / Django)
```bash
cd backend

# Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python backend dependencies
pip install -r requirements.txt

# Run database migrations & seed presentation dataset
python manage.py migrate
python manage.py seed_db

# Start Django backend server on port 8000
python manage.py runserver 8000
```

### 2. Frontend Setup (React / Vite)
```bash
cd frontend

# Install React frontend dependencies
npm install

# Start Vite dev server on port 5173
npm run dev
```

---

## 🔑 Default Demo Credentials

- **Admin Account**: `admin` / `admin1234`
- **Organiser Account**: `organiser` / `organiser1234`
- **Customer Account**: `customer` / `customer1234`

---

## 📡 API Endpoints Summary

### Authentication
- `POST /api/auth/register/` - Register new user (Customer / Organiser / Admin)
- `POST /api/auth/login/` - JWT login (Returns access & refresh tokens)
- `GET /api/auth/me/` - Retrieve authenticated user profile

### Admin & Venues
- `GET /api/admin/venues/` - List all venues
- `POST /api/admin/venues/` - Create venue with seat layout grid
- `GET /api/admin/seat-categories/` - List seat categories

### Events & Shows
- `GET /api/events/` - List all events
- `POST /api/events/create/` - Create an event (Organiser)
- `GET /api/shows/` - List active shows with availability
- `POST /api/shows/create/` - Schedule a show & generate ShowSeat rows (Organiser)

### Bookings & Seat Holds
- `POST /api/shows/<show_id>/seats/<seat_id>/hold/` - Hold seat with 10-min TTL
- `POST /api/shows/<show_id>/seats/<seat_id>/book/` - Confirm booking & issue QR ticket
- `POST /api/bookings/<booking_id>/cancel/` - Cancel booking & trigger waitlist re-allocation
- `GET /api/bookings/history/` - View customer booking history

### Waitlist & Analytics
- `POST /api/waitlist/join/` - Join category waitlist for sold-out show
- `GET /api/waitlist/` - View user waitlist entries
- `GET /api/organiser/revenue/` - Organiser revenue analytics & occupancy rate
