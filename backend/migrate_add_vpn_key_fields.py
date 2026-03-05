#!/usr/bin/env python3
"""
Миграция: Добавление полей subscription_url и vpn_key_generated
Запуск: docker exec vpn_backend python /app/migrate_add_vpn_key_fields.py
"""

import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, '/app')

from server import app
from database.db_config import db
from sqlalchemy import text

def add_vpn_key_fields():
    """Добавление полей для хранения VPN ключа"""
    
    print("🔄 Начало миграции: добавление полей VPN ключа...")
    
    with app.app_context():
        try:
            # Проверяем существование колонок
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            # Добавляем subscription_url если нет
            if 'subscription_url' not in columns:
                print("📝 Добавление колонки subscription_url (TEXT, NULL)...")
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN subscription_url TEXT"
                    ))
                    conn.commit()
                print("✅ subscription_url добавлена")
            else:
                print("ℹ️  subscription_url уже существует")
            
            # Добавляем vpn_key_generated если нет
            if 'vpn_key_generated' not in columns:
                print("📝 Добавление колонки vpn_key_generated (BOOLEAN, DEFAULT FALSE)...")
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN vpn_key_generated BOOLEAN DEFAULT FALSE"
                    ))
                    conn.commit()
                print("✅ vpn_key_generated добавлена")
            else:
                print("ℹ️  vpn_key_generated уже существует")
            
            print("\n✅ Миграция успешно выполнена!")
            print("\n📊 Информация:")
            print("   - subscription_url: ссылка на VPN подписку (сохраняется)")
            print("   - vpn_key_generated: флаг генерации ключа")
            
        except Exception as e:
            print(f"❌ Ошибка при выполнении миграции: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


if __name__ == '__main__':
    success = add_vpn_key_fields()
    sys.exit(0 if success else 1)
