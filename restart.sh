#!/usr/bin/env bash
set -e

echo "===> Останавливаю старые процессы..."
pkill -f "uvicorn app.main:app" || true
pkill -f "vite" || pkill -f "npm run dev" || true
sleep 1

echo "===> Перезапуск..."
./start.sh
