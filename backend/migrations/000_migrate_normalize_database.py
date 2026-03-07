#!/usr/bin/env python3
"""Миграция: нормализация БД"""

import sys
import os
import json

sys.path.insert(0, '/app')

from server import app
from database.db_config import db
from sqlalchemy import text
from datetime import datetime


def migrate_normalize_database():
    print("🔄 Начало миграции: нормализация БД...")

    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]

            # Шаг 1: Создание таблицы connection_logs
            print("\n📝 Шаг 1: Создание таблицы connection_logs...")
            tables = db.inspect(db.engine).get_table_names()
            if 'connection_logs' not in tables:
                print("   Создание таблицы connection_logs...")
                db.session.execute(text("""
                    CREATE TABLE connection_logs (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                        connected BOOLEAN NOT NULL,
                        ip_address VARCHAR(45),
                        user_agent VARCHAR(500)
                    )
                """))
                db.session.commit()
                db.session.execute(text("CREATE INDEX idx_connection_logs_user_id ON connection_logs(user_id)"))
                db.session.execute(text("CREATE INDEX idx_connection_logs_timestamp ON connection_logs(timestamp)"))
                db.session.commit()
                print("   ✅ Таблица connection_logs создана")
            else:
                print("   ℹ️  Таблица connection_logs уже существует")

            # Шаг 2: Перенос данных из connection_history
            print("\n📝 Шаг 2: Перенос данных из connection_history...")
            if 'connection_history' in columns:
                users_result = db.session.execute(text("""
                    SELECT id, connection_history
                    FROM users
                    WHERE connection_history IS NOT NULL
                    AND connection_history != '[]'
                """)).fetchall()

                migrated_count = 0
                for user_id, history_json in users_result:
                    try:
                        history = json.loads(history_json)
                        if isinstance(history, list):
                            for entry in history:
                                timestamp = entry.get('timestamp')
                                connected = entry.get('connected', True)
                                if timestamp:
                                    db.session.execute(text("""
                                        INSERT INTO connection_logs (user_id, timestamp, connected)
                                        VALUES (:user_id, :timestamp, :connected)
                                    """), {'user_id': user_id, 'timestamp': timestamp, 'connected': connected})
                                    migrated_count += 1
                    except Exception as e:
                        print(f"   ⚠️  Ошибка при парсинге JSON для пользователя {user_id}: {e}")

                db.session.commit()
                print(f"   ✅ Перенесено {migrated_count} записей о подключениях")
            else:
                print("   ℹ️  Колонка connection_history не существует")

            # Шаг 3: Добавление колонки deleted_at
            print("\n📝 Шаг 3: Добавление колонки deleted_at...")
            if 'deleted_at' not in columns:
                db.session.execute(text("ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP"))
                db.session.commit()
                db.session.execute(text("CREATE INDEX idx_users_deleted_at ON users(deleted_at)"))
                db.session.commit()
                print("   ✅ Колонка deleted_at добавлена")
            else:
                print("   ℹ️  Колонка deleted_at уже существует")

            # Шаг 4: Удаление старых колонок
            print("\n📝 Шаг 4: Удаление старых колонок...")
            columns_to_drop = [
                'connection_history', 'is_active', 'connection_count',
                'last_connected_ip', 'last_connected_user_agent',
                'suspicious_activity', 'email'
            ]
            columns = [col['name'] for col in inspector.get_columns('users')]
            for col_name in columns_to_drop:
                if col_name in columns:
                    db.session.execute(text(f"ALTER TABLE users DROP COLUMN {col_name}"))
                    db.session.commit()
                    print(f"   ✅ Колонка {col_name} удалена")
                else:
                    print(f"   ℹ️  Колонка {col_name} уже отсутствует")

            # Шаг 5: Обновление таблицы payments
            print("\n📝 Шаг 5: Обновление таблицы payments...")
            payment_columns = [col['name'] for col in inspector.get_columns('payments')]
            new_payment_columns = {
                'yookassa_payment_id': 'VARCHAR(100)',
                'yookassa_status': 'VARCHAR(50)',
                'confirmation_url': 'TEXT'
            }
            for col_name, col_type in new_payment_columns.items():
                if col_name not in payment_columns:
                    db.session.execute(text(f"ALTER TABLE payments ADD COLUMN {col_name} {col_type}"))
                    db.session.commit()
                    print(f"   ✅ Колонка {col_name} добавлена")
                else:
                    print(f"   ℹ️  Колонка {col_name} уже существует")

            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)"))
            db.session.execute(text("CREATE INDEX IF NOT EXISTS idx_payments_yookassa_id ON payments(yookassa_payment_id)"))
            db.session.commit()
            print("   ✅ Индексы для payments созданы")

            # Шаг 6: Удаление таблицы vpn_configs
            print("\n📝 Шаг 6: Удаление таблицы vpn_configs...")
            tables = db.inspect(db.engine).get_table_names()
            if 'vpn_configs' in tables:
                db.session.execute(text("DROP TABLE IF EXISTS vpn_configs CASCADE"))
                db.session.commit()
                print("   ✅ Таблица vpn_configs удалена")
            else:
                print("   ℹ️  Таблица vpn_configs не существует")

            print("\n" + "="*50)
            print("✅ Миграция успешно выполнена!")
            print("="*50)
            print("\n📊 Изменения:")
            print("   ✅ Создана таблица connection_logs")
            print("   ✅ Добавлена колонка deleted_at")
            print("   ✅ Удалены устаревшие колонки из users")
            print("   ✅ Обновлена таблица payments")
            print("   ✅ Созданы индексы")
            print("   ✅ Удалена таблица vpn_configs")

        except Exception as e:
            print(f"\n❌ Ошибка при выполнении миграции: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

    return True


if __name__ == '__main__':
    success = migrate_normalize_database()
    sys.exit(0 if success else 1)
