# 📡 Настройка Marzban для продажи VPN ключей

> **Цель:** Настроить Marzban для выдачи ключей v2ray, Trojan, Reality для клиентов (v2rayNG, Hiddify, V2Box, Streisand)

---

## 📋 Шаг 1: Проверка текущего состояния

Выполни на сервере:

```bash
cd /opt/vpvks
docker compose ps
docker compose logs marzban --tail=30
ss -tulpn | grep 8000
```

---

## 📋 Шаг 2: Настройка Xray конфигурации

Создай файл `/var/lib/marzban/xray_config.json`:

```bash
cat > /var/lib/marzban/xray_config.json << 'EOF'
{
  "log": {
    "loglevel": "warning"
  },
  "inbounds": [
    {
      "tag": "VLESS Reality",
      "port": 443,
      "protocol": "vless",
      "settings": {
        "clients": [],
        "decryption": "none"
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": {
          "show": false,
          "dest": "google.com:443",
          "xver": 0,
          "serverNames": ["google.com", "www.google.com"],
          "privateKey": "YOUR_PRIVATE_KEY",
          "shortIds": ["", "abc123"]
        }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls"]
      }
    },
    {
      "tag": "Trojan",
      "port": 8443,
      "protocol": "trojan",
      "settings": {
        "clients": []
      },
      "streamSettings": {
        "network": "tcp",
        "security": "tls",
        "tlsSettings": {
          "certificates": [
            {
              "certificateFile": "/etc/letsencrypt/live/vpvks.ru/fullchain.pem",
              "keyFile": "/etc/letsencrypt/live/vpvks.ru/privkey.pem"
            }
          ]
        }
      },
      "sniffing": {
        "enabled": true,
        "destOverride": ["http", "tls"]
      }
    }
  ],
  "outbounds": [
    {
      "protocol": "freedom",
      "tag": "direct"
    },
    {
      "protocol": "blackhole",
      "tag": "blocked"
    }
  ],
  "routing": {
    "rules": [
      {
        "type": "field",
        "ip": ["geoip:private"],
        "outboundTag": "blocked"
      }
    ]
  }
}
EOF
```

---

## 📋 Шаг 3: Генерация ключей Reality

```bash
# Генерация приватного ключа для Reality
docker exec marzban xray x25519

# Вывод:
# Private key: <скопируй это>
# Public key: <скопируй это>
```

Замени в `xray_config.json`:
- `"privateKey": "YOUR_PRIVATE_KEY"` → на сгенерированный ключ
- Добавь public key в настройки inbound

---

## 📋 Шаг 4: Настройка через панель Marzban

### 4.1 Вход в панель

```
URL: https://marzban.vpvks.ru/dashboard/
Логин: admin
Пароль: j8X0EcIllDwPK
```

### 4.2 Создание Inbounds

**Inbounds → Create New Inbound → VLESS Reality:**

```yaml
Title: VLESS Reality
Port: 443
Protocol: VLESS
Network: TCP
Security: Reality

Reality Settings:
  - Destination: google.com:443
  - Server Names: google.com, www.google.com
  - Private Key: <из шага 3>
  - Short IDs: (оставь пустым или сгенерируй)
```

**Inbounds → Create New Inbound → Trojan:**

```yaml
Title: Trojan TLS
Port: 8443
Protocol: Trojan
Security: TLS

TLS Settings:
  - Certificate: /etc/letsencrypt/live/vpvks.ru/fullchain.pem
  - Key: /etc/letsencrypt/live/vpvks.ru/privkey.pem
```

### 4.3 Настройка Hosts

**Settings → Hosts:**

```
Domain: vpvks.ru
Port: 443
```

### 4.4 Создание User Templates (Тарифы)

**User Templates → Create Template:**

| Название | Трафик | Время | Описание |
|----------|--------|-------|----------|
| Start | 10 GB | 30 дней | Пробный |
| Standard | 50 GB | 30 дней | Популярный |
| Premium | 100 GB | 30 дней | Максимум |
| Unlimited | 0 (безлим) | 30 дней | Без ограничений |

**Пример настроек для Standard:**
```
Data Limit: 53687091200 (50 GB)
Expire Days: 30
Enabled Protocols: VLESS, Trojan
```

---

## 📋 Шаг 5: Тестирование создания пользователя

### 5.1 Вручную через панель

1. **Users → Create User**
2. Заполни:
   - Username: `testuser`
   - Template: Standard
   - Protocols: VLESS, Trojan
3. **Create**
4. Скопируй ссылку подписки

### 5.2 Через API (для бота)

```bash
# Получить токен админа
TOKEN=$(curl -s -X POST "https://marzban.vpvks.ru/api/admin/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=j8X0EcIllDwPK" | jq -r '.access_token')

# Создать пользователя
curl -X POST "https://marzban.vpvks.ru/api/user" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser123",
    "proxies": ["vless", "trojan"],
    "data_limit": 53687091200,
    "expire": 1743000000
  }'

# Получить ссылку подписки
curl -X GET "https://marzban.vpvks.ru/api/user/testuser123/subscription" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 📋 Шаг 6: Интеграция с Mini App

### 6.1 API endpoints для backend

```python
# backend/marzban_client.py

import requests

class MarzbanClient:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = None
    
    def get_token(self):
        """Получение токена доступа"""
        response = requests.post(
            f"{self.base_url}/api/admin/token",
            data={"username": self.username, "password": self.password}
        )
        self.token = response.json()["access_token"]
        return self.token
    
    def create_user(self, username, data_limit, expire, protocols=["vless", "trojan"]):
        """Создание пользователя"""
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "username": username,
            "proxies": protocols,
            "data_limit": data_limit,  # в байтах
            "expire": expire  # Unix timestamp
        }
        response = requests.post(
            f"{self.base_url}/api/user",
            headers=headers,
            json=payload
        )
        return response.json()
    
    def get_subscription(self, username):
        """Получение ссылки подписки"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{self.base_url}/api/user/{username}/subscription",
            headers=headers
        )
        return response.text
    
    def remove_user(self, username):
        """Удаление пользователя"""
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.delete(
            f"{self.base_url}/api/user/{username}",
            headers=headers
        )
        return response.json()
```

### 6.2 Пример использования в боте

```python
# bot/handlers/payment.py

marzban = MarzbanClient(
    base_url="https://marzban.vpvks.ru",
    username="admin",
    password="j8X0EcIllDwPK"
)

async def activate_vpn(user_id, tariff):
    """Активация VPN после оплаты"""
    
    # Тарифы
    tariffs = {
        "start": {"limit": 10 * 1024**3, "days": 30},
        "standard": {"limit": 50 * 1024**3, "days": 30},
        "premium": {"limit": 100 * 1024**3, "days": 30},
    }
    
    tariff_data = tariffs[tariff]
    username = f"user_{user_id}"
    expire = int(time.time()) + (tariff_data["days"] * 86400)
    
    # Получить токен
    marzban.get_token()
    
    # Создать пользователя
    user = marzban.create_user(
        username=username,
        data_limit=tariff_data["limit"],
        expire=expire
    )
    
    # Получить ссылку
    subscription = marzban.get_subscription(username)
    
    return subscription
```

---

## 📋 Шаг 7: Проверка работы ключей

### 7.1 Тест в клиенте

1. Скопируй ссылку подписки (начинается на `https://...`)
2. Вставь в v2rayNG / Hiddify / V2Box
3. Подключись
4. Проверь IP: `https://2ip.ru`

### 7.2 Мониторинг трафика

```bash
# Логи пользователей
docker compose logs marzban | grep "user_"

# Статистика через API
curl -H "Authorization: Bearer $TOKEN" \
  "https://marzban.vpvks.ru/api/user/testuser123"
```

---

## 🔧 Troubleshooting

### Ошибка: "Connection refused" на порт 8000

```bash
# Проверь статус Marzban
docker compose ps marzban

# Перезапусти
docker compose restart marzban

# Проверь логи
docker compose logs marzban | tail -50
```

### Ошибка: "Invalid Xray config"

```bash
# Проверь синтаксис JSON
cat /var/lib/marzban/xray_config.json | jq .

# Перезапусти Marzban
docker compose restart marzban
```

### Ошибка: "SSL certificate not found"

```bash
# Проверь сертификаты
ls -la /etc/letsencrypt/live/vpvks.ru/

# Обнови SSL
certbot renew
```

---

## 📊 Ссылки для клиентов

| Клиент | Платформа | Ссылка |
|--------|-----------|--------|
| v2rayNG | Android | [Google Play](https://play.google.com/store/apps/details?id=com.v2ray.ang) |
| Hiddify | iOS/Android | [GitHub](https://github.com/hiddify/hiddify-next) |
| V2Box | iOS | [App Store](https://apps.apple.com/app/v2box-v2ray-client/id6447129396) |
| Streisand | iOS | [App Store](https://apps.apple.com/app/streisand/id6450534064) |
| Nekobox | Android | [GitHub](https://github.com/MatsuriDayo/nekoray) |

---

*Документ создан: 22 февраля 2026 г.*
