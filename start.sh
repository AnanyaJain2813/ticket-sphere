#!/bin/bash
echo "🚀 Starting TicketSphere Local Development Environment..."

# 1. Setup Backend
echo "📦 Setting up Python Virtual Environment..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt --quiet

echo "🗄️ Running Database Migrations (SQLite)..."
python manage.py migrate

echo "🌱 Seeding Database (Optional)..."
# python manage.py seed_db

echo "🎬 Starting Django Backend Server on port 8000..."
python manage.py runserver 8000 &
BACKEND_PID=$!

echo "⚙️ Starting Celery Worker..."
celery -A core worker -l info &
CELERY_WORKER_PID=$!

echo "⏱️ Starting Celery Beat Scheduler..."
celery -A core beat -l info &
CELERY_BEAT_PID=$!

cd ..

# 2. Setup Frontend
echo "💻 Setting up Frontend (Vite + React)..."
cd frontend
npm install --silent

echo "✨ Starting Frontend Server..."
npm run dev &
FRONTEND_PID=$!

echo "✅ All services started! TicketSphere is running."
echo "Press Ctrl+C to stop all services."

# Wait for user interrupt
trap "echo '🛑 Stopping all services...'; kill $BACKEND_PID $CELERY_WORKER_PID $CELERY_BEAT_PID $FRONTEND_PID; exit" INT TERM
wait
