# 🚀 Развёртывание и запуск бота

## Быстрый старт

### 1. Настройка переменных окружения

```bash
# Скопируйте пример .env
cp .env.example .env

# Отредактируйте .env
nano .env
```

### 2. Обязательные переменные

```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:AABBccDDeeFFggHHiiJJkkLLmmNNooP

# Backend
BACKEND_URL=http://vpn_backend:8080
DATABASE_URL=postgresql://vpn_bot_user:vp62RofV5h@vpn_pgbouncer:5432/vpn_bot_db

# Mini App
MINI_APP_URL=https://vpvks.ru/miniapp

# Каналы
CHANNEL_NEWS_URL=https://t.me/vpvks_news
CHANNEL_WIN_MAC_URL=https://t.me/vpvkspc
CHANNEL_ANDROID_IOS_URL=https://t.me/VPVKSinstr

# Admin IDs (ваш Telegram ID)
ADMIN_USER_IDS=123456789
```

### 3. Запуск

```bash
# Перезапуск бота
docker compose restart bot

# Проверка логов
docker compose logs -f bot
```

### 4. Проверка работы

1. Отправьте боту `/start`
2. Должно появиться меню с кнопками:
   - 🚀 Открыть VPN приложение
   - 📚 Инструкции
   - 📰 Новости VPVKS

3. Нажмите "📚 Инструкции"
4. Должны появиться кнопки:
   - 🖥️ Windows / macOS → https://t.me/vpvkspc
   - 📱 Android / iOS → https://t.me/VPVKSinstr

## 🔍 Отладка

### Проверка переменных

```bash
# Внутри контейнера бота
docker compose exec bot env | grep CHANNEL
```

**Ожидаемый вывод:**
```
CHANNEL_NEWS_URL=https://t.me/vpvks_news
CHANNEL_WIN_MAC_URL=https://t.me/vpvkspc
CHANNEL_ANDROID_IOS_URL=https://t.me/VPVKSinstr
```

### Логи бота

```bash
# Последние 50 строк
docker compose logs bot --tail 50

# В реальном времени
docker compose logs -f bot
```

### Если кнопки не отображаются

1. **Проверьте `.env` файл:**
```bash
cat .env | grep CHANNEL
```

2. **Перезапустите бота:**
```bash
docker compose down bot
docker compose up -d bot
```

3. **Проверьте логи при нажатии кнопки:**
```bash
docker compose logs -f bot | grep "📚 Показываю инструкции"
```

## 📋 Структура кнопок

```
/start
├── 🚀 Открыть VPN приложение (Mini App)
├── 📚 Инструкции
│   ├── 🖥️ Windows / macOS → https://t.me/vpvkspc
│   ├── 📱 Android / iOS → https://t.me/VPVKSinstr
│   └── 🔙 Назад
└── 📰 Новости VPVKS → https://t.me/vpvks_news
```

## 🛠️ Troubleshooting

### Кнопка "Инструкции" не работает

**Проблема:** При нажатии ничего не происходит

**Решение:**
1. Проверьте логи бота
2. Убедитесь что `TELEGRAM_BOT_TOKEN` правильный
3. Перезапустите бота

### Ссылки ведут на default значения

**Проблема:** Ссылки ведут на `https://t.me/vpvkspc` вместо ваших

**Решение:**
1. Проверьте `.env` файл
2. Убедитесь что переменные заданы правильно
3. Перезапустите бота

### Ошибка "Message is not modified"

**Проблема:** В логах `BadRequest: Message is not modified`

**Решение:** Это нормальное поведение Telegram API. Ошибка обрабатывается автоматически.

---

*Обновлено: Март 2026*
