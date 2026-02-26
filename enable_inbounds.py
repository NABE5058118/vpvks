#!/usr/bin/env python3
"""
Скрипт для включения inbound в Marzban
Запускается один раз после развёртывания
"""

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройки
MARZBAN_URL = "https://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "j8X0EcIllDwPK"

def get_token():
    """Получение токена администратора"""
    response = requests.post(
        f"{MARZBAN_URL}/api/admin/token",
        data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        verify=False
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    return None

def enable_inbound(token, inbound_tag):
    """Включение inbound через модификацию конфига"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Получаем текущие inbound
    response = requests.get(
        f"{MARZBAN_URL}/api/inbounds",
        headers=headers,
        verify=False
    )
    
    if response.status_code != 200:
        print(f"❌ Не удалось получить inbound: {response.text}")
        return False
    
    inbounds = response.json()
    print(f"✓ Получены inbound: {list(inbounds.keys())}")
    
    # Ищем нужный inbound и включаем
    for group, inbounds_list in inbounds.items():
        for inbound in inbounds_list:
            if inbound.get("tag") == inbound_tag:
                if inbound.get("enabled"):
                    print(f"✓ {inbound_tag} уже включён")
                    return True
                
                # Включаем через API
                print(f"⚙️ Включаем {inbound_tag}...")
                
                # Marzban API для включения inbound
                response = requests.post(
                    f"{MARZBAN_URL}/api/inbound/{inbound_tag}/toggle",
                    headers=headers,
                    json={"enabled": True},
                    verify=False
                )
                
                if response.status_code == 200:
                    print(f"✅ {inbound_tag} успешно включён!")
                    return True
                else:
                    print(f"❌ Ошибка включения {inbound_tag}: {response.text}")
                    return False
    
    print(f"❌ Inbound {inbound_tag} не найден!")
    return False

def main():
    print("🔧 Marzban Inbound Activator")
    print("=" * 40)
    
    token = get_token()
    if not token:
        print("❌ Не удалось получить токен!")
        print(f"Проверьте логин/пароль в скрипте:")
        print(f"  ADMIN_USERNAME = '{ADMIN_USERNAME}'")
        print(f"  ADMIN_PASSWORD = '{ADMIN_PASSWORD}'")
        return
    
    print("✓ Токен получен")
    
    # Включаем нужные inbound
    inbounds_to_enable = ["VLESS Reality", "Trojan TLS"]
    
    for inbound in inbounds_to_enable:
        enable_inbound(token, inbound)
        print()
    
    print("=" * 40)
    print("✅ Готово! Теперь пользователи смогут подключаться")
    print()
    print("📱 Для подключения используйте:")
    print("   VLESS Reality: порт 8443")
    print("   Trojan TLS: порт 2083")

if __name__ == "__main__":
    main()
