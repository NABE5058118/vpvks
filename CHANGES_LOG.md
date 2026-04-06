# VPVKS VPN — Applied Changes Log

> Перечень изменений, внесённых вручную на сервер (не все в git).

---

## 1. SSL в Telegram Bot (`bot/`)

### `bot/utils/api_client.py`
- Убран `ssl=False` → `ssl.create_default_context()` (MITM protection)
- Добавлены хелперы: `get_ssl_context()`, `create_connector()`, `create_session()`

### `bot/main.py`
- 7 мест заменены: `aiohttp.TCPConnector(ssl=False)` → `_create_session()` с SSL verification

---

## 2. Circuit Breaker + Retry + SSL в Marzban Client

### `backend/services/marzban_client.py`
- **Circuit Breaker:** `pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60)` на `get_token()`
- **Retry:** `HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504]))`
- **SSL:** `verify=False` → `verify=True` (все запросы)
- Убран `urllib3.disable_warnings()` (больше не глушим SSL warnings)

### `backend/requirements.txt`
- Добавлен `pybreaker==1.0.2`

---

## 3. pg_stat_statements (PostgreSQL мониторинг)

### `docker-compose.yml` → сервис `postgres`
Добавлены параметры:
```yaml
-c shared_preload_libraries=pg_stat_statements
-c pg_stat_statements.track=all
-c pg_stat_statements.max=1000
-c log_min_duration_statement=100
```

---

## 4. Gunicorn оптимизация

### `docker-compose.yml` → сервис `backend`
Уже настроено: `--workers 3 --threads 1 --timeout 60 --keep-alive 5`

---

## 5. Миграции БД

### `backend/migrations/002_add_check_constraints.sql` (НОВЫЙ)
- `chk_balance_positive` — balance >= 0
- `chk_data_limit_positive` — data_limit_gb >= 0
- `chk_used_traffic_positive` — used_traffic_gb >= 0
- `chk_amount_positive` — amount > 0
- `chk_stars_positive` — stars_amount >= 0

### `backend/migrations/003_add_partial_indexes.sql` (НОВЫЙ)
- `idx_users_active` — partial index на активных пользователей
- `idx_users_subscription_active` — composite index для проверки подписки
- `idx_users_balance` — index для balance queries
- `idx_payments_user_status` — composite для платежей пользователей
- `idx_payments_pending` — index для pending платежей
- `idx_connection_logs_recent` — partial index последних 30 дней

### `backend/database/db_config.py`
- Добавлен connection pooling: `pool_size=10, max_overflow=20, pool_recycle=3600, pool_pre_ping=True`

### `backend/scripts/cleanup_logs.py` (НОВЫЙ)
- Скрипт автоматической очистки connection logs старше N дней

---

## 6. Тестовые тарифы (1₽)

### `backend/config/tariffs.py`
Все цены изменены на **1** для тестирования платежей.

---

## 7. Замена vpvks.ru → delron.ru

### `backend/services/business_logic_service.py`
- `return_url`: `https://vpvks.ru/payment-success` → `https://delron.ru/payment-success`

### `backend/routes/__init__.py`
- `return_url`: `https://vpvks.ru/payment-success` → `https://delron.ru/payment-success`

---

## 8. nginx → Marzban (HTTPS upstream)

### `nginx/conf.d/marzban.conf`
- `proxy_pass http://127.0.0.1:8000/` → `proxy_pass https://127.0.0.1:8000/`
- Добавлены: `proxy_ssl_server_name off`, `proxy_ssl_verify off`

---

## 9. Маршрутизация сертификатов Marzban

### На сервере (НЕ в git):
```bash
# xray_config.json использует delron.ru вместо vpvks.ru
sed -i 's|/etc/letsencrypt/live/vpvks.ru/|/etc/letsencrypt/live/delron.ru/|g' /var/lib/marzban/xray_config.json

# Volume /etc/letsencrypt:/etc/letsencrypt:ro возвращён в docker-compose.yml для marzban
```

### `docker-compose.yml` → сервис `marzban`
- Убраны `UVICORN_SSL_CERTFILE` и `UVICORN_SSL_KEYFILE` (nginx делает SSL termination)
- Volume `/etc/letsencrypt:/etc/letsencrypt:ro` — **вернуть!** (нужен для Xray config)

---

## Известные проблемы

1. **YooKassa webhook'и** — не приходят в тестовом режиме. Нужен dev с доступом к магазину.
2. **cleanup_logs.py** — требует `ConnectionLog` model (должна существовать).
3. **MARZBAN_PASSWORD not set** — warning если переменная не установлена в `.env`.
