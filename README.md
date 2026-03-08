# 🔐 VPVKS VPN — Telegram-бот для продажи VPN-подписок

Автоматизированная система продажи и управления VPN-подписками через Telegram с интеграцией платежей.

---

## 📋 Содержание

1. [О проекте](#-о-проекте)
2. [Архитектура](#-архитектура)
3. [Быстрый старт](#-быстрый-старт)
4. [Настройка](#-настройка)
5. [API](#-api)
6. [Troubleshooting](#-troubleshooting)

---

## 📖 О проекте

**VPVKS VPN** — Telegram-бот для автоматизированной продажи VPN-подписок.

### Возможности

- ✅ Telegram Mini App (Web App)
- ✅ Платёжная система (YooKassa)
- ✅ Автоматическая выдача подписок
- ✅ Автоматические уведомления
- ✅ Anti-Sharing защита

---

---

---

## 🏗️ Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                    nginx:443 (SSL)                              │
│                reverse proxy для всех сервисов                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼
        │                    │  
        ▼                    ▼  
┌───────────────┐   ┌───────────────┐   
│ Backend:8080  │   │ Marzban:8000  │   
│ (Flask API)   │   │               │
└───────┬───────┘   └───────┬───────┘   
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

### 3. Запуск

```bash
docker compose up -d
```

### 4. Проверка

```bash
docker compose ps
```

**Ожидаемый результат:**

```
NAME            STATUS
marzban         Up
vpn_backend     Up
vpn_bot         Up
vpn_pgbouncer   Up
vpn_postgres    Up (healthy)
```

### 5. Миграция БД

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

### Firewall

```bash
# Установка UFW
apt install ufw -y

# Настройка правил
ufw allow 22/tcp comment "SSH"
ufw allow 80/tcp comment "HTTP"
ufw allow 443/tcp comment "HTTPS"
ufw allow 8443/tcp comment "VLESS Reality"
ufw allow 2083/tcp comment "Trojan TLS"

# Включение
ufw enable
ufw status
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

---

## 📡 API

### Основные endpoint'ы

| Метод | Endpoint                    | Описание                                 |
| ---------- | --------------------------- | ------------------------------------------------ |
| `GET`    | `/api/users/<id>`         | Информация о пользователе |
| `POST`   | `/api/users`              | Создание пользователя        |
| `GET`    | `/api/users/<id>/balance` | Баланс пользователя            |
| `GET`    | `/api/vpn/key/<id>`       | Получение VPN ключа                |
| `POST`   | `/api/payment/create`     | Создание платежа                  |
| `POST`   | `/api/payment/webhook`    | Webhook от платёжной системы   |

### Rate Limiting

| Endpoint                | Лимит              |
| ----------------------- | ----------------------- |
| `/api/users` (POST)   | 10/мин               |
| `/api/payment/create` | 5/мин                |
| `/api/vpn/key/<id>`   | 20/мин               |
| Остальные      | 100/мин, 1000/час |

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

| Тариф                  | Время   | Цена |
| --------------------------- | ------------ | -------- |
| **1 месяц**      | 30 дней  | 110₽    |
| **3 месяца**    | 90 дней  | 210₽    |
| **12 месяцев** | 365 дней | 590₽    |

---

## 🎛️ Команды управления

### Docker

```bash
# Запуск всех сервисов
docker compose up -d

# Остановка
docker compose down

# Перезапуск сервиса
docker compose restart marzban

# Логи
docker compose logs -f
docker compose logs marzban --tail 50

# Статус
docker compose ps
```

### Marzban

```bash
# Проверка статуса
docker compose ps marzban

# Логи
docker compose logs marzban --tail 30

# Перезапуск
docker compose restart marzban
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

---

## 📊 Метрики

### Целевые показатели

| Метрика             | Цель         |
| -------------------------- | ---------------- |
| **Uptime**           | 99.9%            |
| **Пинг**         | ~45ms            |
| **Скорость** | ~100 Мбит/с |

---

## 📚 История изменений

### v1.1.0 — Большое обновление

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

## 🔒 Безопасность

- ✅ Rate Limiting (защита от brute force)
- ✅ CORS (ограничение источников)
- ✅ Security Headers (XSS, clickjacking)
- ✅ Нет хардкода секретов
- ✅ Валидация входных данных

**Подробнее:** [SECURITY.md](SECURITY.md)

---

*Документ обновлён: Март 2026 г.*
