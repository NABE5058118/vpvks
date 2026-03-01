# Инструкция по настройке webhook YooKassa

## 🔴 Критично важно!

Без настройки webhook платежи не будут активировать подписки!

---

## Шаг 1: Зайдите в личный кабинет YooKassa

URL: https://yookassa.ru/my/

---

## Шаг 2: Перейдите в настройки уведомлений

1. Нажмите на ваш магазин (1266298)
2. Выберите **"Настройки"** → **"Уведомления"**
3. Или прямой URL: `https://yookassa.ru/my/settings/notifications`

---

## Шаг 3: Добавьте webhook URL

**URL для уведомлений:**
```
https://vpvks.ru/api/payment/webhook
```

**Что нужно сделать:**
1. Вставьте URL в поле "URL для уведомлений"
2. Нажмите "Сохранить"
3. Скопируйте **Secret Key** (ключ уведомления)

---

## Шаг 4: Проверка webhook

YooKassa отправит тестовый запрос для проверки.

**В логах должно появиться:**
```bash
docker compose logs backend | grep webhook
```

---

## Шаг 5: Проверка на сервере

```bash
# Проверка текущего .env
ssh root@23.134.216.190
cd /opt/vpvks
cat .env | grep YOOKASSA
```

**Ожидаемый результат:**
```
YOOKASSA_SHOP_ID=1266298
YOOKASSA_SECRET_KEY=live_...
YOOKASSA_TEST_MODE=false
YOOKASSA_RETURN_URL=https://vpvks.ru/payment-success
```

---

## Шаг 6: Тестовый платёж

```bash
# Создайте тестовый платёж
curl -X POST https://vpvks.ru/api/payment/create \
  -H "Content-Type: application/json" \
  -d '{"user_id": 699469085, "plan_type": "month"}'
```

**Ожидаемый ответ:**
```json
{
  "status": "success",
  "payment": {
    "id": "...",
    "confirmation_url": "https://yookassa.ru/..."
  }
}
```

---

## Шаг 7: Проверка webhook в логах

После оплаты проверьте:

```bash
# Логи backend
docker compose logs backend | grep "YooKassa webhook"

# Логи должны показать:
# Received YooKassa webhook: {...}
# Payment ... succeeded
# Activating subscription for user ...
```

---

## 🔧 Troubleshooting

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

3. Проверьте backend:
```bash
docker compose ps backend
docker compose logs backend
```

### Ошибка "Payment not found"

Webhook приходит до того, как платёж создан в БД. Это нормально — YooKassa отправит повторный webhook.

---

## 📞 Поддержка YooKassa

Техническая поддержка: support@yookassa.ru
Документация: https://yookassa.ru/developers/api

---

*Инструкция обновлена: 1 марта 2026 г.*
