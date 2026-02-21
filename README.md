# VPN Bot Project - Полное руководство (vpvks.ru)

> **Последнее обновление:** 21 февраля 2026 г. (MSK)
> **Статус:** 🟡 Marzban настраивается (SQLite)
> **Сервер:** 23.134.216.190 (Ubuntu 24.04.4 LTS)
> **Домен:** vpvks.ru (SSL: Let's Encrypt)

---

## 📋 Описание проекта

Telegram-бот для управления VPN-подключениями с мини-приложением, системой оплаты и поддержкой двух протоколов:
- **WireGuard** (классический VPN)
- **V2Ray/Trojan/Reality** (через Marzban, для обхода блокировок)

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
│ Backend:8080  │   │ Marzban:8000  │   │ WireGuard:51820│
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
| Marzban | **SQLite** | `/var/lib/marzban/db.sqlite3` |
| WireGuard | Нет | Конфиги в `/etc/wireguard/` |

---

## 📁 Структура проекта

```
/opt/vpvks/                          # Основная директория (владелец: vpvks)
├── docker-compose.yml               # Оркестрация всех сервисов
├── .env                             # Переменные окружения (секреты)
├── marzban.env                      # Переменные для Marzban (секреты)
│
├── backend/                         # Flask API сервер
│   ├── server.py
│   ├── routes/
│   ├── models/
│   ├── database/
│   └── templates/
│       └── miniapp.html            # Mini App для Telegram
│
├── bot/                             # Telegram бот
│   ├── main.py
│   ├── handlers/
│   └── config/
│
├── pgbouncer/                       # Конфигурация PgBouncer
│   └── pgbouncer.ini
│
├── marzban/                         # Marzban конфиги (локальная копия)
│   ├── docker-compose.yml
│   ├── .env.example
│   └── README.md
│
└── .git/                            # Git репозиторий
```

---

## ✅ Выполненные задачи

### Инфраструктура (19-20 февраля 2026)
- [x] Сервер Ubuntu 24.04.4 LTS (23.134.216.190)
- [x] Домен `vpvks.ru` + SSL (Let's Encrypt)
- [x] Docker + Docker Compose установлен
- [x] nginx как reverse proxy
- [x] Пользователь `vpvks` (без права логина, в группе docker)
- [x] systemd-сервис для автозапуска

### VPN Bot Project (19-20 февраля 2026)
- [x] PostgreSQL 17-alpine в Docker
- [x] PgBouncer (connection pooler, порт 6432)
- [x] Backend (Flask, порт 8080)
- [x] Telegram бот (@relatevpnbot, polling)
- [x] Mini App (Web App для Telegram)
- [x] YooKassa интеграция (продакшен режим)
- [x] WireGuard сервер (порт 51820/udp)
- [x] WireGuard API (QR-коды, конфиги)

### Marzban (21 февраля 2026)
- [x] Docker Compose настроен
- [x] Отдельная сеть `marzban_network`
- [x] **SQLite для БД** (избегание проблем с миграциями PostgreSQL)
- [ ] Настройка Inbound (VLESS, Trojan, Reality)
- [ ] Интеграция с Telegram ботом

---

## 🔧 Конфигурация

### Переменные окружения

#### `.env` (основной)
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

# YooKassa (PRODUCTION)
YOOKASSA_SHOP_ID=1266298
YOOKASSA_SECRET_KEY=live_qGfOvzEBZkeKq-uhGWODlMjBC4mTavEpmZaYfwFX8Fo
YOOKASSA_TEST_MODE=false
YOOKASSA_RETURN_URL=https://vpvks.ru/payment-success

# WireGuard
WG_SERVER_IP=10.0.0.1
WG_PORT=51820
WG_DNS=8.8.8.8
WG_SERVER_PUBLIC_KEY=0gKla07MC1eDcaIuN4YSA5zKpDchNH0PCfELHBM3d34=
WG_CONFIG_DIR=./wg_configs

# Bot
TELEGRAM_BOT_TOKEN=8321727057:AAGJJwoVRoG7wYZQPfN9-q-IM4mHA82g2cU
BACKEND_URL=https://vpvks.ru
ADMIN_USER_IDS=699469085
MINI_APP_URL=https://vpvks.ru/miniapp
```

#### `marzban.env` (для Marzban)
```env
SECRET_KEY=7c1ac2b949198c0d8ac414776fd11b6beac83fb0a86acc9f1859c05384b717b5
SUBSCRIPTION_URL_PREFIX=https://vpvks.ru
UVICORN_WORKERS=2
XRAY_JSON=/var/lib/marzban/xray_config.json
SUDO_USERNAME=admin
SUDO_PASSWORD=j8X0EcIllDwPK
```

---

## 🚀 Команды для управления

### Запуск всех сервисов

```bash
cd /opt/vpvks
sudo -u vpvks docker compose up -d
```

### Проверка статуса

```bash
# Все сервисы
sudo -u vpvks docker compose ps

# Только Marzban
sudo -u vpvks docker compose ps marzban

# Только VPN Bot
sudo -u vpvks docker compose ps vpn_backend vpn_bot
```

### Логи

```bash
# Все логи
sudo -u vpvks docker compose logs -f

# Только Marzban
sudo -u vpvks docker compose logs -f marzban

# Только Backend
sudo -u vpvks docker compose logs -f backend
```

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

---

## 🌐 Доступ к панелям

### Marzban Panel

**URL:** `https://marzban.vpvks.ru`

**Логин/пароль:**
```
Username: admin
Password: j8X0EcIllDwPK
```

**Через SSH туннель:**
```bash
ssh -L 8000:localhost:8000 root@23.134.216.190
# Затем: http://127.0.0.1:8000
```

### Telegram Bot

**Бот:** @relatevpnbot

**Команды:**
- `/start` — главное меню
- `/app` — открыть Mini App
- `/status` — проверить статус подписки
- `/connect` — подключиться к VPN
- `/disconnect` — отключиться от VPN

### Mini App

**URL:** `https://vpvks.ru/miniapp`

Открывается через бота командой `/app`

---

## 📊 Порты сервисов

| Сервис | Порт | Протокол | Доступ |
|--------|------|----------|--------|
| nginx | 80, 443 | TCP | Внешний |
| Backend | 8080 | TCP | localhost |
| Marzban | 8000 | TCP | localhost |
| PgBouncer | 6432 | TCP | Внешний |
| WireGuard | 51820 | UDP | Внешний |
| PostgreSQL (bot) | 5432 | TCP | Docker network |
| Marzban (SQLite) | - | - | Файл |

---

## 🔍 Troubleshooting

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

---

## 🔑 Критичные файлы

| Файл | Описание | Секреты |
|------|----------|---------|
| `.env` | Основные переменные | ✅ |
| `marzban.env` | Marzban переменные | ✅ |
| `docker-compose.yml` | Конфигурация Docker | ❌ |
| `/etc/wireguard/*` | WireGuard ключи | ✅ |
| `/etc/letsencrypt/*` | SSL сертификаты | ✅ |
| `/var/lib/marzban/db.sqlite3` | БД Marzban | ✅ |

---

## 📝 Следующие шаги

### Актуальные задачи
1. ⏳ **Настроить Inbound в Marzban** (VLESS Reality, Trojan)
2. ⏳ **Интеграция бота с Marzban** (создание пользователей через API)
3. ⏳ **Диагностика WireGuard** (трафик уходит, но не возвращается)

### Долгосрочные задачи
- [ ] Настроить мониторинг (Prometheus + Grafana)
- [ ] Настроить резервное копирование БД
- [ ] Провести нагрузочное тестирование
- [ ] Добавить поддержку v2ray/Xray в Mini App

---

## 📞 Контакты

| Параметр | Значение |
|----------|----------|
| Сервер | 23.134.216.190 |
| Домен | vpvks.ru |
| Бот | @relatevpnbot |
| Admin ID | 699469085 |
| Пользователь | `vpvks` (без права логина) |

---

## 📚 Документация

- [`НАСТРОЙКА_MARZBAN.md`](./НАСТРОЙКА_MARZBAN.md) — Инструкция по настройке Marzban
- [`РАЗВЁРТЫВАНИЕ_MARZBAN.md`](./РАЗВЁРТЫВАНИЕ_MARZBAN.md) — Полная инструкция по развёртыванию
- [`ИНСТРУКЦИЯ_ДОМЕН_SSL.md`](./ИНСТРУКЦИЯ_ДОМЕН_SSL.md) — Настройка домена и SSL
- [`ЗАПУСК_КОМАНДЫ.md`](./ЗАПУСК_КОМАНДЫ.md) — Команды для запуска

---

*Документ обновлён: 21 февраля 2026 г.*
