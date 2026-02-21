# 🔐 VPN Bot Project — Полное руководство (vpvks.ru)

> **Последнее обновление:** 21 февраля 2026 г.  
> **Статус:** ✅ Все сервисы работают  
> **Сервер:** 23.134.216.190 (Ubuntu 24.04.4 LTS)  
> **Домен:** vpvks.ru (SSL: Let's Encrypt)

---

## 📋 Содержание

1. [О проекте](#-о-проекте)
2. [Архитектура](#-архитектура)
3. [Быстрый старт](#-быстрый-старт)
4. [Настройка Marzban — подводные камни](#-настройка-marzban--подводные-камни)
5. [Конфигурация](#-конфигурация)
6. [Команды управления](#-команды-управления)
7. [Доступ к панелям](#-доступ-к-панелям)
8. [Troubleshooting](#-troubleshooting)
9. [Безопасность](#-безопасность)

---

## 📖 О проекте

Telegram-бот для управления VPN-подключениями с мини-приложением, системой оплаты и поддержкой двух протоколов:

| Протокол | Описание |
|----------|----------|
| **WireGuard** | Классический VPN, высокая скорость |
| **V2Ray/Trojan/Reality** | Через Marzban, для обхода блокировок |

### Возможности

- ✅ Telegram Mini App (Web App)
- ✅ YooKassa интеграция (продакшен)
- ✅ Автоматическая выдача подписок
- ✅ Мониторинг трафика
- ✅ Мультипротокольность

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                        nginx:443 (SSL)                          │
│                    reverse proxy для всех сервисов               │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Backend:8080  │   │ Marzban:8000  │   │WireGuard:51820│
│ (Flask API)   │   │ (V2Ray/Xray)  │   │ (UDP)         │
└───────┬───────┘   └───────┬───────┘   └───────────────┘
        │                   │
        ▼                   ▼
┌───────────────┐   ┌───────────────┐
│ PgBouncer:6432│   │   SQLite      │
│ (pooler)      │   │   db.sqlite3  │
└───────┬───────┘   └───────────────┘
        │
        ▼
┌───────────────┐
│ PostgreSQL:5432│
│ (Docker)      │
└───────────────┘
```

### Распределение баз данных

| Компонент | БД | Расположение |
|-----------|-----|--------------|
| Telegram бот | PostgreSQL 17 | Docker `vpn_postgres` |
| Backend (Flask) | PostgreSQL | Через PgBouncer |
| **Marzban** | **SQLite** | `/var/lib/marzban/db.sqlite3` |
| WireGuard | Нет | Конфиги в `/etc/wireguard/` |

### Структура проекта

```
/opt/vpvks/
├── docker-compose.yml          # Оркестрация всех сервисов
├── .env                        # Переменные окружения (секреты)
├── marzban.env                 # Переменные для Marzban
│
├── backend/                    # Flask API сервер
│   ├── server.py
│   ├── routes/
│   ├── models/
│   └── templates/miniapp.html
│
├── bot/                        # Telegram бот
│   ├── main.py
│   └── handlers/
│
├── pgbouncer/                  # PgBouncer конфиг
│   └── pgbouncer.ini
│
└── marzban/                    # Marzban (локальная копия)
    └── docker-compose.yml
```

---

## 🚀 Быстрый старт

### 1. Подготовка сервера

```bash
# Обновление системы
apt update && apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com | sh

# Установка Docker Compose
apt install docker-compose-plugin -y

# Клонирование репозитория
cd /opt
git clone https://github.com/NABE5058118/vpvks.git
cd vpvks
```

### 2. Настройка переменных окружения

```bash
# Скопируйте примеры
cp .env.example .env
cp marzban.env.example marzban.env

# Отредактируйте под свои значения
nano .env
nano marzban.env
```

### 3. Запуск всех сервисов

```bash
cd /opt/vpvks
docker compose up -d
```

### 4. Проверка статуса

```bash
docker compose ps
```

**Ожидаемый результат:**
```
NAME            STATUS
vpn_bot         Up
vpn_backend     Up
vpn_pgbouncer   Up
vpn_postgres    Up (healthy)
marzban         Up
```

---

## ⚠️ Настройка Marzban — Подводные камни

### Проблема 1: База данных (PostgreSQL → SQLite)

**Симптомы:**
```
sqlalchemy.exc.OperationalError: could not translate host name "marzban-db" to address
```

**Причина:** Marzban не может подключиться к PostgreSQL при миграции Alembic.

**Решение — использовать SQLite:**

```yaml
# docker-compose.yml
marzban:
  environment:
    - SQLALCHEMY_DATABASE_URL=sqlite:////var/lib/marzban/db.sqlite3
  network_mode: host  # Важно!
```

```env
# marzban.env
# DATABASE_URL не требуется для SQLite
SECRET_KEY=your_secret_key
UVICORN_WORKERS=2
```

---

### Проблема 2: UVICORN_HOST не работает

**Симптомы:**
```
INFO: Uvicorn running on http://127.0.0.1:8000
```

Marzban слушает только localhost внутри контейнера, nginx не может подключиться.

**Решение:**

```yaml
marzban:
  network_mode: host  # Обязательно!
  # Убрать networks: и ports:
```

**Преимущества:**
- Marzban слушает напрямую на хосте
- Не нужен Docker proxy
- Прямой доступ к порту 8000

---

### Проблема 3: Nginx возвращает 502 Bad Gateway

**Симптомы:**
- `502 Bad Gateway` при доступе к `marzban.vpvks.ru`
- Или страница загружается, но **неоновая анимация крутится бесконечно**

**Причины:**
1. Порт 80 занят основным nginx
2. Неправильный `proxy_pass`
3. Нет WebSocket поддержки
4. Неправильные пути к статике (`/statics/`, `/dashboard/`)

**Решение — полный nginx конфиг:**

```nginx
server {
    listen 443 ssl http2;
    server_name marzban.vpvks.ru;
    
    ssl_certificate /etc/letsencrypt/live/marzban.vpvks.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/marzban.vpvks.ru/privkey.pem;

    # Dashboard
    location /dashboard/ {
        proxy_pass http://127.0.0.1:8000/dashboard/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # Статика (JS/CSS)
    location /statics/ {
        proxy_pass http://127.0.0.1:8000/statics/;
        proxy_set_header Host $host;
    }

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
    }

    # Основное (WebSocket)
    location / {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
```

```bash
nginx -t && nginx -s reload
```

---

### Проблема 4: Нет админа в базе

**Симптомы:**
- Страница логина загружается
- Войти невозможно — админ не создан

**Проверка:**
```bash
docker exec marzban python -c 'import sqlite3; c=sqlite3.connect("/var/lib/marzban/db.sqlite3"); print("Админы:", c.execute("SELECT username FROM admins").fetchall())'
```

**Решение — создать админа:**

```bash
cat > /tmp/create_admin.py << 'EOF'
import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hash = pwd_context.hash("j8X0EcIllDwPK")

conn = sqlite3.connect('/var/lib/marzban/db.sqlite3')
c = conn.cursor()

c.execute('''
    INSERT INTO admins (username, hashed_password, is_sudo, created_at)
    VALUES (?, ?, 1, datetime('now'))
''', ('admin', password_hash))

conn.commit()
print('Админ создан!')
conn.close()
EOF

docker cp /tmp/create_admin.py marzban:/tmp/create_admin.py
docker exec marzban python /tmp/create_admin.py
```

---

## ⚙️ Конфигурация

### .env (основной)

```env
# PostgreSQL
POSTGRES_DB=vpn_bot_db
POSTGRES_USER=vpn_bot_user
POSTGRES_PASSWORD=vp62RofV5h
PGDATA=/var/lib/postgresql/data

# PgBouncer
DATABASE_URL=postgresql://vpn_bot_user:vp62RofV5h@postgres:5432/vpn_bot_db
POOL_MODE=transaction
MAX_CLIENT_CONN=1000
DEFAULT_POOL_SIZE=50
AUTH_TYPE=scram-sha-256

# Backend
SECRET_KEY=5n_IX5ODiFJcuR0ZDH5s1cCRRAQYZcOiHYn4ZQ5xjEc
PORT=8080

# YooKassa
YOOKASSA_SHOP_ID=1266298
YOOKASSA_SECRET_KEY=live_xxx
YOOKASSA_TEST_MODE=false
YOOKASSA_RETURN_URL=https://vpvks.ru/payment-success

# WireGuard
WG_SERVER_IP=10.0.0.1
WG_PORT=51820
WG_SERVER_PUBLIC_KEY=xxx

# Bot
TELEGRAM_BOT_TOKEN=xxx
BACKEND_URL=https://vpvks.ru
ADMIN_USER_IDS=699469085
```

### marzban.env

```env
SECRET_KEY=7c1ac2b949198c0d8ac414776fd11b6beac83fb0a86acc9f1859c05384b717b5
UVICORN_WORKERS=2
XRAY_JSON=/var/lib/marzban/xray_config.json
SUDO_USERNAME=admin
SUDO_PASSWORD=j8X0EcIllDwPK
SUBSCRIPTION_URL_PREFIX=https://vpvks.ru
```

### docker-compose.yml (фрагмент Marzban)

```yaml
marzban:
  build:
    context: .
    dockerfile: Dockerfile.marzban
  container_name: marzban
  restart: always
  env_file:
    - marzban.env
  environment:
    - SQLALCHEMY_DATABASE_URL=sqlite:////var/lib/marzban/db.sqlite3
    - XRAY_JSON=/var/lib/marzban/xray_config.json
  network_mode: host
  volumes:
    - /var/lib/marzban:/var/lib/marzban
    - /etc/letsencrypt:/etc/letsencrypt:ro
```

---

## 🎛️ Команды управления

### Запуск / остановка

```bash
# Все сервисы
docker compose up -d
docker compose down

# Отдельный сервис
docker compose up -d marzban
docker compose stop marzban
```

### Статус и логи

```bash
# Статус всех
docker compose ps

# Статус Marzban
docker compose ps marzban
docker compose logs marzban | tail -30

# Логи в реальном времени
docker compose logs -f
docker compose logs -f marzban
```

### Перезапуск / обновление

```bash
# Перезапуск
docker compose restart
docker compose restart marzban

# Обновление образов
docker compose pull
docker compose up -d --force-recreate
```

### Проверка БД Marzban

```bash
# Таблицы
docker exec marzban python -c 'import sqlite3; c=sqlite3.connect("/var/lib/marzban/db.sqlite3"); print("Таблицы:", [t[0] for t in c.execute("SELECT name FROM sqlite_master WHERE type=\"table\"")])'

# Админы
docker exec marzban python -c 'import sqlite3; c=sqlite3.connect("/var/lib/marzban/db.sqlite3"); print("Админы:", c.execute("SELECT username FROM admins").fetchall())'
```

### Nginx

```bash
# Проверка конфига
nginx -t

# Перезагрузка
nginx -s reload

# Логи
tail -f /var/log/nginx/error.log
```

---

## 🌐 Доступ к панелям

### Marzban Panel

| Параметр | Значение |
|----------|----------|
| **URL** | `https://marzban.vpvks.ru/dashboard/` |
| **Логин** | `admin` |
| **Пароль** | `j8X0EcIllDwPK` |

**Через SSH туннель:**
```bash
ssh -L 8000:localhost:8000 root@23.134.216.190
# Затем: http://127.0.0.1:8000/dashboard/
```

### Telegram Bot

| Параметр | Значение |
|----------|----------|
| **Бот** | [@relatevpnbot](https://t.me/relatevpnbot) |
| **Команды** | `/start`, `/app`, `/status`, `/connect` |

### Mini App

| Параметр | Значение |
|----------|----------|
| **URL** | `https://vpvks.ru/miniapp` |
| **Доступ** | Через бота командой `/app` |

---

## 🔧 Troubleshooting

### Marzban не запускается

```bash
# Проверь логи
docker compose logs marzban | tail -50

# Проверь переменные
docker exec marzban env | grep -i "database\|uvicorn"

# Проверь БД
ls -la /var/lib/marzban/db.sqlite3
```

### 502 Bad Gateway

```bash
# Слушает ли Marzban
ss -tulpn | grep 8000

# Проверь nginx
nginx -t
tail -f /var/log/nginx/error.log | grep marzban
```

### Неоновая анимация крутится

1. Открой **F12 → Console** — проверь ошибки JavaScript
2. Открой **F12 → Network** — проверь запросы к `/api/` и `/statics/`
3. Очисти кэш: **Cmd+Shift+R** (Mac) или **Ctrl+Shift+R** (Windows)

```bash
# Проверь nginx конфиг
nginx -t && nginx -s reload
```

### Backend не подключается к БД

```bash
# Проверь DATABASE_URL
cat /opt/vpvks/.env | grep DATABASE_URL
# Должно быть: @postgres:5432 (не @pgbouncer!)

# Перезапусти
docker compose restart backend pgbouncer postgres
```

### WireGuard не работает

```bash
# Статус
sudo wg show

# Порт
sudo ss -tulpn | grep 51820

# Перезапуск
sudo systemctl restart wg-quick@wg0
```

---

## 🔒 Безопасность

### Критичные файлы

| Файл | Секреты |
|------|---------|
| `.env` | ✅ Пароли БД, токены |
| `marzban.env` | ✅ SECRET_KEY, пароль админа |
| `/etc/wireguard/*` | ✅ Приватные ключи |
| `/etc/letsencrypt/*` | ✅ SSL сертификаты |
| `/var/lib/marzban/db.sqlite3` | ✅ БД Marzban |

### Рекомендации

1. **Не коммитьте `.env` в git** — используйте `.env.example`
2. **Смените пароли по умолчанию** — особенно для админа Marzban
3. **Настройте firewall**:
   ```bash
   ufw allow 22/tcp    # SSH
   ufw allow 80/tcp    # HTTP
   ufw allow 443/tcp   # HTTPS
   ufw allow 51820/udp # WireGuard
   ufw enable
   ```
4. **Регулярно обновляйтесь**:
   ```bash
   apt update && apt upgrade -y
   docker compose pull
   docker compose up -d
   ```

---

## 📊 Порты сервисов

| Сервис | Порт | Протокол | Доступ |
|--------|------|----------|--------|
| nginx | 80, 443 | TCP | Внешний |
| Backend | 8080 | TCP | localhost |
| Marzban | 8000 | TCP | localhost |
| PgBouncer | 6432 | TCP | Внешний |
| WireGuard | 51820 | UDP | Внешний |
| PostgreSQL | 5432 | TCP | Docker network |

---

## 📞 Контакты

| Параметр | Значение |
|----------|----------|
| **Сервер** | 23.134.216.190 |
| **Домен** | vpvks.ru |
| **Бот** | @relatevpnbot |
| **Admin ID** | 699469085 |
| **Пользователь** | `vpvks` (без права логина) |

---

## 📚 История изменений

### 21 февраля 2026
- ✅ Marzban настроен с SQLite (решены проблемы с миграцией)
- ✅ Nginx настроен для проксирования dashboard/statics/api
- ✅ Админ создан в БД
- ✅ Все сервисы работают

### 19-20 февраля 2026
- ✅ Сервер развёрнут
- ✅ SSL настроен (Let's Encrypt)
- ✅ VPN Bot + Mini App работают
- ✅ YooKassa интегрирована
- ✅ WireGuard настроен

---

*Документ обновлён: 21 февраля 2026 г.*
