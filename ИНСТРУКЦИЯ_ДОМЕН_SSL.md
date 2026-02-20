# Полная инструкция: Домен + SSL + Настройка продакшена

## 📋 Обзор процесса

```
1. Покупка домена (~5 мин)
2. Настройка DNS (~5 мин + ожидание 1-24 часа)
3. Установка Certbot (~2 мин)
4. Получение SSL-сертификата (~5 мин)
5. Настройка nginx (~10 мин)
6. Обновление конфигурации проекта (~5 мин)
7. Финальная проверка (~5 мин)
```

**Общее время:** ~30-40 минут (не считая ожидания DNS)

---

## Шаг 1: Покупка домена

### 1.1 Выбери регистратора

| Регистратор | Ссылка | Цена .ru |
|-------------|--------|----------|
| Reg.ru | https://www.reg.ru/ | ~299₽/год |
| Nic.ru | https://www.nic.ru/ | ~349₽/год |
| Beget | https://beget.ru/ | ~295₽/год |

### 1.2 Проверь доступность

Введи желаемое имя в поиске на сайте регистратора:
```
vpn-[твоё-имя].ru
[бренд]-vpn.ru
```

### 1.3 Зарегистрируй домен

1. Нажми «Купить» / «Зарегистрировать»
2. Заполни паспортные данные (обязательно для .ru)
3. Оплати (~300₽)
4. Подтверди email

**Готово!** Домен твой. Переходи к шагу 2.

---

## Шаг 2: Настройка DNS

### 2.1 Зайди в панель управления доменом

- **Reg.ru:** Личный кабинет → Мои домены → [твой домен] → DNS-серверы
- **Nic.ru:** Личный кабинет → Домены → [твой домен] → Управление зоной DNS

### 2.2 Добавь A-запись

| Поле | Значение |
|------|----------|
| **Тип записи** | `A` |
| **Subdomain / Host** | `@` (или оставь пустым) |
| **IP адрес / Points to** | `23.134.216.190` |
| **TTL** | `3600` (или по умолчанию) |

### 2.3 Добавь A-запись для поддомена (опционально)

Если хочешь использовать `vpn.твой-домен.ru`:

| Поле | Значение |
|------|----------|
| **Тип записи** | `A` |
| **Subdomain / Host** | `vpn` |
| **IP адрес / Points to** | `23.134.216.190` |
| **TTL** | `3600` |

### 2.4 Сохрани изменения

Нажми **«Сохранить»** / **«Применить»**

### 2.5 Ожидание применения DNS

⏳ **DNS обновляется от 1 до 24 часов** (обычно 1-4 часа)

**Проверь применение:**
```bash
# Замени yourdomain.ru на свой домен
ping yourdomain.ru
# Должен ответить: 23.134.216.190

# Или через nslookup
nslookup yourdomain.ru
```

---

## Шаг 3: Подключение к серверу

```bash
# Подключись к серверу по SSH
ssh root@23.134.216.190

# Или через панель хостинга (консоль)
```

---

## Шаг 4: Установка Certbot

```bash
# Обнови пакеты
sudo apt update && sudo apt upgrade -y

# Установи Certbot и плагин для nginx
sudo apt install certbot python3-certbot-nginx -y

# Проверь установку
certbot --version
# Должно вывести: certbot 2.x.x
```

---

## Шаг 5: Получение SSL-сертификата

### 5.1 Убедись, что nginx запущен

```bash
sudo systemctl status nginx
# Должен быть active (running)

# Если не запущен:
sudo systemctl start nginx
```

### 5.2 Получи сертификат

```bash
# Замени yourdomain.ru на свой домен
sudo certbot --nginx -d yourdomain.ru -d www.yourdomain.ru
```

### 5.3 Пройди интерактивную настройку

Certbot задаст вопросы:

| Вопрос | Ответ |
|--------|-------|
| **Enter email address** | Введи свой email (для уведомлений) |
| **Terms of Service** | `A` (Agree) |
| **Share email with EFF** | `Y` или `N` (по желанию) |
| **Redirect HTTP to HTTPS** | `2` (Redirect — рекомендуется) |

### 5.4 Проверь результат

```bash
# Сертификаты сохранены в:
ls -la /etc/letsencrypt/live/yourdomain.ru/

# Должны быть файлы:
# - fullchain.pem
# - privkey.pem
# - cert.pem
# - chain.pem
```

**Готово!** SSL-сертификат получен.

---

## Шаг 6: Настройка nginx

### 6.1 Создай конфигурацию nginx

```bash
sudo nano /etc/nginx/sites-available/vpnn
```

### 6.2 Вставь конфигурацию

```nginx
server {
    listen 80;
    server_name yourdomain.ru www.yourdomain.ru;
    
    # Перенаправление на HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.ru www.yourdomain.ru;

    # SSL-сертификаты (Certbot автоматически обновит пути)
    ssl_certificate /etc/letsencrypt/live/yourdomain.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.ru/privkey.pem;

    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Логирование
    access_log /var/log/nginx/vpnn_access.log;
    error_log /var/log/nginx/vpnn_error.log;

    # Backend (Flask на порту 8080)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket (если нужен)
    location /ws {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Замени `yourdomain.ru` на свой домен!**

### 6.3 Активируй конфигурацию

```bash
# Создай символическую ссылку
sudo ln -s /etc/nginx/sites-available/vpnn /etc/nginx/sites-enabled/

# Удали дефолтную конфигурацию (если есть)
sudo rm -f /etc/nginx/sites-enabled/default

# Проверь конфигурацию на ошибки
sudo nginx -t

# Если всё ок, перезапусти nginx
sudo systemctl restart nginx

# Проверь статус
sudo systemctl status nginx
```

---

## Шаг 7: Обновление конфигурации проекта

### 7.1 Обнови `bot/.env`

```bash
nano /opt/vpnn/bot/.env
```

```env
TELEGRAM_BOT_TOKEN=7543289159:AAGslISwjNM2Jys619vk25bDH_Az7t2vMa8
BACKEND_URL=https://yourdomain.ru
ADMIN_USER_IDS=699469085
DATABASE_URL=postgresql://vpn_bot_user:пароль@localhost/vpn_bot_db
MINI_APP_URL=https://yourdomain.ru/miniapp
```

### 7.2 Обнови `backend/.env`

```bash
nano /opt/vpnn/backend/.env
```

```env
YOOKASSA_SHOP_ID=1268375
YOOKASSA_SECRET_KEY=test_D_4q_NKAypyB9hN_CWzru9rAGZNNkALoKrhzGPB3sdc
YOOKASSA_TEST_MODE=true
YOOKASSA_RETURN_URL=https://yourdomain.ru/payment-success
DATABASE_URL=postgresql://vpn_bot_user:пароль@localhost/vpn_bot_db
```

**Замени `yourdomain.ru` на свой домен!**

### 7.3 Перезапусти сервисы

```bash
# Перезапусти бот
cd /opt/vpnn/bot
# Останови старого бота (Ctrl+C или kill)
python3 main.py &

# Перезапусти backend
cd /opt/vpnn/backend
# Останови старый backend (Ctrl+C или kill)
PORT=8080 python3 server.py &
```

---

## Шаг 8: Финальная проверка

### 8.1 Проверь HTTPS

```bash
# Проверь ответ сервера
curl -I https://yourdomain.ru

# Должен быть статус 200 или 301/302
```

### 8.2 Проверь SSL-сертификат

```bash
# Проверь сертификат
echo | openssl s_client -connect yourdomain.ru:443 -servername yourdomain.ru 2>/dev/null | openssl x509 -noout -dates

# Должны быть даты действия сертификата
```

Или открой в браузере: `https://yourdomain.ru` — должен быть замок 🔒

### 8.3 Проверь API

```bash
# Проверь endpoint
curl https://yourdomain.ru/api/status
```

### 8.4 Проверь мини-приложение

Открой в Telegram или браузере: `https://yourdomain.ru/miniapp`

### 8.5 Проверь бота

Запусти `@relatevpnbot` в Telegram:
- `/start` — должен работать
- `/app` — должно открывать мини-приложение

---

## Шаг 9: Автообновление SSL-сертификата

Certbot автоматически создаёт cron-задачу, но проверь:

```bash
# Проверь автообновление
sudo systemctl list-timers | grep certbot

# Должен быть certbot.timer active

# Протестируй обновление (сухой запуск)
sudo certbot renew --dry-run
```

**Сертификат обновляется автоматически каждые 90 дней.**

---

## 🎉 Готово!

### Чек-лист выполненных задач:

- [x] Домен куплен
- [x] DNS настроены
- [x] SSL-сертификат получен
- [x] nginx настроен
- [x] Конфигурация обновлена
- [x] HTTPS работает
- [x] Автообновление SSL настроено

---

## 🔧 Полезные команды

```bash
# Проверка статуса nginx
sudo systemctl status nginx

# Перезапуск nginx
sudo systemctl restart nginx

# Логи nginx
sudo tail -f /var/log/nginx/vpnn_access.log
sudo tail -f /var/log/nginx/vpnn_error.log

# Проверка SSL
sudo certbot certificates

# Принудительное обновление SSL
sudo certbot renew --force-renewal

# Проверка портов
sudo ss -tulpn | grep :443
sudo ss -tulpn | grep :80
```

---

## 🆘 Если что-то пошло не так

### Проблема: DNS не применяется

**Решение:** Подожди до 24 часов. Проверь через:
```bash
nslookup yourdomain.ru
```

### Проблема: Certbot не может получить сертификат

**Решение:**
1. Убедись, что DNS применяется (`ping yourdomain.ru`)
2. Убедись, что порт 80 открыт:
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw status
   ```
3. Убедись, что nginx запущен:
   ```bash
   sudo systemctl status nginx
   ```

### Проблема: nginx не запускается

**Решение:**
```bash
# Проверь ошибки
sudo nginx -t
sudo journalctl -u nginx

# Исправь ошибки в конфиге
sudo nano /etc/nginx/sites-available/vpnn
```

### Проблема: HTTPS не работает

**Решение:**
1. Проверь, что порт 443 открыт:
   ```bash
   sudo ufw allow 443/tcp
   ```
2. Проверь конфиг nginx:
   ```bash
   sudo nginx -t
   ```

---

## 📞 Контакты для помощи

- Certbot документация: https://certbot.eff.org/
- nginx документация: https://nginx.org/en/docs/
- Reg.ru поддержка: https://www.reg.ru/support/
