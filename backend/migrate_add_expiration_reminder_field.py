#!/usr/bin/env python3
"""
Миграция: Добавление поля last_expiration_reminder_sent в таблицу users
"""

import psycopg2
from dotenv import load_dotenv
import os
import sys

# Загрузка переменных окружения
load_dotenv('/opt/vpvks/.env')

DB_HOST = os.getenv('POSTGRES_HOST', 'vpn_postgres')
DB_NAME = os.getenv('POSTGRES_DB', 'vpn_bot_db')
DB_USER = os.getenv('POSTGRES_USER', 'vpn_bot_user')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'vp62RofV5h')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')


def migrate():
    """Добавление колонки last_expiration_reminder_sent"""
    
    print("🔄 Начало миграции: добавление поля last_expiration_reminder_sent...")
    
    try:
        # Подключение к базе данных
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Проверка существования колонки
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'last_expiration_reminder_sent'
        """)
        
        if cursor.fetchone():
            print("ℹ️ Колонка уже существует, миграция не требуется")
            cursor.close()
            conn.close()
            return True
        
        # Добавление колонки
        print("📝 Добавление колонки last_expiration_reminder_sent (DATE, NULL)...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN last_expiration_reminder_sent DATE
        """)
        
        conn.commit()
        print("✅ Миграция успешно выполнена!")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
