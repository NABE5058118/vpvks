# 📦 VPN Bot Project - Финальная конфигурация

## 🏗️ Архитектура

```
┌─────────────────┐
│   nginx:443     │ HTTPS (SSL Let's Encrypt)
└────────┬────────┘
         │
         ├──────────────────┬──────────────────┬─────────────────┐
         ▼                  ▼                  ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Backend:8080   │ │  Marzban:8000   │ │  PgBouncer:6432 │ │  WireGuard:51820│
│  (Flask API)    │ │  (V2Ray/Trojan) │ │  (Pooler)       │ │  (UDP)          │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘ └─────────────────┘
         │                   │                   │
         ▼                   │                   ▼
┌─────────────────┐          │          ┌─────────────────┐
│  PostgreSQL:5432│          │          │  PostgreSQL:5432│
│  (VPN Bot)      │          │          │  (Docker)       │
└─────────────────┘          │          └─────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  SQLite         │
                    │  db.sqlite3     │
                    └─────────────────┘
```

## 📁 Структура проекта

```
/opt/vpvks/
├── docker-compose.yml       # Основная конфигурация Docker
├── .env                     # Переменные окружения (секреты)
├── marzban.env              # Переменные для Marzban (секреты)
├── backend/                 # Flask API сервер
├── bot/                     # Telegram бот
├── pgbouncer/               # Конфигурация PgBouncer
└── marzban/                 # Marzban конфиги (локальная копия)
    ├── docker-compose.yml
    ├── .env.example
    └── README.md
```

## 🚀 Быстрый старт

### 1. Запуск всех сервисов

```bash
cd /opt/vpvks
sudo -u vpvks docker compose up -d
```

### 2. Проверка статуса

```bash
sudo -u vpvks docker compose ps
```

Ожидаемый результат:
```
NAME                 STATUS
vpn_bot              Up
vpn_backend          Up
vpn_pgbouncer        Up
vpn_postgres         Up (healthy)
marzban              Up
```

### 3. Просмотр логов

```bash
# Все логи
sudo -u vpvks docker compose logs -f

# Только backend
sudo -u vpvks docker compose logs -f backend

# Только Marzban
sudo -u vpvks docker compose logs -f marzban
```

## 🔐 Доступ к панелям

### Marzban Panel

**URL:** `https://marzban.vpvks.ru`

**Логин:** `admin`  
**Пароль:** `j8X0EcIllDwPK`

**Через SSH туннель:**
```bash
ssh -L 8000:localhost:8000 root@23.134.216.190
```
Затем открой `http://127.0.0.1:8000`

### Telegram Bot

**Бот:** @relatevpnbot  
**Команды:** `/start`, `/app`, `/status`, `/connect`, `/disconnect`

### Mini App

**URL:** `https://vpvks.ru/miniapp`

Открывается через бота командой `/app`

## 🔧 Управление сервисами

### Перезапуск

```bash
# Все сервисы
sudo -u vpvks docker compose restart

# Отдельный сервис
sudo -u vpvks docker compose restart marzban
```

### Остановка

```bash
# Все сервисы
sudo -u vpvks docker compose down

# Отдельный сервис
sudo -u vpvks docker compose stop marzban
```

### Обновление

```bash
# Обновить образы
sudo -u vpvks docker compose pull

# Пересоздать контейнеры
sudo -u vpvks docker compose up -d --force-recreate
```

## 📊 Порты сервисов

| Сервис | Порт | Протокол | Доступ |
|--------|------|----------|--------|
| nginx | 80, 443 | TCP | Внешний |
| Backend | 8080 | TCP | localhost |
| Marzban | 8000 | TCP | localhost |
| PgBouncer | 6432 | TCP | Внешний |
| WireGuard | 51820 | UDP | Внешний |
| PostgreSQL (bot) | 5432 | TCP | Docker network |
| Marzban (SQLite) | - | - | Файл `/var/lib/marzban/db.sqlite3` |

## 🔑 Критичные файлы

| Файл | Описание | Секреты |
|------|----------|---------|
| `.env` | Основные переменные | ✅ |
| `marzban.env` | Marzban переменные | ✅ |
| `docker-compose.yml` | Конфигурация Docker | ❌ |
| `/etc/wireguard/*` | WireGuard ключи | ✅ |
| `/etc/letsencrypt/*` | SSL сертификаты | ✅ |

## 🛠️ Troubleshooting

### Marzban не запускается

```bash
# Проверь логи
sudo -u vpvks docker compose logs marzban

# Проверь .env файл
cat /opt/vpvks/marzban.env

# Пересоздай контейнер
sudo -u vpvks docker compose down marzban
sudo -u vpvks docker compose up -d marzban
```

**Важно:** Marzban использует SQLite (`/var/lib/marzban/db.sqlite3`). При проблемах с миграцией:

```bash
# Подключись к контейнеру
sudo -u vpvks docker compose exec marzban bash

# Проверь БД
cd /var/lib/marzban
ls -la db.sqlite3

# При необходимости - ручное исправление через psql не требуется
```

### Backend не подключается к БД

```bash
# Проверь DATABASE_URL в .env
cat /opt/vpvks/.env | grep DATABASE_URL

# Должно быть: @postgres:5432 (не @pgbouncer!)

# Перезапусти
sudo -u vpvks docker compose restart backend pgbouncer postgres
```

### WireGuard не работает

```bash
# Проверь статус
sudo wg show

# Проверь порт
sudo ss -tulpn | grep 51820

# Перезапусти
sudo systemctl restart wg-quick@wg0
```

### nginx не проксирует

```bash
# Проверь конфиг
nginx -t

# Перезагрузи
systemctl reload nginx

# Проверь логи
tail -f /var/log/nginx/vpvks_error.log
```

## 📝 Интеграция с Marzban

### Создание пользователя через API

```bash
curl -X POST "https://vpvks.ru/api/user" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user123",
    "proxies": ["vless", "trojan"],
    "inbounds": ["VLESS TCP", "Trojan TCP"],
    "data_limit": 10737418240,
    "expire": 1709251200
  }'
```

### Получение подписки

```bash
curl "https://vpvks.ru/sub/<TOKEN>"
```

## 📞 Контакты

- **Сервер:** 23.134.216.190
- **Домен:** vpvks.ru
- **Бот:** @relatevpnbot
- **Admin ID:** 699469085
- **Пользователь:** vpvks (без права логина)
