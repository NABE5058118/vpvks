#!/usr/bin/env python3
"""
Миграция: Исправление foreign key constraint для CASCADE DELETE
Запуск: docker exec vpn_backend python /app/migrate_fix_payments_foreign_key.py
"""

import sys
import os

# Добавляем путь к приложению
sys.path.insert(0, '/app')

from server import app
from database.db_config import db
from sqlalchemy import text

def fix_payments_foreign_key():
    """Исправление FK constraints для payments.user_id"""
    
    print("🔄 Начало миграции: исправление foreign key constraint...")
    
    with app.app_context():
        try:
            with db.engine.connect() as conn:
                # Получаем имя текущего constraint
                print("📝 Проверка текущего foreign key constraint...")
                result = conn.execute(text("""
                    SELECT conname
                    FROM pg_constraint
                    WHERE conrelid = 'payments'::regclass
                    AND confrelid = 'users'::regclass
                    AND contype = 'f'
                """))
                row = result.fetchone()
                
                if row:
                    constraint_name = row[0]
                    print(f"ℹ️  Найден constraint: {constraint_name}")
                    
                    # Проверяем есть ли уже ON DELETE CASCADE
                    check_result = conn.execute(text(f"""
                        SELECT confdeltype
                        FROM pg_constraint
                        WHERE conname = '{constraint_name}'
                    """))
                    check_row = check_result.fetchone()
                    
                    # confdeltype: 'a' = NO ACTION, 'r' = RESTRICT, 'c' = CASCADE, 'n' = SET NULL, 'd' = SET DEFAULT
                    if check_row and check_row[0] == 'c':
                        print("✅ CASCADE уже настроен, миграция не требуется")
                        return True
                    
                    # Удаляем старый constraint
                    print(f"📝 Удаление старого constraint: {constraint_name}...")
                    conn.execute(text(f"ALTER TABLE payments DROP CONSTRAINT {constraint_name}"))
                    conn.commit()
                    print("✅ Старый constraint удалён")
                    
                    # Добавляем новый constraint с CASCADE
                    print("📝 Добавление нового constraint с ON DELETE CASCADE...")
                    conn.execute(text("""
                        ALTER TABLE payments
                        ADD CONSTRAINT payments_user_id_fkey
                        FOREIGN KEY (user_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE
                    """))
                    conn.commit()
                    print("✅ Новый constraint добавлен")
                else:
                    print("⚠️  Foreign key constraint не найден, создаём новый...")
                    conn.execute(text("""
                        ALTER TABLE payments
                        ADD CONSTRAINT payments_user_id_fkey
                        FOREIGN KEY (user_id)
                        REFERENCES users(id)
                        ON DELETE CASCADE
                    """))
                    conn.commit()
                    print("✅ Constraint создан")
            
            print("\n✅ Миграция успешно выполнена!")
            print("\n📊 Теперь при удалении пользователя:")
            print("   - Все его платежи будут автоматически удалены (CASCADE)")
            print("   - Ошибка foreign key constraint больше не появится")
            print("\n💡 Также доступен API endpoint: DELETE /api/users/<user_id>")
            print("   Он сначала удаляет платежи, потом пользователя")
            
        except Exception as e:
            print(f"❌ Ошибка при выполнении миграции: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


if __name__ == '__main__':
    success = fix_payments_foreign_key()
    sys.exit(0 if success else 1)
