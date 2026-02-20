# Marzban Setup

## Установка на сервере

### 1. Создать директорию и файлы

```bash
mkdir -p /opt/marzban
cd /opt/marzban
chown -R vpvks:vpvks /opt/marzban
```

### 2. Создать .env файл

```bash
sudo -u vpvks nano .env
```

Вставить:

```env
# Database (PostgreSQL)
POSTGRES_DB=marzban
POSTGRES_USER=marzban
POSTGRES_PASSWORD=MarzbanPass123!
DATABASE_URL=postgresql://marzban:MarzbanPass123!@localhost:5433/marzban
SQLALCHEMY_DATABASE_URL=postgresql://marzban:MarzbanPass123!@localhost:5433/marzban

# Security
SECRET_KEY=7c1ac2b949198c0d8ac414776fd11b6beac83fb0a86acc9f1859c05384b717b5

# Subscription
SUBSCRIPTION_URL_PREFIX=https://vpvks.ru

# UVICORN workers
UVICORN_WORKERS=2

# Xray config
XRAY_JSON=/var/lib/marzban/xray_config.json

# Marzban host/port
MARZBAN_HOST=127.0.0.1
MARZBAN_PORT=8000
```

### 3. Запустить Marzban

```bash
# Запусти контейнеры (от vpvks)
sudo -u vpvks docker compose up -d

# Проверь статус
sudo -u vpvks docker compose ps

# Посмотри логи
sudo -u vpvks docker compose logs -f marzban
```

### 4. Создать админа

```bash
sudo -u vpvks docker exec -it marzban python -c "
from app.db import GetDB
from app.models.admin import Admin
from app.utils.crypto import get_password_hash

with GetDB() as db:
    admin = Admin(
        username='admin',
        hashed_password=get_password_hash('ТВОЙ_ПАРОЛЬ_123'),
        is_sudo=True
    )
    db.add(admin)
    db.commit()
    print('✅ Admin created successfully!')
"
```

## Доступ к панели

### Через nginx (рекомендуется)

1. Исправь `/etc/nginx/nginx.conf`:
```nginx
http {
    server_names_hash_bucket_size 64;
    # ...
}
```

2. Создай `/etc/nginx/sites-enabled/marzban.conf`:
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

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. Перезагрузи nginx:
```bash
nginx -t && systemctl reload nginx
```

4. Открой в браузере: `https://marzban.vpvks.ru`

### Через SSH туннель

```bash
ssh -L 8000:localhost:8000 root@23.134.216.190
```

Затем открой `http://127.0.0.1:8000` на компьютере.

## Команды управления

```bash
# Перезапуск
sudo -u vpvks docker compose restart

# Остановка
sudo -u vpvks docker compose down

# Обновление
sudo -u vpvks docker compose pull
sudo -u vpvks docker compose up -d

# Логи
sudo -u vpvks docker compose logs -f marzban

# Создать админа
sudo -u vpvks docker exec -it marzban python -c "..."

# Удалить админа
sudo -u vpvks docker exec -it marzban marzban cli admin remove --username admin
```

## Поддерживаемые протоколы

- ✅ V2Ray (VMess, VLESS)
- ✅ Trojan
- ✅ Shadowsocks
- ✅ Reality (для обхода блокировок)

## Интеграция с Telegram ботом

После настройки Marzban нужно обновить бота для поддержки V2Ray/Trojan.
