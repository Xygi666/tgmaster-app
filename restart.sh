#!/usr/bin/env bash
set -e

echo "===> TeleFlow: останавливаю старые процессы..."
pkill -f "uvicorn app.main:app" || true
pkill -f "vite" || pkill -f "npm run dev" || true
sleep 1

echo "===> TeleFlow: перезапуск..."
./start.sh
