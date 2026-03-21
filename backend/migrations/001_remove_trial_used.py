#!/usr/bin/env python3
"""Миграция: удаление колонки trial_used"""

import sys
import os

sys.path.insert(0, '/app')

from server import app
from database.db_config import db
from sqlalchemy import text


def migrate_remove_trial():
    print("🔄 Удаление колонки trial_used...")

    with app.app_context():
        try:
            # Проверяем существует ли колонка
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('users')]

            if 'trial_used' in columns:
                print("📝 Удаление колонки trial_used из таблицы users...")
                db.session.execute(text("ALTER TABLE users DROP COLUMN trial_used"))
                db.session.commit()
                print("✅ Колонка trial_used успешно удалена")
            else:
                print("ℹ️  Колонка trial_used уже отсутствует")

            print("\n" + "="*50)
            print("✅ Миграция успешно выполнена!")
            print("="*50)

        except Exception as e:
            print(f"\n❌ Ошибка при выполнении миграции: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False

    return True


if __name__ == '__main__':
    success = migrate_remove_trial()
    sys.exit(0 if success else 1)
