# Инструкция по развёртыванию платёжной системы

## 📋 Изменения

Теперь доступ к ключам VPN доступен **только после оплаты тарифа**.

---

## 🚀 Развёртывание на сервере

### Шаг 1: Скопируйте файлы на сервер

```bash
# С локальной машины
scp backend/templates/miniapp.html \
    backend/services/vpn_service.py \
    backend/check_expirations.py \
    bot/main.py \
    root@23.134.216.190:/opt/vpvks/

# Копирование в правильные директории
ssh root@23.134.216.190
cd /opt/vpvks

# Перемещение файлов
cp miniapp.html backend/templates/
cp vpn_service.py backend/services/
cp check_expirations.py backend/
cp main.py bot/
```

### Шаг 2: Перезапустите сервисы

```bash
# Перезапуск backend
docker compose restart backend

# Перезапуск bot
docker compose restart bot
```

### Шаг 3: Проверка работы

```bash
# Проверка логов backend
docker compose logs backend --tail 30

# Проверка логов bot
docker compose logs bot --tail 30
```

---

## 🔧 Настройка YooKassa Webhook

**Критично важно!** Без webhook платежи не будут активировать подписки.

### 1. Зайдите в личный кабинет YooKassa

URL: https://yookassa.ru/my/settings/notifications

### 2. Добавьте webhook URL

```
https://vpvks.ru/api/payment/webhook
```

### 3. Сохраните Secret Key

Убедитесь что в `.env` указан правильный ключ:

```bash
cat /opt/vpvks/.env | grep YOOKASSA
```

**Ожидаемый результат:**
```
YOOKASSA_SHOP_ID=1266298
YOOKASSA_SECRET_KEY=live_...
YOOKASSA_TEST_MODE=false
YOOKASSA_RETURN_URL=https://vpvks.ru/payment-success
```

---

## 🧪 Тестирование

### 1. Проверка блокировки ключей (без оплаты)

```bash
# Откройте бота @relatevpnbot
# Нажмите /start
# Откройте Mini App
# Перейдите в раздел "Ключи"

# Ожидаемый результат:
# ⚠️ Сообщение: "Доступ к ключам доступен только после оплаты тарифа"
# Переключение на экран тарифов
```

### 2. Тест оплаты

```bash
# В Mini App выберите тариф
# Оплатите через YooKassa

# Ожидаемый результат:
# ✅ Webhook получен
# ✅ Подписка активирована
# ✅ Ключи доступны
```

### 3. Проверка webhook в логах

```bash
# После оплаты проверьте логи
docker compose logs backend | grep "YooKassa webhook"

# Ожидаемый результат:
# Received YooKassa webhook: {...}
# Payment ... succeeded
# Activating subscription for user ...
```

---

## 📊 Как теперь работает система

```
┌─────────────────┐
│ Новый пользователь │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Нет подписки   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Ключи недоступны │ ←─── Переключение на экран тарифов
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Оплата тарифа  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Webhook YooKassa│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Подписка активна│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Ключи доступны │
└─────────────────┘
```

---

## 🔍 Troubleshooting

### Ключи всё ещё доступны без оплаты

1. Проверьте что файл обновлён:
```bash
grep "checkSubscriptionAndShowKeys" /opt/vpvks/backend/templates/miniapp.html
```

2. Перезапустите backend:
```bash
docker compose restart backend
```

3. Очистите кэш браузера в Mini App

### Webhook не приходит

1. Проверьте доступность URL:
```bash
curl -I https://vpvks.ru/api/payment/webhook
```

2. Проверьте nginx:
```bash
nginx -t
systemctl reload nginx
```

3. Проверьте что webhook настроен в YooKassa

### Ошибка "Подписка не активна" после оплаты

1. Проверьте логи webhook:
```bash
docker compose logs backend | grep "Activating subscription"
```

2. Проверьте статус платежа:
```bash
docker compose logs backend | grep "payment.succeeded"
```

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker compose logs backend --tail 100`
2. Проверьте БД: `docker exec vpn_postgres psql -U vpn_bot_user -d vpn_bot_db`
3. Перезапустите сервисы: `docker compose restart`

---

*Инструкция обновлена: 1 марта 2026 г.*
