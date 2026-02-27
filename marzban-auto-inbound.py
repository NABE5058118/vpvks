#!/usr/bin/env python3
"""
Auto-enable Marzban Inbounds
Запускается автоматически при старте контейнера Marzban
"""

import requests
import urllib3
import time
import os
import logging

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('marzban-auto-inbound')

# Настройки из переменных окружения или по умолчанию
MARZBAN_URL = os.getenv('MARZBAN_URL', 'https://127.0.0.1:8000')
ADMIN_USERNAME = os.getenv('MARZBAN_ADMIN', 'admin')
ADMIN_PASSWORD = os.getenv('MARZBAN_PASSWORD', '')

def get_token(max_retries=5):
    """Получение токена администратора с повторными попытками"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{MARZBAN_URL}/api/admin/token",
                data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
                verify=False,
                timeout=10
            )
            if response.status_code == 200:
                return response.json()["access_token"]
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: Failed to get token")
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries}: {e}")
        
        time.sleep(2)
    
    return None

def enable_inbound(token, inbound_tag):
    """Включение inbound"""
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # Получаем текущие inbound
        response = requests.get(
            f"{MARZBAN_URL}/api/inbounds",
            headers=headers,
            verify=False,
            timeout=10
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to get inbounds: {response.text}")
            return False
        
        inbounds = response.json()
        
        # Ищем нужный inbound
        for group, inbounds_list in inbounds.items():
            for inbound in inbounds_list:
                if isinstance(inbound, dict) and inbound.get("tag") == inbound_tag:
                    if inbound.get("enabled", False):
                        logger.info(f"✓ {inbound_tag} already enabled")
                        return True
                    
                    # Пытаемся включить через API
                    logger.info(f"Enabling {inbound_tag}...")
                    
                    # Пробуем разные методы включения
                    # Метод 1: Через toggle endpoint
                    try:
                        response = requests.post(
                            f"{MARZBAN_URL}/api/inbound/{inbound_tag}/toggle",
                            headers=headers,
                            json={"enabled": True},
                            verify=False,
                            timeout=10
                        )
                        if response.status_code == 200:
                            logger.info(f"✅ {inbound_tag} enabled via toggle API")
                            return True
                    except Exception as e:
                        logger.warning(f"Toggle API failed: {e}")
                    
                    # Метод 2: Через modification endpoint
                    try:
                        # Получаем полную конфигурацию inbound
                        response = requests.get(
                            f"{MARZBAN_URL}/api/inbound/{inbound_tag}",
                            headers=headers,
                            verify=False,
                            timeout=10
                        )
                        if response.status_code == 200:
                            config = response.json()
                            config['enabled'] = True
                            
                            response = requests.put(
                                f"{MARZBAN_URL}/api/inbound/{inbound_tag}",
                                headers=headers,
                                json=config,
                                verify=False,
                                timeout=10
                            )
                            if response.status_code == 200:
                                logger.info(f"✅ {inbound_tag} enabled via update API")
                                return True
                    except Exception as e:
                        logger.warning(f"Update API failed: {e}")
                    
                    logger.error(f"❌ Failed to enable {inbound_tag}")
                    return False
        
        logger.error(f"❌ Inbound {inbound_tag} not found")
        return False
        
    except Exception as e:
        logger.error(f"Error enabling {inbound_tag}: {e}")
        return False

def main():
    logger.info("=" * 50)
    logger.info("🔧 Marzban Auto-Inbound Enabler")
    logger.info("=" * 50)
    
    if not ADMIN_PASSWORD:
        logger.error("❌ MARZBAN_PASSWORD not set!")
        return
    
    # Ждём пока Marzban запустится
    logger.info("Waiting for Marzban to start...")
    time.sleep(5)
    
    token = get_token()
    if not token:
        logger.error("❌ Failed to get admin token!")
        logger.error(f"Check credentials: username='{ADMIN_USERNAME}'")
        return
    
    logger.info("✓ Admin token obtained")
    
    # Включаем нужные inbound
    inbounds_to_enable = [
        "VLESS Reality",
        "Trojan TLS"
    ]
    
    success_count = 0
    for inbound in inbounds_to_enable:
        if enable_inbound(token, inbound):
            success_count += 1
    
    logger.info("=" * 50)
    logger.info(f"✅ Enabled {success_count}/{len(inbounds_to_enable)} inbounds")
    logger.info("=" * 50)

if __name__ == "__main__":
    main()
