#!/usr/bin/env python3
"""
Массовая синхронизация subscription_end_date для всех пользователей
"""

import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import sys

load_dotenv('/opt/vpvks/.env')

# Marzban config
MARZBAN_URL = os.getenv('MARZBAN_URL', 'https://127.0.0.1:8000')
MARZBAN_ADMIN = os.getenv('MARZBAN_ADMIN', 'admin')
MARZBAN_PASSWORD = os.getenv('MARZBAN_PASSWORD', 'j8X0EcIllDwPK')

# PostgreSQL config
import psycopg2
from psycopg2.extras import RealDictCursor

DB_HOST = 'vpn_postgres'
DB_NAME = os.getenv('POSTGRES_DB', 'vpn_bot_db')
DB_USER = os.getenv('POSTGRES_USER', 'vpn_bot_user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'vp62RofV5h')

def get_marzban_token():
    response = requests.post(
        f"{MARZBAN_URL}/api/admin/token",
        data={"username": MARZBAN_ADMIN, "password": MARZBAN_PASSWORD},
        timeout=10,
        verify=False
    )
    return response.json().get("access_token")

def get_user_info(token, username):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{MARZBAN_URL}/api/user/{username}",
        headers=headers,
        timeout=10,
        verify=False
    )
    return response.json()

def sync_all():
    print("🔄 Синхронизация всех пользователей...")
    
    token = get_marzban_token()
    print("✅ Токен получен")
    
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Получить всех пользователей из БД
    cursor.execute("SELECT id, username FROM users")
    users = cursor.fetchall()
    
    updated = 0
    not_found = 0
    
    for user in users:
        user_id = user['id']
        username = f"user_{user_id}"
        
        # Получить данные из Marzban
        user_data = get_user_info(token, username)
        
        if 'error' in user_data or 'expire' not in user_data:
            print(f"⏭️ {username}: не найден в Marzban")
            not_found += 1
            continue
        
        expire_timestamp = user_data.get('expire')
        
        if expire_timestamp and expire_timestamp > 0:
            subscription_end_date = datetime.fromtimestamp(expire_timestamp)
        else:
            subscription_end_date = None
        
        # Обновить в БД
        cursor.execute("""
            UPDATE users 
            SET subscription_end_date = %s
            WHERE id = %s
        """, (subscription_end_date, user_id))
        
        if cursor.rowcount > 0:
            print(f"✅ {username}: {subscription_end_date or 'бессрочно'}")
            updated += 1
        else:
            print(f"⏭️ {username}: не обновлено")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n📊 Результаты: {updated} обновлено, {not_found} не найдено")

if __name__ == "__main__":
    sync_all()
