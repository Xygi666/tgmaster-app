#!/usr/bin/env bash
set -e

echo "===> Останавливаю старые процессы..."

# убиваем uvicorn
pkill -f "uvicorn app.main:app" || true

# убиваем Vite / npm dev
pkill -f "vite" || pkill -f "npm run dev" || true

echo "===> Перезапуск..."
./start.sh
