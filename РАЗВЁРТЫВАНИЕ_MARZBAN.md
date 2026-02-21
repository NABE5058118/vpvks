# 🚀 Marzban + PostgreSQL: Инструкция по развёртыванию

## 📋 Предварительные требования

- Сервер Ubuntu 24.04 с Docker и Docker Compose
- Домен `marzban.vpvks.ru` с A-записью на сервер
- SSL-сертификаты Let's Encrypt в `/etc/letsencrypt/live/vpvks.ru/`

---

## 🔧 Шаг 1: Подготовка на сервере

### 1.1 Создай пользователя и директорию

```bash
# Создай пользователя (без права логина)
useradd -r -s /usr/sbin/nologin vpvks

# Создай директорию
mkdir -p /opt/vpvks

# Назначь владельца
chown -R vpvks:vpvks /opt/vpvks
```

### 1.2 Проверь SSL-сертификаты

```bash
ls -la /etc/letsencrypt/live/vpvks.ru/
```

Должны быть файлы:
- `fullchain.pem`
- `privkey.pem`

---

## 📦 Шаг 2: Копирование файлов на сервер

### 2.1 Локально (на Mac)

```bash
cd /Users/Galim/Documents/vpnn

# Копируем файлы
scp docker-compose.yml Dockerfile.marzban .env marzban.env root@23.134.216.190:/opt/vpvks/

# Копируем папки
scp -r backend bot pgbouncer root@23.134.216.190:/opt/vpvks/
```

### 2.2 На сервере

```bash
cd /opt/vpvks

# Назначь права
chmod 600 .env marzban.env
chown -R vpvks:vpvks /opt/vpvks
```

---

## 🗄️ Шаг 3: Исправление миграции PostgreSQL (если нужно)

### 3.1 Очистка старых данных

```bash
sudo -u vpvks docker compose down -v
rm -rf /var/lib/marzban-db
rm -rf /var/lib/marzban
```

### 3.2 Запуск только базы данных

```bash
sudo -u vpvks docker compose up -d marzban-db
```

### 3.3 Проверка подключения к БД

```bash
sudo -u vpvks docker compose exec marzban-db psql -U marzban -d marzban -c "\dt"
```

---

## 🔨 Шаг 4: Ручное исправление миграции (если ошибка Alembic)

### 4.1 Удаление проблемного типа

```bash
sudo -u vpvks docker compose exec marzban-db psql -U marzban -d marzban -c "DROP TYPE IF EXISTS temp_alpn CASCADE;"
```

### 4.2 Откат миграции

```bash
sudo -u vpvks docker compose run --rm marzban alembic downgrade 31f92220c0d0
```

### 4.3 Удаление DEFAULT у колонки alpn

```bash
sudo -u vpvks docker compose exec marzban-db psql -U marzban -d marzban -c "ALTER TABLE hosts ALTER COLUMN alpn DROP DEFAULT;"
```

### 4.4 Создание ENUM типа вручную

```bash
sudo -u vpvks docker compose exec -it marzban-db psql -U marzban -d marzban <<EOF
DO \$\$ BEGIN
    CREATE TYPE temp_alpn AS ENUM ('none', 'h2', 'http/1.1', 'h3', 'h3,h2', 'h3,h2,http/1.1', 'h2,http/1.1');
EXCEPTION
    WHEN duplicate_object THEN null;
END \$\$;

ALTER TABLE hosts ALTER COLUMN alpn TYPE text;
ALTER TABLE hosts ALTER COLUMN alpn TYPE temp_alpn USING alpn::temp_alpn;
ALTER TABLE hosts ALTER COLUMN alpn SET DEFAULT 'none';
EOF
```

### 4.5 Обновление версии Alembic

```bash
sudo -u vpvks docker compose exec marzban-db psql -U marzban -d marzban -c "INSERT INTO alembic_version (version_num) VALUES ('305943d779c4') ON CONFLICT DO NOTHING;"
```

### 4.6 Применение миграций

```bash
sudo -u vpvks docker compose run --rm marzban alembic upgrade head
```

---

## 🚀 Шаг 5: Запуск Marzban

```bash
sudo -u vpvks docker compose up -d marzban
```

### Проверка логов

```bash
sudo -u vpvks docker compose logs -f marzban
```

**Ожидаемый результат:**
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## 👤 Шаг 6: Создание администратора

```bash
sudo -u vpvks docker compose exec marzban marzban cli admin create --username admin --password ТВОЙ_ПАРОЛЬ
```

---

## 🌐 Шаг 7: Настройка nginx

### 7.1 Создай конфиг nginx

```bash
nano /etc/nginx/sites-enabled/marzban.conf
```

Вставь:

```nginx
server {
    listen 80;
    server_name marzban.vpvks.ru;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name marzban.vpvks.ru;

    ssl_certificate /etc/letsencrypt/live/vpvks.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vpvks.ru/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    access_log /var/log/nginx/marzban_access.log;
    error_log /var/log/nginx/marzban_error.log;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 7.2 Исправь nginx.conf (если нужно)

```bash
nano /etc/nginx/nginx.conf
```

Добавь в секцию `http {`:

```nginx
server_names_hash_bucket_size 64;
```

### 7.3 Проверь и перезагрузи

```bash
nginx -t && systemctl reload nginx
```

---

## ✅ Шаг 8: Проверка доступа

### 8.1 Открой в браузере

```
https://marzban.vpvks.ru
```

**Логин:** `admin`  
**Пароль:** тот, который создал на шаге 6

### 8.2 Или через SSH туннель

```bash
ssh -L 8000:localhost:8000 root@23.134.216.190
```

Затем открой `http://127.0.0.1:8000`

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

### Ошибка подключения к БД

```bash
# Проверь DATABASE_URL
cat /opt/vpvks/marzban.env | grep DATABASE_URL

# Должно быть: @marzban-db:5432 (не @localhost!)

# Перезапусти
sudo -u vpvks docker compose restart marzban-db marzban
```

### Ошибка миграции Alembic

Смотри **Шаг 4** — ручное исправление миграции.

---

## 📊 Проверка статуса

```bash
# Все сервисы
sudo -u vpvks docker compose ps

# Только Marzban
sudo -u vpvks docker compose ps marzban marzban-db

# Логи
sudo -u vpvks docker compose logs -f marzban
```

**Ожидаемый результат:**
```
NAME                 STATUS
marzban              Up
marzban_postgres     Up (healthy)
```

---

## 🎉 Готово!

Marzban развёрнут и готов к использованию.

**Следующие шаги:**
1. Создай Inbound (VLESS, Trojan, Reality)
2. Создай тестового пользователя
3. Получи ссылку подписки
4. Протестируй подключение
