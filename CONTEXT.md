# 🎯 КОНТЕКСТ ПРОЕКТА: VPVKS VPN

> **Дата:** 24 февраля 2026 г.  
> **Статус:** ✅ **ВСЁ РАБОТАЕТ**  
> **Для:** Продолжения разработки в новом чате

---

## 📊 ТЕКУЩИЙ СТАТУС

✅ **ВСЁ РАБОТАЕТ:**

| Компонент | Статус | Детали |
|-----------|--------|--------|
| **Сервер** | ✅ | 23.134.216.190 (Стокгольм, Aeza) |
| **Домен** | ✅ | vpvks.ru (SSL: Let's Encrypt) |
| **Marzban** | ✅ | Запущен, пользователи создаются |
| **VLESS Reality** | ✅ | Порт 8443, SNI: www.microsoft.com |
| **Trojan TLS** | ✅ | Порт 2083, SNI: vpvks.ru |
| **WireGuard** | ✅ | Порт 51820 (резервный) |
| **Backend (Flask)** | ✅ | Порт 8080, интегрирован с Marzban |
| **Telegram Bot** | ✅ | @relatevpnbot, выдаёт ключи через /key |
| **YooKassa** | ✅ | Настроена (Shop ID: 1266298) |
| **PostgreSQL 17** | ✅ | Работает через PgBouncer |
| **nginx** | ✅ | Reverse proxy для всех сервисов |

✅ **ТЕСТЫ ПРОЙДЕНЫ:**

| Тест | Результат |
|------|-----------|
| **YouTube** | ✅ Работает |
| **Instagram** | ✅ Работает |
| **DNS Leak** | ✅ Утечек нет |
| **IP Leak** | ✅ IP меняется на серверный |

---

## 🏗️ АРХИТЕКТУРА

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram Bot                          │
│              @relatevpnbot                               │
└────────────────────┬────────────────────────────────────┘
                     │ API запросы
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Backend (Flask, порт 8080)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │ VPN Service │  │Payment Svc  │  │ Business Logic  │  │
│  │(WireGuard)  │  │ (YooKassa)  │  │     Service     │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└────────────┬──────────────────────────────┬──────────────┘
             │                               │
             ▼                               ▼
┌─────────────────────┐          ┌──────────────────────────┐
│  PostgreSQL (БД)    │          │   Marzban (V2Ray/Trojan) │
│  - users            │          │   - VLESS Reality:8443   │
│  - payments         │          │   - Trojan TLS:2083      │
│  - vpn_configs      │          │   - API:8000             │
│  - wireguard конфиги│          │   - SQLite БД            │
└─────────────────────┘          └──────────────────────────┘
```

### Структура проекта:

```
/opt/vpvks/
├── docker-compose.yml          # Все сервисы
├── .env                        # Переменные (MARZBAN_URL=https://172.19.0.1:8000)
├── marzban.env                 # Marzban настройки
├── xray_config.json            # Xray конфиг (VLESS Reality + Trojan)
│
├── backend/
│   ├── server.py
│   ├── routes/__init__.py      # API endpoints (/api/marzban/create, /api/payment/webhook)
│   ├── models/                 # User, Payment, VPNConfig
│   └── services/
│       ├── vpn_service.py      # Интеграция с Marzban
│       ├── marzban_client.py   # Marzban API client (verify=False для HTTPS)
│       └── payment_service.py  # YooKassa интеграция
│
├── bot/
│   ├── main.py
│   ├── config.py
│   └── handlers/
│       ├── command_handlers.py
│       └── vpn_key_handler.py  # /key → выдача ключей
│
└── pgbouncer/
    └── pgbouncer.ini
```

---

## 🔑 КРИТИЧНЫЕ КОНФИГУРАЦИИ

### Marzban Credentials:

| Параметр | Значение |
|----------|----------|
| **URL (для backend)** | `https://172.19.0.1:8000` |
| **Public URL** | `https://vpvks.ru/marzban/dashboard/` |
| **Логин** | `admin` |
| **Пароль** | `j8X0EcIllDwPK` |

### VLESS Reality:

| Параметр | Значение |
|----------|----------|
| **Port** | `8443` |
| **SNI** | `www.microsoft.com` |
| **Public Key** | `daGDXnfX27yZ0e_ADuEMLJ3s96lMs2J3DGeBBw9XT0k` |
| **Private Key** | `OBGPuDLRkb0Cbae2t84LacjkcWY38TBw9umx1vKUHyk` |
| **Short IDs** | `["", "abc123def456"]` |

### Trojan TLS:

| Параметр | Значение |
|----------|----------|
| **Port** | `2083` |
| **SNI** | `vpvks.ru` |

### YooKassa:

| Параметр | Значение |
|----------|----------|
| **Shop ID** | `1266298` |
| **Secret Key** | `live_qGfOvzEBZkeKq-uhGWODlMjBC4mTavEpmZaYfwFX8Fo` |
| **Test Mode** | `false` (продакшен) |
| **Return URL** | `https://vpvks.ru/payment-success` |

### Firewall (UFW):

```bash
51820/udp  ALLOW  # WireGuard
80/tcp     ALLOW  # HTTP
443/tcp    ALLOW  # HTTPS
22/tcp     ALLOW  # SSH
8443/tcp   ALLOW  # VLESS Reality
2083/tcp   ALLOW  # Trojan TLS
```

### .env (ключевые переменные):

```env
# Marzban
MARZBAN_URL=https://172.19.0.1:8000
MARZBAN_ADMIN=admin
MARZBAN_PASSWORD=j8X0EcIllDwPK
MARZBAN_PUBLIC_URL=https://vpvks.ru

# Backend
BACKEND_URL=http://vpn_backend:8080
PORT=8080

# YooKassa
YOOKASSA_SHOP_ID=1266298
YOOKASSA_SECRET_KEY=live_qGfOvzEBZkeKq-uhGWODlMjBC4mTavEpmZaYfwFX8Fo
YOOKASSA_TEST_MODE=false
YOOKASSA_RETURN_URL=https://vpvks.ru/payment-success

# Bot
TELEGRAM_BOT_TOKEN=8321727057:AAGJJwoVRoG7wYZQPfN9-q-IM4mHA82g2cU
BACKEND_URL=http://vpn_backend:8080
ADMIN_USER_IDS=699469085
```

---

## 🎯 СЛЕДУЮЩИЕ ЗАДАЧИ (ПРИОРИТЕТЫ)

### Приоритет 1: Платёжная логика 🔴

| Задача | Статус | Сложность |
|--------|--------|-----------|
| Интегрировать YooKassa webhook (`/api/payment/webhook`) | ⏳ | ⭐⭐⭐ |
| Автоматическая выдача ключа после оплаты | ⏳ | ⭐⭐⭐ |
| Проверка баланса перед выдачей ключа | ⏳ | ⭐⭐ |
| Уведомления об оплате | ⏳ | ⭐⭐ |

### Приоритет 2: Улучшение бота 🟡

| Задача | Статус | Сложность |
|--------|--------|-----------|
| Красивые inline-кнопки с emoji | ⏳ | ⭐ |
| Команда `/tariffs` — список тарифов | ⏳ | ⭐ |
| Команда `/profile` — личный кабинет | ⏳ | ⭐⭐ |
| Mini App для управления подпиской | ⏳ | ⭐⭐⭐ |

### Приоритет 3: Безопасность 🟢

| Задача | Статус | Сложность |
|--------|--------|-----------|
| Rate Limiting для API | ⏳ | ⭐⭐ |
| Проверка на шаринг аккаунтов | ⏳ | ⭐⭐⭐ |
| Бэкап БД каждый час | ⏳ | ⭐⭐ |

### Приоритет 4: Аналитика 🔵

| Задача | Статус | Сложность |
|--------|--------|-----------|
| Дашборд метрик (выручка, пользователи, отток) | ⏳ | ⭐⭐⭐ |
| Событийная аналитика | ⏳ | ⭐⭐⭐ |

---

## 📝 ТЕКУЩИЕ ПРОБЛЕМЫ

| Проблема | Описание | Решение |
|----------|----------|---------|
| **Ключи выдаются без оплаты** | Любой может получить бесплатно | Проверка баланса перед выдачей |
| **Нет проверки подписки** | Нет механизма блокировки | Добавить статус в БД |
| **Нет автопродления** | Пользователь должен сам продлевать | Cron + списание с баланса |
| **Нет уведомлений** | Не напоминает об истечении | Telegram уведомления |

---

## 🛠️ ИНСТРУКЦИИ ДЛЯ РАЗРАБОТЧИКА

### При внесении изменений:

1. ❗ Не ломай текущую интеграцию с Marzban
2. ❗ Все изменения в `.env` сохраняй в `.env.example`
3. ❗ После изменений в backend — перезапускай: `docker compose restart backend`
4. ❗ После изменений в bot — перезапускай: `docker compose restart bot`
5. ❗ Проверяй логи: `docker compose logs backend --tail 30`

### Тестирование:

```bash
# DNS Leak
https://dnsleaktest.com

# IP Leak
https://api.ipify.org

# Speedtest
https://speedtest.net

# Instagram/YouTube
Должны работать!
```

### Git Workflow:

```bash
# Локально (Mac)
cd /Users/Galim/Documents/vpnn
git add .
git commit -m "feat: описание изменений"
git push origin main

# На сервере
cd /opt/vpvks
git pull origin main
docker compose restart <сервис>
```

---

## 💡 ВАЖНЫЕ ПРИНЦИПЫ

1. **Не усложняй** — текущая архитектура работает
2. **Тестируй** — каждое изменение проверяй на боевом сервере
3. **Документируй** — все изменения записывай в README.md
4. **Безопасность** — не коммить `.env`, пароли, ключи
5. **Постепенность** — внедряй по 1-2 фичи за раз

---

## 🚀 С ЧЕГО НАЧАТЬ

Если не знаешь с чего начать:

### 1. Проверь текущий статус:

```bash
cd /opt/vpvks
docker compose ps
curl -s http://localhost:8080/api/status
```

### 2. Выбери задачу из Приоритета 1 (платежи):

```python
# backend/services/payment_service.py

class PaymentService:
    def create_payment(self, data):
        """Создание платежа через YooKassa"""
        payment_data = {
            "amount": {"value": data['amount'], "currency": "RUB"},
            "capture": True,
            "description": f"VPN подписка: {data['tariff']}",
            "metadata": {"user_id": data['user_id']},
            "confirmation": {
                "type": "redirect",
                "return_url": YOOKASSA_RETURN_URL
            }
        }
        
        response = requests.post(
            "https://api.yookassa.ru/v3/payments",
            auth=(YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY),
            json=payment_data
        )
        
        return response.json()
```

### 3. Спроси у AI — помогу с реализацией!

---

## ⚠️ НЕ ДЕЛАТЬ

- ❌ Не меняй архитектуру Marzban (работает стабильно)
- ❌ Не переводи на PostgreSQL (SQLite достаточно)
- ❌ Не меняй сеть Docker (network_mode: host работает)
- ❌ Не трогай firewall (все порты открыты правильно)

---

## 📚 ДОКУМЕНТАЦИЯ

Полная документация в `/opt/vpvks/README.md`

Включает:
- ✅ Архитектура проекта
- ✅ Настройка протоколов
- ✅ План внедрения платежей (4 этапа)
- ✅ План развития (мобильный прокси, маркетинг)
- ✅ Команды управления
- ✅ Troubleshooting

---

## 📞 КОНТАКТЫ

| Параметр | Значение |
|----------|----------|
| **Сервер** | 23.134.216.190 (NKtelecom INC) |
| **Домен** | vpvks.ru |
| **Бот** | [@relatevpnbot](https://t.me/relatevpnbot) |
| **Admin ID** | 699469085 |
| **GitHub** | [NABE5058118/vpvks](https://github.com/NABE5058118/vpvks) |

---

## 📈 ИСТОРИЯ ИЗМЕНЕНИЙ

### 24 февраля 2026 — ФИНАЛЬНЫЙ РЕЛИЗ

- ✅ **ВСЁ РАБОТАЕТ!**
- ✅ VLESS Reality с SNI `www.microsoft.com`
- ✅ Trojan TLS работает
- ✅ WireGuard работает
- ✅ Backend интегрирован с Marzban
- ✅ Bot выдаёт ключи через `/key`
- ✅ YooKassa настроена
- ✅ Firewall открыт (8443, 2083, 51820)
- ✅ Instagram работает
- ✅ YouTube работает

### 22 февраля 2026

- ✅ Marzban переведён на `network_mode: host`
- ✅ Xray запущен (порты 8443/2083 слушают)
- ✅ nginx настроен для проксирования

### 19-20 февраля 2026

- ✅ Сервер развёрнут (Aeza, Стокгольм)
- ✅ SSL настроен (Let's Encrypt)
- ✅ VPN Bot + Mini App работают
- ✅ YooKassa интегрирована
- ✅ WireGuard настроен

---

## 🎯 БЫСТРЫЕ КОМАНДЫ

```bash
# Проверка статуса
docker compose ps

# Перезапуск сервиса
docker compose restart backend
docker compose restart bot
docker compose restart marzban

# Логи
docker compose logs -f
docker compose logs backend --tail 30
docker compose logs bot --tail 30

# Проверка Marzban
curl -s -k https://127.0.0.1:8000/api/system

# Проверка backend
curl -s http://localhost:8080/api/status

# Проверка портов
ss -tulpn | grep -E "8443|2083|51820"
```

---

**ГОТОВ ПРОДОЛЖАТЬ РАЗРАБОТКУ! НАЧНИ С ВОПРОСА ИЛИ ЗАДАЧИ.** 🚀

---

*Документ создан: 24 февраля 2026 г.*  
*Для продолжения работы скопируй этот файл и отправь в новом чате с AI*
