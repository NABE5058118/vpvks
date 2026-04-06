#!/usr/bin/env python3
"""
Скрипт для автоматической очистки старых connection logs
Запускается ежедневно через cron job в Docker

Usage:
    python scripts/cleanup_logs.py [days]

Arguments:
    days - количество дней для хранения логов (по умолчанию 30)
"""

import os
import sys
from datetime import datetime, timedelta

# Добавляем путь к backend
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем Flask app для context
from server import app
from database.models.connection_log_model import ConnectionLog
from database.db_config import db

def cleanup_old_logs(days=30):
    """
    Удаление старых connection logs

    :param days: Хранить логи за последние N дней
    :return: Количество удалённых записей
    """
    print("=" * 60)
    print(f"🗑️  Очистка connection logs старше {days} дней")
    print("=" * 60)

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Считаем количество записей до очистки
        total_before = ConnectionLog.query.count()
        print(f"\n📊 Записей до очистки: {total_before}")

        # Удаляем пакетами по 1000 записей для избежания блокировок
        deleted_count = 0
        batch_size = 1000

        while True:
            # Находим старые записи
            old_logs = ConnectionLog.query.filter(
                ConnectionLog.timestamp < cutoff_date
            ).limit(batch_size).all()

            if not old_logs:
                break

            # Удаляем пакет
            for log in old_logs:
                db.session.delete(log)

            db.session.commit()
            deleted_count += len(old_logs)

            if len(old_logs) < batch_size:
                break

        # Считаем количество записей после очистки
        total_after = ConnectionLog.query.count()
        print(f"📊 Записей после очистки: {total_after}")
        print(f"✅ Удалено записей: {deleted_count}")

        print("\n" + "=" * 60)
        print("🎉 Очистка завершена успешно")
        print("=" * 60)

        return deleted_count

    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Ошибка при очистке: {e}")
        import traceback
        traceback.print_exc()
        return -1


if __name__ == '__main__':
    # Получаем количество дней из аргументов командной строки
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    # Запуск в Flask application context
    with app.app_context():
        result = cleanup_old_logs(days)

    # Выходим с кодом ошибки если что-то пошло не так
    sys.exit(0 if result >= 0 else 1)
