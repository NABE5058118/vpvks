# 🚀 Инструкция по развёртыванию VPN проекта с Marzban

> **Версия:** Февраль 2026
> **Сервер:** 23.134.216.190
> **Домен:** vpvks.ru

---

## 📋 Содержание

1. [Подготовка сервера](#1-подготовка-сервера)
2. [Настройка Marzban](#2-настройка-marzban)
3. [Настройка Backend](#3-настройка-backend)
4. [Настройка бота](#4-настройка-бота)
5. [Тестирование](#5-тестирование)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Подготовка сервера

### 1.1 Обновление системы

```bash
ssh root@23.134.216.190

apt update && apt upgrade -y
apt install ufw -y
```

### 1.2 Настройка firewall

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp       # SSH
ufw allow 443/tcp      # HTTPS
ufw allow 80/tcp       # HTTP
ufw allow 8443/tcp     # VLESS Reality
ufw allow 2083/tcp     # Trojan TLS
ufw --force enable
ufw status
```

### 1.3 Клонирование проекта

```bash
cd /opt
rm -rf vpvks
git clone https://github.com/YOUR_USERNAME/vpvks.git
cd /opt/vpvks
```

### 1.4 Настройка переменных окружения

```bash
# Копирование примеров
cp .env.example .env
cp marzban.env.example marzban.env

# Редактирование .env
nano .env
```

**Заполни .env:**

```env
# PostgreSQL
POSTGRES_DB=vpn_bot_db
POSTGRES_USER=vpn_bot_user
POSTGRES_PASSWORD=<secure_password>

# PgBouncer
DATABASE_URL=postgresql://vpn_bot_user:<password>@pgbouncer:5432/vpn_bot_db
POOL_MODE=transaction
MAX_CLIENT_CONN=1000
DEFAULT_POOL_SIZE=50
ADMIN_USERS=vpn_bot_user
AUTH_TYPE=scram-sha-256

# Backend
SECRET_KEY=<secret_key>
PORT=8080

# YooKassa
YOOKASSA_SHOP_ID=<shop_id>
YOOKASSA_SECRET_KEY=<secret_key>
YOOKASSA_TEST_MODE=true
YOOKASSA_RETURN_URL=https://vpvks.ru/payment-success

# Marzban
MARZBAN_URL=http://127.0.0.1:8000
MARZBAN_ADMIN=admin
MARZBAN_PASSWORD=j8X0EcIllDwPK

# Bot
TELEGRAM_BOT_TOKEN=<bot_token>
BACKEND_URL=https://vpvks.ru
ADMIN_USER_IDS=<your_telegram_id>
MINI_APP_URL=https://vpvks.ru/miniapp
```

---

## 2. Настройка Marzban

### 2.1 Копирование конфига Xray

```bash
# Копируем готовый конфиг из репозитория
cp /opt/vpvks/xray_config.json /var/lib/marzban/xray_config.json

# Проверка JSON
python3 -m json.tool /var/lib/marzban/xray_config.json > /dev/null && echo "✅ JSON валиден" || echo "❌ Ошибка"
```

### 2.2 Проверка SSL сертификатов

```bash
# Проверка наличия SSL
ls -la /etc/letsencrypt/live/vpvks.ru/

# Если нет — нужно получить
apt install certbot -y
certbot certonly --standalone -d vpvks.ru -d marzban.vpvks.ru
```

### 2.3 Запуск Marzban

```bash
cd /opt/vpvks
docker compose up -d marzban

# Проверка статуса
docker compose ps marzban
docker compose logs marzban --tail 30
```

### 2.4 Настройка через веб-панель

1. Открой: **https://marzban.vpvks.ru/dashboard/**
2. Логин: `admin`
3. Пароль: `j8X0EcIllDwPK`

**A. Проверь Inbounds:**
- Кликни **Inbounds** → должны быть `VLESS Reality` (8443) и `Trojan TLS` (2083)

**B. Настройка Hosts:**
- **Settings → Hosts → Add**
```
Remark: Main
Address: vpvks.ru
Port: 443
```

**C. User Templates (Тарифы):**
- **User Templates → Create Template**

| Название | Data Limit (bytes) | Expire Days |
|----------|-------------------|-------------|
| Start | 10737418240 (10 GB) | 30 |
| Standard | 53687091200 (50 GB) | 30 |
| Premium | 107374182400 (100 GB) | 30 |

---

## 3. Настройка Backend

### 3.1 Запуск backend

```bash
cd /opt/vpvks
docker compose up -d backend postgres pgbouncer

# Проверка
docker compose ps
```

### 3.2 Проверка API

```bash
# Health check
curl -s http://localhost:8080/api/status

# Проверка Marzban API
curl -s -X POST "http://127.0.0.1:8000/api/admin/token" \
  -d "username=admin&password=j8X0EcIllDwPK"
```

---

## 4. Настройка бота

### 4.1 Запуск бота

```bash
cd /opt/vpvks
docker compose up -d bot

# Проверка
docker compose ps bot
docker compose logs bot --tail 20
```

### 4.2 Проверка в Telegram

1. Открой бота в Telegram
2. Отправь `/start`
3. Проверь команду `/key`

---

## 5. Тестирование

### 5.1 Тест создания пользователя Marzban

```bash
# Получение токена
TOKEN=$(curl -s -X POST "http://127.0.0.1:8000/api/admin/token" \
  -d "username=admin&password=j8X0EcIllDwPK" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Создание тестового пользователя
curl -X POST "http://127.0.0.1:8000/api/user" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "test_user",
    "proxies": ["vless", "trojan"],
    "data_limit": 10737418240,
    "expire": 1774500000
  }' | python3 -m json.tool

# Получение подписки
curl -X GET "http://127.0.0.1:8000/api/user/test_user/subscription" \
  -H "Authorization: Bearer $TOKEN"
```

### 5.2 Тест backend API

```bash
# Тест создания пользователя Marzban через backend
curl -X POST "http://localhost:8080/api/marzban/create" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 123456, "tariff": "standard"}' | python3 -m json.tool
```

### 5.3 Тест в клиенте

1. Скопируй ссылку подписки из теста 5.1
2. Вставь в v2rayNG (Android) или V2Box (iOS)
3. Подключись
4. Проверь IP: https://2ip.ru

---

## 6. Troubleshooting

### Marzban не запускается

```bash
# Проверка логов
docker compose logs marzban --tail 50

# Проверка конфига
python3 -m json.tool /var/lib/marzban/xray_config.json

# Перезапуск
docker compose restart marzban
```

### Ошибка подключения к Marzban

```bash
# Проверка что порт 8000 слушается
ss -tulpn | grep 8000

# Проверка firewall
ufw status | grep 8000
```

### Backend не видит Marzban

```bash
# Проверка переменных окружения
docker exec vpn_backend env | grep MARZBAN

# Проверка подключения
docker exec vpn_backend curl -s http://127.0.0.1:8000/api/system
```

### Бот не отвечает

```bash
# Проверка логов
docker compose logs bot --tail 30

# Проверка токена
docker exec vpn_bot env | grep TELEGRAM_BOT_TOKEN

# Перезапуск
docker compose restart bot
```

### Ошибка SSL

```bash
# Проверка сертификатов
ls -la /etc/letsencrypt/live/vpvks.ru/

# Обновление SSL
certbot renew --force-renewal

# Перезапуск nginx
docker compose restart marzban-nginx
```

---

## 📊 Полезные команды

```bash
# Статус всех сервисов
docker compose ps

# Логи всех сервисов
docker compose logs -f

# Перезапуск всех сервисов
docker compose restart

# Обновление проекта
cd /opt/vpvks
git pull
docker compose down
docker compose up -d

# Мониторинг ресурсов
docker stats
```

---

## 🔐 Безопасность

1. **Смените пароль админа Marzban** после первой настройки
2. **Не коммитьте .env** в git
3. **Регулярно обновляйте** систему и Docker образы
4. **Настройте backup** базы данных

---

*Документ обновлён: 22 февраля 2026 г.*
