#!/usr/bin/env bash
set -e

BACKEND="traffsoft-backend"
FRONTEND="traffsoft-frontend"

echo "===> Запускаю backend..."
cd "$BACKEND"

if [ -d "venv/Scripts" ]; then
  source venv/Scripts/activate
elif [ -d "venv/bin" ]; then
  source venv/bin/activate
fi

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACK_PID=$!

cd ..

echo "===> Запускаю frontend..."
cd "$FRONTEND"
npm run dev -- --host 127.0.0.1 &
FRONT_PID=$!

cd ..

echo ""
echo "Backend PID: $BACK_PID (http://127.0.0.1:8000)"
echo "Frontend PID: $FRONT_PID (http://localhost:5173)"
echo "Все запущено. Ctrl+C остановит управляющий скрипт (процессы останутся)."
wait
