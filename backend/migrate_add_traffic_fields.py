#!/usr/bin/env python3
"""
Миграция: Добавление полей data_limit_gb и used_traffic_gb
Запуск: docker exec vpn_backend python /app/migrate_add_traffic_fields.py
"""

import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, '/app')

from server import app
from database.db_config import db
from sqlalchemy import text

def add_traffic_fields():
    """Добавление полей трафика в таблицу users"""
    
    print("🔄 Начало миграции: добавление полей трафика...")
    
    with app.app_context():
        try:
            # Проверяем существование колонок
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]
            
            # Добавляем data_limit_gb если нет
            if 'data_limit_gb' not in columns:
                print("📝 Добавление колонки data_limit_gb (FLOAT, NULL)...")
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN data_limit_gb FLOAT"
                    ))
                    conn.commit()
                print("✅ data_limit_gb добавлена")
            else:
                print("ℹ️  data_limit_gb уже существует")
            
            # Добавляем used_traffic_gb если нет
            if 'used_traffic_gb' not in columns:
                print("📝 Добавление колонки used_traffic_gb (FLOAT, DEFAULT 0.0)...")
                with db.engine.connect() as conn:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN used_traffic_gb FLOAT DEFAULT 0.0"
                    ))
                    conn.commit()
                print("✅ used_traffic_gb добавлена")
            else:
                print("ℹ️  used_traffic_gb уже существует")
            
            print("\n✅ Миграция успешно выполнена!")
            print("\n📊 Информация:")
            print("   - data_limit_gb: лимит трафика в GB")
            print("   - used_traffic_gb: использованный трафик в GB")
            
        except Exception as e:
            print(f"❌ Ошибка при выполнении миграции: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


if __name__ == '__main__':
    success = add_traffic_fields()
    sys.exit(0 if success else 1)
