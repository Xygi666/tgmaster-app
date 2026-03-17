#!/usr/bin/env bash
set -e

# ---- BACKEND ----
echo "===> Запускаю backend..."
cd backend

# активация venv (Windows / Unix)
if [ -d "venv/Scripts" ]; then
  # Windows (Git Bash / MSYS)
  source venv/Scripts/activate
elif [ -d "venv/bin" ]; then
  # Linux / macOS
  source venv/bin/activate
fi

# запускаем uvicorn в фоне
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACK_PID=$!

cd ..

# ---- FRONTEND ----
echo "===> Запускаю frontend..."
cd frontend
npm run dev -- --host 127.0.0.1 &
FRONT_PID=$!

cd ..

echo "Backend PID: $BACK_PID"
echo "Frontend PID: $FRONT_PID"
echo "Все запущено. Нажми Ctrl+C, чтобы остановить этот управляющий скрипт (процессы останутся)."
wait
