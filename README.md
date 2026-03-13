# 🔐 VPVKS VPN — Telegram-бот для продажи VPN-подписок

Автоматизированная система продажи и управления VPN-подписками через Telegram с интеграцией платежей.

---

## 📋 Содержание

1. [О проекте](#-о-проекте)
2. [Архитектура](#-архитектура)
3. [Быстрый старт](#-быстрый-старт)
4. [Настройка](#-настройка)
5. [Безопасность](#-безопасность)
6. [API](#-api)
7. [Troubleshooting](#-troubleshooting)

---

## 📖 О проекте

**VPVKS VPN** — Telegram-бот для автоматизированной продажи VPN-подписок.

### Возможности

- ✅ Telegram Mini App (Web App)
- ✅ Платёжная система (YooKassa)
- ✅ Автоматическая выдача подписок
- ✅ Автоматические уведомления (ежедневно в 10:00)
- ✅ Anti-Sharing защита
- ✅ Синхронизация Marzban ↔ PostgreSQL (каждые 15 мин)
- ✅ Production WSGI сервер (Gunicorn)
- ✅ Health checks для всех сервисов

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    nginx:443 (SSL)                              │
│                reverse proxy для всех сервисов                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Backend:8080  │   │ Marzban:8000  │   │   Bot         │
│ (Gunicorn)    │   │               │   │               │
│ 2 workers     │   │               │   │               │
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

### Компоненты

| Сервис | Порт | Описание |
|--------|------|----------|
| **nginx** | 443, 80 | Reverse proxy, SSL termination |
| **Backend** | 8080 | Flask API + Gunicorn (2 workers × 2 threads) |
| **Bot** | — | Telegram bot + APScheduler |
| **Marzban** | 8000 | VPN панель управления (VLESS/Trojan) |
| **PgBouncer** | 6432 | Connection pooler для PostgreSQL |
| **PostgreSQL** | 5432 | Основная база данных |

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
git clone <repository_url> vpvks
cd vpvks
```

### 2. Настройка переменных

```bash
# Копирование примеров
cp .env.example .env
cp marzban.env.example marzban.env

# Редактирование
nano .env
nano marzban.env
```

**Обязательные переменные:**

- `POSTGRES_PASSWORD` — пароль БД
- `SECRET_KEY` — ключ Flask (минимум 32 символа)
- `TELEGRAM_BOT_TOKEN` — токен бота
- `YOOKASSA_SHOP_ID` — ID магазина
- `YOOKASSA_SECRET_KEY` — секретный ключ
- `MARZBAN_PASSWORD` — пароль администратора Marzban

### 3. Настройка Firewall (UFW)

```bash
# Установка UFW
apt install ufw -y

# Настройка правил
ufw allow 22/tcp comment "SSH"
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"
ufw allow 8443/tcp comment "VLESS Reality"
ufw allow 2083/tcp comment "Trojan TLS"
ufw allow 6432/tcp comment "PgBouncer (admin)"

# Включение
ufw enable
ufw status
```

### 4. Запуск

```bash
docker compose up -d
```

### 5. Проверка

```bash
docker compose ps
```

**Ожидаемый результат:**

```
NAME            STATUS
marzban         Up
vpn_backend     Up (healthy)
vpn_bot         Up (healthy)
vpn_pgbouncer   Up
vpn_postgres    Up (healthy)
```

### 6. Миграция БД

```bash
docker exec vpn_backend python /app/migrations/migrate_normalize_database.py
```

---

## 🔧 Настройка

### SSL сертификаты

```bash
# Установка Certbot
apt install certbot python3-certbot-nginx -y

# Получение сертификата
certbot --nginx -d yourdomain.com

# Автоматическое обновление
certbot renew --dry-run
```

### Nginx

```bash
# Проверка конфига
nginx -t

# Перезагрузка
systemctl reload nginx

# Логи
tail -f /var/log/nginx/error.log
```

### Gunicorn (Production Server)

Backend использует Gunicorn с настройками для 2 CPU / 2 RAM:

```yaml
# docker-compose.yml
backend:
  command: >
    gunicorn 
    --bind 0.0.0.0:8080 
    --workers 2 
    --threads 2 
    --timeout 120 
    --keep-alive 5
    server:app
```

**Параметры:**
- `--workers 2` — количество процессов (= CPU ядрам)
- `--threads 2` — потоков на процесс
- `--timeout 120` — таймаут запросов (сек)
- `--keep-alive 5` — keep-alive соединения (сек)

---

## 🔒 Безопасность

### Firewall (UFW)

| Порт | Статус | Описание |
|------|--------|----------|
| **22/tcp** | ✅ Открыт | SSH |
| **80/tcp** | ✅ Открыт | HTTP (redirect на HTTPS) |
| **443/tcp** | ✅ Открыт | HTTPS |
| **6432/tcp** | ✅ Открыт | PgBouncer (admin доступ) |
| **8443/tcp** | ✅ Открыт | VLESS Reality |
| **2083/tcp** | ✅ Открыт | Trojan TLS |
| **8444/udp** | ✅ Открыт | Hysteria 2 |
| **5432/tcp** | 🔒 Закрыт | PostgreSQL (только Docker) |
| **8080/tcp** | 🔒 Закрыт | Backend (только Docker) |
| **8000/tcp** | 🔒 Закрыт | Marzban (только Docker) |

### Защита данных

- ✅ Rate Limiting (100/мин, 1000/час)
- ✅ CORS (ограничение источников)
- ✅ Security Headers (XSS, clickjacking)
- ✅ Нет хардкода секретов
- ✅ Валидация входных данных
- ✅ PostgreSQL закрыт от интернета
- ✅ Backend доступен только через nginx

### Health Checks

| Сервис | Интервал | Endpoint |
|--------|----------|----------|
| **Backend** | 30 сек | `/health` |
| **Bot** | 60 сек | Telegram API |
| **PostgreSQL** | 10 сек | `pg_isready` |

---

## 📡 API

### Основные endpoint'ы

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/health` | Health check |
| `GET` | `/api/users/<id>` | Информация о пользователе |
| `POST` | `/api/users` | Создание пользователя |
| `GET` | `/api/users/<id>/balance` | Баланс пользователя |
| `GET` | `/api/vpn/key/<id>` | Получение VPN ключа |
| `POST` | `/api/payment/create` | Создание платежа |
| `POST` | `/api/payment/webhook` | Webhook от платёжной системы |
| `POST` | `/api/sync/marzban` | Синхронизация с Marzban |

### Rate Limiting

| Endpoint | Лимит |
|----------|-------|
| `/api/users` (POST) | 10/мин |
| `/api/payment/create` | 5/мин |
| `/api/vpn/key/<id>` | 20/мин |
| Остальные | 100/мин, 1000/час |

---

## 💰 Платёжная система

### Настройка YooKassa

1. Зарегистрируйтесь на [yookassa.ru](https://yookassa.ru)
2. Получите `shopId` и `secretKey`
3. Настройте webhook: `https://yourdomain.com/api/payment/webhook`
4. Обновите `.env`:
   ```bash
   YOOKASSA_SHOP_ID=your_shop_id
   YOOKASSA_SECRET_KEY=your_secret_key
   YOOKASSA_TEST_MODE=true  # false для production
   ```

### Тарифы

| Тариф | Время | Цена |
|-------|-------|------|
| **1 месяц** | 30 дней | 110₽ |
| **3 месяца** | 90 дней | 210₽ |
| **12 месяцев** | 365 дней | 590₽ |

---

## 🎛️ Команды управления

### Docker

```bash
# Запуск всех сервисов
docker compose up -d

# Остановка
docker compose down

# Перезапуск сервиса
docker compose restart backend

# Логи
docker compose logs -f
docker compose logs backend --tail 50

# Статус
docker compose ps
```

### Проверка здоровья

```bash
# Проверка всех сервисов
docker compose ps

# Проверка health status
docker inspect vpn_backend --format='{{.State.Health.Status}}'
docker inspect vpn_bot --format='{{.State.Health.Status}}'
docker inspect vpn_postgres --format='{{.State.Health.Status}}'
```

### UFW

```bash
# Статус
ufw status

# Добавить правило
ufw allow 8443/tcp comment "VLESS Reality"

# Удалить правило
ufw delete allow 5432

# Перезагрузка
ufw disable && ufw enable
```

---

## 🔧 Troubleshooting

### VPN подключается, но сайты не работают

**Диагностика:**

```bash
# Проверь IP
curl -s https://api.ipify.org

# Проверь DNS
curl -s https://dnsleaktest.com

# Проверь сервер
docker compose logs marzban --tail 30 | grep -i "error"
```

**Решение:**

1. Включи **Fragment** в клиенте
2. Включи **VPN Mode** (не Proxy!)
3. Пропиши DNS: `1.1.1.1` или `8.8.8.8`

### Backend не подключается к Marzban

```bash
# Проверь переменные
docker exec vpn_backend env | grep MARZBAN

# Перезапусти backend
docker compose restart backend
```

### 502 Bad Gateway

```bash
# Проверь Marzban
docker compose ps marzban
ss -tulpn | grep 8000

# Проверь nginx
nginx -t
systemctl reload nginx

# Проверь логи
tail -f /var/log/nginx/error.log
```

### Синхронизация не работает

```bash
# Проверь логи backend
docker compose logs backend --grep "sync" --tail 20

# Проверь логи bot
docker compose logs bot --grep "marzban_sync" --tail 20

# Принудительная синхронизация
curl -X POST http://localhost:8080/api/sync/marzban
```

### Health check failed

```bash
# Проверь статус
docker compose ps

# Проверь логи
docker compose logs backend --tail 50

# Перезапусти
docker compose restart backend
```

---

## 📊 Метрики

### Целевые показатели

| Метрика | Цель |
|---------|------|
| **Uptime** | 99.9% |
| **Пинг** | ~45ms |
| **Скорость** | ~100 Мбит/с |
| **RAM usage** | < 1.5 GB / 2 GB |
| **CPU usage** | < 80% |

### Мониторинг

```bash
# Использование ресурсов
docker stats

# Логи всех сервисов
docker compose logs -f

# Статус UFW
ufw status verbose
```

---

## 📚 История изменений

### v1.2.0 — Production Ready

- ✅ Gunicorn production server (2 workers × 2 threads)
- ✅ UFW firewall настроен
- ✅ PostgreSQL закрыт от интернета
- ✅ Backend закрыт от интернета (только nginx)
- ✅ Health checks для всех сервисов
- ✅ Синхронизация Marzban каждые 15 минут
- ✅ Уведомления об истечении подписки

### v1.1.0

- ✅ Автоматические уведомления об истечении
- ✅ Синхронизация Marzban ↔ PostgreSQL
- ✅ Anti-Sharing защита
- ✅ Обновлён Mini App (только V2Ray)
- ✅ Улучшены .gitignore и .dockerignore

### v1.0.0

- ✅ Полная интеграция Marzban + Backend
- ✅ Bot выдаёт ключи V2Ray
- ✅ Платёжная система интегрирована
- ✅ Mini App личный кабинет

---

## 📞 Поддержка

- **Telegram:** @vpvks_support
- **Канал:** @vpvks_news
- **Инструкции:** @vpvkspc, @VPVKSinstr

---

*Документ обновлён: Март 2026 г.*
