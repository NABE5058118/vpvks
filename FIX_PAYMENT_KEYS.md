# 🔧 Исправление проблемы с оплатой и генерацией ключей

## Проблема
Пользователи оплатили подписку (запись в `payments` есть), но:
- Ключи не генерируются в боте
- QR-код не отображается
- В Marzban пользователи не созданы

## Причина
Backend не мог подключиться к Marzban API:
- Использовался неправильный URL: `host.docker.internal:8000`
- Отсутствовали переменные окружения для Marzban в `.env`
- Ошибка asyncio в bot/notifications.py

## Решение

### 1. Обновите файл `.env` на сервере

Файл уже обновлён, проверьте что присутствуют:

```bash
# Marzban (VPN Server)
MARZBAN_URL=http://marzban:8000
MARZBAN_PUBLIC_URL=https://vpvks.ru
MARZBAN_ADMIN=admin
MARZBAN_PASSWORD=j8X0EcIllDwPK
```

### 2. Перезапустите backend

```bash
cd /opt/vpvks  # или ваш путь к проекту
docker compose restart backend
```

### 3. Проверьте логи backend

```bash
docker compose logs backend --tail 100
```

Ищите строки:
- ✅ `Creating user user_XXX in Marzban`
- ✅ `Marzban user created`
- ❌ `Error getting Marzban token` (если есть — проблема с подключением)

### 4. Запустите скрипт синхронизации

Скрипт найдёт всех пользователей с успешными платежами и создаст их в Marzban:

```bash
# Внутри контейнера backend
docker compose exec backend python3 /app/scripts/sync_paid_users.py
```

Или локально (если есть доступ к БД и Marzban):

```bash
cd backend
python3 scripts/sync_paid_users.py
```

### 5. Проверьте результат

После выполнения скрипта:
- Пользователи будут созданы в Marzban
- В БД обновится `subscription_url`
- Пользователи смогут получить ключи через бота

## Проверка для конкретного пользователя

```bash
# Проверка платежа в БД
docker compose exec pgbouncer psql -U vpn_bot_user -d vpn_bot_db -c \
  "SELECT id, user_id, amount, status, paid FROM payments WHERE user_id = <USER_ID>;"

# Проверка пользователя в БД
docker compose exec pgbouncer psql -U vpn_bot_user -d vpn_bot_db -c \
  "SELECT id, username, subscription_end_date, subscription_url FROM users WHERE id = <USER_ID>;"
```

## Проверка в Marzban

```bash
# Проверка пользователя в Marzban API
curl -X GET "http://marzban:8000/api/user/user_<USER_ID>" \
  -H "Authorization: Bearer <TOKEN>"
```

Или через веб-интерфейс: `https://vpvks.ru/dashboard/users`

## Если проблема повторится

1. Проверьте что Marzban доступен из backend:
```bash
docker compose exec backend curl http://marzban:8000/
```

2. Проверьте переменные окружения:
```bash
docker compose exec backend env | grep MARZBAN
```

3. Проверьте логи Marzban:
```bash
docker compose logs marzban --tail 50
```

## Дополнительные исправления

### Исправлена ошибка asyncio в bot/notifications.py

Было:
```python
new_loop = asyncio.new_event_loop()
new_loop.run_until_complete(...)
```

Стало:
```python
new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(new_loop)
new_loop.run_until_complete(...)
```

Это предотвращает ошибку:
```
RuntimeWarning: coroutine 'send_welcome_notification' was never awaited
```
