# 🚀 СРОЧНОЕ ОБНОВЛЕНИЕ НА СЕРВЕРЕ

## 1. Обновление кода:

```bash
cd /opt/vpvks
git pull origin main
```

## 2. Миграция базы данных (ДОБАВИТЬ колонку is_tester):

```bash
docker compose exec pgbouncer psql -U vpn_bot_user -d vpn_bot_db -c "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_tester BOOLEAN DEFAULT FALSE;"
```

Или через pgAdmin/phpPgAdmin:
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_tester BOOLEAN DEFAULT FALSE;
```

## 3. Перезапуск сервисов:

```bash
docker compose restart backend bot
```

## 4. Проверка:

```bash
# Проверка логов
docker compose logs bot --tail=30
docker compose logs backend --tail=30

# Проверка БД
docker compose exec pgbouncer psql -U vpn_bot_user -d vpn_bot_db -c "SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_tester';"
```

## 5. Добавить тестировщика (админ):

В Telegram боте:
```
/tester 699469085
```

---

## Если что-то пошло не так:

```bash
# Откат к предыдущей версии
cd /opt/vpvks
git log --oneline -5
git reset --hard <commit-hash>
docker compose restart
```
