# Инструкция по развёртыванию исправлений уведомлений

## 📋 Изменения

Исправлены критические проблемы в системе уведомлений об истечении подписки:

1. **Исправлен расчёт days_left** — теперь корректно обрабатываются просроченные подписки
2. **Добавлена защита от дублей** — уведомления не отправляются повторно в тот же день
3. **Добавлено уведомление за 2 дня** — теперь уведомления отправляются за 3, 2, 1 дня и в день истечения
4. **Улучшено логирование** — статистика: всего пользователей/отправлено/пропущено

---

## 🚀 Развёртывание

### Шаг 1: Скопируйте файлы на сервер

```bash
# На локальной машине
scp -r bot/notifications.py root@23.134.216.190:/opt/vpvks/bot/
scp -r backend/database/models/user_model.py root@23.134.216.190:/opt/vpvks/backend/database/models/
scp -r backend/migrate_add_expiration_reminder_field.py root@23.134.216.190:/opt/vpvks/backend/
scp -r backend/tests/test_notifications.py root@23.134.216.190:/opt/vpvks/backend/tests/
```

### Шаг 2: Выполните миграцию БД

```bash
# На сервере
ssh root@23.134.216.190
cd /opt/vpvks

# Запустить миграцию
docker exec vpn_backend python /opt/vpvks/backend/migrate_add_expiration_reminder_field.py
```

**Ожидаемый результат:**
```
🔄 Начало миграции: добавление поля last_expiration_reminder_sent...
📝 Добавление колонки last_expiration_reminder_sent (DATE, NULL)...
✅ Миграция успешно выполнена!
```

### Шаг 3: Перезапустите бота

```bash
# На сервере
cd /opt/vpvks
docker compose restart vpn_bot
```

### Шаг 4: Проверьте логи

```bash
# Через 10 секунд после перезапуска
docker compose logs vpn_bot --tail 30
```

**Ожидаемый результат:**
```
✅ JobQueue настроен: уведомления об истечении в 10:00
✅ JobQueue настроен: синхронизация Marzban каждые 5 минут
```

### Шаг 5: Проверьте работу уведомлений

Дождитесь 10:00 утра или протестируйте вручную:

```bash
# Тестирование (опционально)
docker exec vpn_bot python /opt/vpvks/backend/tests/test_notifications.py
```

---

## 🧪 Тестирование

### Сценарий 1: Пользователь с подпиской на 3 дня

```
Ожидаемое поведение:
- Уведомление отправляется
- Текст: "Ваша подписка истекает через 3 дня!"
- Поле last_expiration_reminder_sent обновляется на сегодня
```

### Сценарий 2: Пользователь с подпиской на 2 дня

```
Ожидаемое поведение:
- Уведомление отправляется
- Текст: "Ваша подписка истекает через 2 дня!"
- Поле last_expiration_reminder_sent обновляется на сегодня
```

### Сценарий 3: Пользователь с подпиской на 1 день

```
Ожидаемое поведение:
- Уведомление отправляется
- Текст: "Ваша подписка истекает завтра!"
- Поле last_expiration_reminder_sent обновляется на сегодня
```

### Сценарий 4: Пользователь с подпиской, истекающей сегодня

```
Ожидаемое поведение:
- Уведомление отправляется
- Текст: "Ваша подписка истекла сегодня"
- Поле last_expiration_reminder_sent обновляется на сегодня
```

### Сценарий 5: Пользователь с просроченной подпиской

```
Ожидаемое поведение:
- Уведомление НЕ отправляется (days_left = 0, но уже истекло)
```

### Сценарий 6: Повторный запуск в тот же день

```
Ожидаемое поведение:
- Уведомление НЕ отправляется (защита от дублей)
- В логах: "пропущено 1"
```

---

## 📊 Мониторинг

### Проверка статистики уведомлений

```bash
# Логи бота в 10:00
docker compose logs vpn_bot | grep "Проверка завершена"
```

**Пример вывода:**
```
✅ Проверка завершена: всего 150, отправлено 12, пропущено 138
```

### Проверка поля в БД

```bash
# Подключение к БД
docker exec -it vpn_postgres psql -U vpn_bot_user -d vpn_bot_db

# Проверка пользователей с отправленными уведомлениями
SELECT id, username, subscription_end_date, last_expiration_reminder_sent 
FROM users 
WHERE last_expiration_reminder_sent IS NOT NULL 
ORDER BY last_expiration_reminder_sent DESC 
LIMIT 10;
```

---

## 🔙 Откат изменений

При необходимости отката:

### 1. Откат кода

```bash
cd /opt/vpvks
git checkout HEAD -- bot/notifications.py
git checkout HEAD -- backend/database/models/user_model.py
docker compose restart vpn_bot
```

### 2. Удаление колонки из БД (опционально)

```bash
docker exec vpn_postgres psql -U vpn_bot_user -d vpn_bot_db -c \
  "ALTER TABLE users DROP COLUMN IF EXISTS last_expiration_reminder_sent;"
```

---

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи: `docker compose logs vpn_bot --tail 100`
2. Проверьте БД: `docker exec vpn_postgres psql -U vpn_bot_user -d vpn_bot_db`
3. Перезапустите сервисы: `docker compose restart vpn_bot vpn_backend`

---

*Инструкция обновлена: 1 марта 2026 г.*
