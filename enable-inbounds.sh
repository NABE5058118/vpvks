#!/bin/bash
# Скрипт для включения VLESS Reality и Trojan TLS в Marzban
# Запускается ОДИН РАЗ после установки

echo "🔧 Marzban Inbound Auto-Enabler"
echo "================================"

# Проверяем существует ли конфиг
if [ ! -f /var/lib/marzban/xray_config.json ]; then
    echo "❌ Файл конфигурации не найден!"
    exit 1
fi

echo "✓ Конфигурация найдена"

# Проверяем есть ли VLESS Reality в конфиге
if grep -q "VLESS Reality" /var/lib/marzban/xray_config.json; then
    echo "✓ VLESS Reality найден в конфигурации"
else
    echo "❌ VLESS Reality не найден!"
    exit 1
fi

# Проверяем есть ли Trojan TLS в конфиге
if grep -q "Trojan TLS" /var/lib/marzban/xray_config.json; then
    echo "✓ Trojan TLS найден в конфигурации"
else
    echo "❌ Trojan TLS не найден!"
    exit 1
fi

echo ""
echo "⚠️  ВНИМАНИЕ: Marzban требует ручного включения inbound через Dashboard"
echo ""
echo "📋 Инструкция:"
echo "   1. Открой https://marzban.vpvks.ru/dashboard/"
echo "   2. Логин: admin"
echo "   3. Пароль: j8X0EcIllDwPK"
echo "   4. Settings → Inbounds"
echo "   5. Включи VLESS Reality ✓"
echo "   6. Включи Trojan TLS ✓"
echo "   7. Save"
echo ""
echo "✅ После этого все новые пользователи смогут подключаться!"
echo ""

# Перезапускаем Marzban чтобы применить конфиг
echo "🔄 Перезапуск Marzban..."
cd /opt/vpvks
docker compose restart marzban

echo ""
echo "✅ Готово! Теперь включи inbound в Dashboard (см. инструкцию выше)"
