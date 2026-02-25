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
            payload = {
                "username": username,
                "proxies": protocols,
                "data_limit": data_limit,
                "expire": expire_timestamp  # Явно передаём timestamp
            }
            
            logger.info(f"Creating user {username} with expire={expire_timestamp}")
            logger.info(f"Payload: {payload}")

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
            return {"status": "success", "data": result}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                return {"status": "error", "message": "User already exists"}
            logger.error(f"HTTP error creating Marzban user: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Error creating Marzban user: {e}")
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
