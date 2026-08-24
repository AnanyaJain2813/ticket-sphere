# TicketSphere — High-Concurrency Ticket Booking System

A production-ready, full-stack event & movie ticket booking platform built with **Python (Django REST Framework & ASGI Channels)** for the backend API and **React 19 + TypeScript + Vite** for the dynamic web frontend.

---

## 🔗 Live Deployment

- **Frontend**: https://ticket-sphere-sand.vercel.app/
- **Backend API**: https://web-production-6ecbf.up.railway.app/api/

**Demo Login Credentials:**
- **Customer**: `customer` / `customer1234`
- **Organiser**: `organiser` / `organiser1234`
- **Admin**: `admin` / `admin1234`

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
2. **Setup & API Guide**: `README.md` (this file) & `backend/.env.example`
3. **System Design Document**: `system_design.md` (800-word design write-up)
4. **Deployment Blueprints**: `render.yaml` (Render Backend Blueprint) & Vercel deployment guide

---

## ✨ Key Features

- 🎟️ **Interactive Seat Layout Map**: Visual layout grid with real-time status indicators (Available, Held, Booked).
- ⏱️ **Atomic Seat Hold & TTL Engine**: Configurable 10-minute hold timer with animated countdown ring and automatic background hold release.
- 🔒 **Concurrency & Double-Booking Protection**: Database row locking via `select_for_update()` inside atomic transactions; Idempotency header protection on booking requests.
- 📲 **Live Email Delivery Polling**: Asynchronous Brevo SMTP email integration. The UI silently polls the backend to verify actual email delivery status and dynamically updates the confirmation screen (Success vs Pending).
- ⏳ **Automated Category Waitlist**: When an event sells out, users can join a waitlist per seat category (`VIP`, `Premium`, `Standard`). When a booking is cancelled, seats are automatically assigned to the next waitlisted customer with a time-limited offer window.
- 📊 **Organiser Revenue & Active Database Analytics**: Real-time revenue summary, occupancy rate metrics, and a dynamic table exposing the active database shows directly in the organiser dashboard.
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
- **Redis Server** (Required for Celery background tasks and Websockets)

---

## ⚡ Zero-Config Local Setup (Recommended)

The absolute easiest way to test this project locally is to use the included `start.sh` script, which automatically provisions the virtual environment, installs dependencies, migrates the database, seeds the test dataset, and boots both frontend and backend servers simultaneously on isolated ports (5175/8005) to avoid local port collisions.

```bash
# Make the script executable
chmod +x start.sh

# Run the complete stack (Django + React + Celery)
./start.sh
```

---

## ⚡ Manual Setup

### 1. Backend Setup (Python / Django)
```bash
cd backend

# Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python backend dependencies
pip install -r ../requirements.txt

# Run database migrations & seed presentation dataset
python manage.py migrate
python manage.py seed_db

# Start Django backend server
python manage.py runserver 8005
```

### 2. Frontend Setup (React / Vite)
```bash
cd frontend

# Set up environment variables
# Create a .env file in the frontend folder:
# echo "VITE_API_BASE_URL=http://localhost:8005/api" > .env

# Install React frontend dependencies
npm install

# Start Vite dev server
npm run dev -- --port 5175
```

### 3. SMTP Email Configuration (Optional)
By default, the backend simulates email delivery by printing to the terminal console (to prevent crashes on unconfigured environments). To test real email delivery:
1. Create a `backend/.env` file.
2. Add your Brevo SMTP credentials (see `backend/.env.example`).
3. Restart the backend server. The UI will automatically poll and display actual email delivery successes!

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
