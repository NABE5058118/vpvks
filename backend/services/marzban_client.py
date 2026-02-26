"""
Marzban Client
API клиент для взаимодействия с Marzban панелью (V2Ray/Trojan/Reality)
"""

import requests
import time
import os
import logging
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class MarzbanClient:
    def __init__(self):
        self.base_url = os.getenv('MARZBAN_URL', 'https://127.0.0.1:8000')
        self.username = os.getenv('MARZBAN_ADMIN', 'admin')
        self.password = os.getenv('MARZBAN_PASSWORD', 'j8X0EcIllDwPK')
        self.token = None
        self.token_expiry = 0

    def get_token(self):
        """Получение токена доступа"""
        if self.token and time.time() < self.token_expiry:
            return self.token

        try:
            response = requests.post(
                f"{self.base_url}/api/admin/token",
                data={"username": self.username, "password": self.password},
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            self.token = response.json()["access_token"]
            self.token_expiry = time.time() + 2300
            return self.token
        except Exception as e:
            logger.error(f"Error getting Marzban token: {e}")
            return None

    def create_user(self, username: str, data_limit: int, expire_days: int,
                    protocols: dict = None) -> dict:
        """Создание пользователя в Marzban
        
        Args:
            username: Имя пользователя
            data_limit: Лимит трафика в байтах
            expire_days: Срок действия в днях
            protocols: Протоколы
        """
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}

        if protocols is None:
            protocols = {"vless": {}, "trojan": {}}

        try:
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "username": username,
                "proxies": protocols,
                "data_limit": data_limit,
            }
            
            # Добавляем expire только если не None и > 0
            if expire_days is not None and expire_days > 0:
                import time
                expire_timestamp = int(time.time()) + (expire_days * 86400)
                payload["expire"] = expire_timestamp
                logger.info(f"Creating user {username} with expire={expire_timestamp} ({expire_days} days)")

            response = requests.post(
                f"{self.base_url}/api/user",
                headers=headers,
                json=payload,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                return {"status": "error", "message": "User already exists"}
            logger.error(f"HTTP error creating Marzban user: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Error creating Marzban user: {e}")
            return {"status": "error", "message": str(e)}

    def create_user_with_expire(self, username: str, data_limit: int, expire_timestamp: int,
                    protocols: dict = None) -> dict:
        """Создание пользователя с явным expire timestamp
        
        Args:
            username: Имя пользователя
            data_limit: Лимит трафика в байтах
            expire_timestamp: Unix timestamp когда истекает
            protocols: Протоколы
        """
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}

        if protocols is None:
            protocols = {"vless": {}, "trojan": {}}

        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Проверяем что timestamp правильный (должен быть в будущем)
            import time
            current_time = int(time.time())
            logger.info(f"Current timestamp: {current_time}")
            logger.info(f"Expire timestamp: {expire_timestamp}")
            logger.info(f"Diff: {expire_timestamp - current_time} seconds ({(expire_timestamp - current_time) // 86400} days)")
            
            # Если timestamp в прошлом - используем +3650 дней от сейчас
            if expire_timestamp <= current_time:
                logger.warning("Expire timestamp is in the past! Using current time + 3650 days")
                expire_timestamp = current_time + (3650 * 86400)
            
            payload = {
                "username": username,
                "proxies": protocols,
                "data_limit": data_limit,
                "expire": expire_timestamp  # Явно передаём timestamp
            }
            
            logger.info(f"Final payload: {payload}")

            response = requests.post(
                f"{self.base_url}/api/user",
                headers=headers,
                json=payload,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"User {username} created: {result}")
            
            # Проверяем и включаем inbound
            self.ensure_inbounds_enabled()
            
            return {"status": "success", "data": result}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                return {"status": "error", "message": "User already exists"}
            logger.error(f"HTTP error creating Marzban user: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Error creating Marzban user: {e}")
            return {"status": "error", "message": str(e)}

    def ensure_inbounds_enabled(self):
        """Проверяет и включает нужные inbound (VLESS Reality и Trojan TLS)"""
        token = self.get_token()
        if not token:
            logger.error("Failed to get token for inbounds check")
            return False

        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Получаем список всех inbound
            response = requests.get(
                f"{self.base_url}/api/inbounds",
                headers=headers,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            inbounds = response.json()
            
            logger.info(f"Found inbounds: {list(inbounds.keys())}")
            
            # Нужные inbound
            required_inbounds = {
                "VLESS Reality": {"port": 8443, "protocol": "vless"},
                "Trojan TLS": {"port": 2083, "protocol": "trojan"}
            }
            
            # Проверяем каждый required inbound
            for inbound_name, inbound_info in required_inbounds.items():
                # Ищем inbound в списке
                found = False
                for group, inbounds_list in inbounds.items():
                    for inbound in inbounds_list:
                        if inbound.get("tag") == inbound_name:
                            found = True
                            if not inbound.get("enabled", False):
                                logger.warning(f"Inbound {inbound_name} is disabled! Trying to enable...")
                                # Включаем inbound
                                self.toggle_inbound(inbound_name, True)
                            else:
                                logger.info(f"Inbound {inbound_name} is already enabled")
                            break
                    if found:
                        break
                
                if not found:
                    logger.error(f"Inbound {inbound_name} not found in Marzban configuration!")
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking inbounds: {e}")
            return False

    def toggle_inbound(self, inbound_tag: str, enable: bool) -> dict:
        """Включает или выключает inbound
        
        Args:
            inbound_tag: Название inbound (например "VLESS Reality")
            enable: True для включения, False для выключения
        """
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(
                f"{self.base_url}/api/inbound/{inbound_tag}/toggle",
                headers=headers,
                json={"enabled": enable},
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Inbound {inbound_tag} {'enabled' if enable else 'disabled'}: {result}")
            return {"status": "success", "data": result}
        except Exception as e:
            logger.error(f"Error toggling inbound {inbound_tag}: {e}")
            # Если API toggle не работает, пробуем через update
            return self.update_inbound(inbound_tag, {"enabled": enable})

    def update_inbound(self, inbound_tag: str, updates: dict) -> dict:
        """Обновляет настройки inbound
        
        Args:
            inbound_tag: Название inbound
            updates: Словарь с обновлениями
        """
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}

        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Сначала получаем текущие настройки
            response = requests.get(
                f"{self.base_url}/api/inbound/{inbound_tag}",
                headers=headers,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            current_config = response.json()
            
            # Обновляем настройки
            current_config.update(updates)
            
            # Отправляем обновлённые настройки
            response = requests.put(
                f"{self.base_url}/api/inbound/{inbound_tag}",
                headers=headers,
                json=current_config,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Inbound {inbound_tag} updated: {result}")
            return {"status": "success", "data": result}
        except Exception as e:
            logger.error(f"Error updating inbound {inbound_tag}: {e}")
            return {"status": "error", "message": str(e)}

    def get_subscription_url(self, username: str) -> str:
        """Получение ссылки подписки"""
        token = self.get_token()
        if not token:
            return None
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            # Сначала получаем информацию о пользователе
            response = requests.get(
                f"{self.base_url}/api/user/{username}",
                headers=headers,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            user_data = response.json()
            
            # Извлекаем subscription_url из данных пользователя
            subscription_url = user_data.get('subscription_url', '')
            
            if subscription_url:
                # Если URL относительный (начинается с /), добавляем публичный домен
                if subscription_url.startswith('/'):
                    # Используем публичный домен из переменных окружения
                    public_url = os.getenv('MARZBAN_PUBLIC_URL', 'https://vpvks.ru')
                    return f"{public_url}{subscription_url}"
                return subscription_url
            return None
        except Exception as e:
            logger.error(f"Error getting subscription URL: {e}")
            return None

    def remove_user(self, username: str) -> dict:
        """Удаление пользователя"""
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.delete(
                f"{self.base_url}/api/user/{username}",
                headers=headers,
                timeout=10,
                verify=False
            )
            return {"status": "success", "data": response.json()}
        except Exception as e:
            logger.error(f"Error removing user: {e}")
            return {"status": "error", "message": str(e)}

    def get_user(self, username: str) -> dict:
        """Получение информации о пользователе"""
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{self.base_url}/api/user/{username}",
                headers=headers,
                timeout=10,
                verify=False
            )
            if response.status_code == 404:
                return {"status": "not_found"}
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return {"status": "error", "message": str(e)}
