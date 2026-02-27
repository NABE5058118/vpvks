#!/bin/bash
# Скрипт для автоматического включения VLESS Reality и Trojan TLS
# Запускается ПЕРЕД стартом Marzban

echo "🔧 Enabling Marzban inbounds..."

DB_PATH="/var/lib/marzban/db.sqlite3"

if [ ! -f "$DB_PATH" ]; then
    echo "⚠️ Database not found, skipping inbound enable"
    exit 0
fi

# Включаем inbound через SQLite
sqlite3 "$DB_PATH" "UPDATE inbounds SET enabled = 1 WHERE tag IN ('VLESS Reality', 'Trojan TLS');"

echo "✅ Inbounds enabled!"

# Запускаем Marzban
exec marzban
