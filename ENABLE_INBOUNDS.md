# 🚀 АВТОМАТИЧЕСКОЕ ВКЛЮЧЕНИЕ INBOUND

## Быстрая активация (ОДИН РАЗ):

```bash
# На сервере
cd /opt/vpvks

# Запустить скрипт
python3 enable_inbounds.py
```

Скрипт:
- ✅ Подключится к Marzban API
- ✅ Включит **VLESS Reality** (порт 8443)
- ✅ Включит **Trojan TLS** (порт 2083)

---

## Если скрипт не работает — вручную через Dashboard:

1. Зайди в **https://marzban.vpvks.ru/dashboard/**
2. **Settings** → **Inbounds**
3. **VLESS Reality** → переключи в **Enabled** ✓
4. **Trojan TLS** → переключи в **Enabled** ✓
5. **Save**

---

## Проверка:

```bash
# Проверить что порты слушают
ss -tulpn | grep -E "8443|2083"

# Должно быть:
# tcp   LISTEN 0  4096  *:8443  *:*  users:(("xray",...))
# tcp   LISTEN 0  4096  *:2083  *:*  users:(("xray",...))
```

---

## После активации:

1. **Удали** старых пользователей в Marzban
2. **Создай новых** через бота: `/start` → "🔑 Мои ключи" → V2Ray
3. **Вставь ссылку** в Hiddify/v2rayNG
4. **Подключайся!**

---

## 🔑 Порты для firewall:

```bash
ufw allow 8443/tcp
ufw allow 2083/tcp
ufw reload
```
