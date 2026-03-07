# 🔒 Security Guidelines

## Настройка безопасности

### 1. Генерация безопасных ключей

```bash
# SECRET_KEY для Flask (32 байта)
python -c "import secrets; print(secrets.token_hex(32))"

# Пароль для БД (минимум 16 символов)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Пароль для Marzban
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Настройка .env

```bash
cp .env.example .env
nano .env  # Вставьте сгенерированные ключи
```

**Критические переменные:**
- `SECRET_KEY` - ключ сессии Flask
- `TELEGRAM_BOT_TOKEN` - токен бота
- `MARZBAN_PASSWORD` - пароль администратора Marzban
- `POSTGRES_PASSWORD` - пароль БД
- `YOOKASSA_SECRET_KEY` - секретный ключ платёжной системы

### 3. Проверка безопасности

```bash
# Проверка что .env не в git
git ls-files | grep -E "^\.env$|\.env\."

# Должно вернуть пусто!
```

---

## ✅ Реализованные меры безопасности

### 1. Rate Limiting (защита от brute force)

**Default limits:**
- 100 запросов в минуту
- 1000 запросов в час

**Критичные endpoint'ы:**
| Endpoint | Лимит | Назначение |
|----------|-------|------------|
| `/api/users` (POST) | 10/мин | Регистрация |
| `/api/payment/create` | 5/мин | Создание платежей |
| `/api/payment/topup` | 10/мин | Пополнение баланса |
| `/api/vpn/key/<user_id>` | 20/мин | Получение ключа |
| `/api/vpn/check-fingerprint` | 30/мин | Anti-sharing |
| `/api/users/<id>/balance` | 60/мин | Проверка баланса |

**Для production с несколькими инстансами backend используйте Redis:**
```bash
RATELIMIT_STORAGE_URL=redis://redis:6379
```

**Для текущего проекта (1 инстанс):**
```bash
RATELIMIT_STORAGE_URL=memory://  # ✅ Достаточно!
```

**Когда понадобится Redis:**
- При >500 активных пользователей
- При 2+ инстансах backend
- При добавлении Celery для фоновых задач

### 2. Защита от XSS атак
```python
X-XSS-Protection: 1; mode=block
```

### 2. Защита от clickjacking
```python
X-Frame-Options: DENY
```

### 3. Защита от MIME sniffing
```python
X-Content-Type-Options: nosniff
```

### 4. Referrer Policy
```python
Referrer-Policy: strict-origin-when-cross-origin
```

### 5. CORS защита
```python
CORS(app, resources={r"/api/*": {"origins": "*"}})
```

### 6. Безопасное хранение секретов
- Все секреты в переменных окружения
- Нет хардкода в коде
- `.env` в `.gitignore`

### 7. Валидация входных данных
- SQLAlchemy ORM (защита от SQL injection)
- Проверка типов данных
- Валидация JSON

---

## 🚨 Критические предупреждения

### Никогда не делайте:
1. ❌ Не коммитьте `.env` в git
2. ❌ Не используйте пароли по умолчанию
3. ❌ Не передавайте секреты в логах
4. ❌ Не используйте `debug=True` в production

### Всегда делайте:
1. ✅ Генерируйте случайные пароли (32+ символа)
2. ✅ Регулярно обновляйте зависимости
3. ✅ Проверяйте логи на подозрительную активность
4. ✅ Используйте HTTPS в production

---

## 📋 Checklist для production

- [ ] Сгенерирован `SECRET_KEY`
- [ ] Установлены сложные пароли
- [ ] `.env` добавлен в `.gitignore`
- [ ] Включён HTTPS
- [ ] Настроен firewall
- [ ] Включено логирование
- [ ] Настроены бэкапы
- [ ] Ограничен доступ к админке

---

## 🛡️ Дополнительные рекомендации

### 1. Ограничьте CORS
```python
# Для production укажите конкретные домены
CORS(app, resources={r"/api/*": {"origins": ["https://yourdomain.com"]}})
```

### 2. Rate limiting
Установите Flask-Limiter для защиты от brute force:
```bash
pip install flask-limiter
```

### 3. HTTPS в production
Используйте reverse proxy (nginx) с Let's Encrypt:
```bash
certbot --nginx -d yourdomain.com
```

### 4. Мониторинг
Настройте алерты на:
- Множественные неудачные логины
- Подозрительная активность API
- Ошибки базы данных
