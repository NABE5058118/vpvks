#!/bin/bash
# Скрипт для автоматического включения VLESS Reality и Trojan TLS
# Запускается ПЕРЕД стартом Marzban

echo "🔧 Enabling Marzban inbounds..."

DB_PATH="/var/lib/marzban/db.sqlite3"

if [ ! -f "$DB_PATH" ]; then
    echo "⚠️ Database not found, skipping inbound enable"
else
    # В Marzban нет колонки enabled - inbound управляются через JSON config
    # Просто проверяем что БД существует
    echo "✅ Database exists, Marzban will manage inbounds"
fi

# Запускаем Marzban через uvicorn (стандартный способ)
cd /var/lib/marzban
exec uvicorn marzban:app --host 0.0.0.0 --port 8000 --loop uvloop
