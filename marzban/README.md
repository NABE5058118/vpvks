# Marzban Setup

## Установка на сервере

### 1. Создать директорию и файлы

```bash
mkdir -p /opt/marzban
cd /opt/marzban
```

### 2. Создать .env файл

```bash
nano .env
```

Вставить:

```env
# Database
POSTGRES_DB=marzban
POSTGRES_USER=marzban
POSTGRES_PASSWORD=MarzbanPass123!
DATABASE_URL=postgresql://marzban:MarzbanPass123!@localhost:5432/marzban

# Security (сгенерируй свою: openssl rand -hex 32)
SECRET_KEY=7c1ac2b949198c0d8ac414776fd11b6beac83fb0a86acc9f1859c05384b717b5

# Subscription
SUBSCRIPTION_URL_PREFIX=https://vpvks.ru

# UVICORN workers
UVICORN_WORKERS=2
```

### 3. Запустить Marzban

```bash
# Запусти контейнеры
docker compose up -d

# Проверь статус
docker compose ps

# Посмотри логи
docker compose logs -f marzban
```

## Доступ к панели

После установки открой в браузере:

```
https://vpvks.ru:8000
```

Логин/пароль администратора создаётся при первом запуске (смотри логи).

## Команды управления

```bash
# Перезапуск
docker compose restart

# Остановка
docker compose down

# Обновление
docker compose pull
docker compose up -d

# Логи
docker compose logs -f marzban
```

## Интеграция с Telegram ботом

После настройки Marzban нужно обновить бота для поддержки V2Ray/Trojan.
