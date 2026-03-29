#!/usr/bin/env python3
"""Одноразовый скрипт авторизации Telegram."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from app.core.config import settings
from telethon import TelegramClient

api_id = settings.TELEGRAM_API_ID
api_hash = settings.TELEGRAM_API_HASH
session_name = settings.TELEGRAM_SESSION_NAME or "tg_session"

if not api_id or not api_hash:
    print("ERROR: TELEGRAM_API_ID и TELEGRAM_API_HASH не настроены")
    sys.exit(1)

print(f"=== Авторизация Telegram ===")
print(f"API ID: {api_id}")
print()

client = TelegramClient(session_name, api_id, api_hash)

async def do_auth():
    await client.connect()
    if not await client.is_user_authorized():
        print("Введите номер телефона (с +):")
        phone = input().strip()
        await client.send_code_request(phone)
        print("Введите код из Telegram:")
        code = input().strip()
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            print(f"Ошибка: {e}")
            return
    me = await client.get_me()
    print()
    print(f"✅ Авторизован!")
    print(f"   {me.first_name} {me.last_name or ''}")
    print(f"   @{me.username}")
    print()
    await client.disconnect()

import asyncio
asyncio.run(do_auth())
input("Нажмите Enter...")
