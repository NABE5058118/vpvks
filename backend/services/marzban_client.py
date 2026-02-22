"""
Marzban Client
API клиент для взаимодействия с Marzban панелью (V2Ray/Trojan/Reality)
"""

import requests
import time
import os
import logging

logger = logging.getLogger(__name__)


class MarzbanClient:
    def __init__(self):
        self.base_url = os.getenv('MARZBAN_URL', 'http://127.0.0.1:8000')
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
                timeout=10
            )
            response.raise_for_status()
            self.token = response.json()["access_token"]
            self.token_expiry = time.time() + 2300  # Токен живёт ~30 мин
            return self.token
        except Exception as e:
            logger.error(f"Error getting Marzban token: {e}")
            return None
    
    def create_user(self, username: str, data_limit: int, expire_days: int, 
                    protocols: list = ["vless", "trojan"]) -> dict:
        """Создание пользователя в Marzban"""
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            payload = {
                "username": username,
                "proxies": protocols,
                "data_limit": data_limit,
                "expire": int(time.time()) + (expire_days * 86400)
            }
            
            response = requests.post(
                f"{self.base_url}/api/user",
                headers=headers,
                json=payload,
                timeout=10
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
    
    def get_subscription_url(self, username: str) -> str:
        """Получение ссылки подписки"""
        token = self.get_token()
        if not token:
            return None
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{self.base_url}/api/user/{username}/subscription",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.text
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
                timeout=10
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
                timeout=10
            )
            if response.status_code == 404:
                return {"status": "not_found"}
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return {"status": "error", "message": str(e)}
    
    def modify_user(self, username: str, data_limit: int = None, expire_days: int = None,
                    protocols: list = None) -> dict:
        """Модификация пользователя"""
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            payload = {}
            
            if data_limit is not None:
                payload["data_limit"] = data_limit
            if expire_days is not None:
                payload["expire"] = int(time.time()) + (expire_days * 86400)
            if protocols is not None:
                payload["proxies"] = protocols
            
            response = requests.put(
                f"{self.base_url}/api/user/{username}",
                headers=headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            logger.error(f"Error modifying user: {e}")
            return {"status": "error", "message": str(e)}
    
    def revoke_user_subscription(self, username: str) -> dict:
        """Отзыв подписки пользователя (сброс ключей)"""
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}
        
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(
                f"{self.base_url}/api/user/{username}/revoke-sub",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            logger.error(f"Error revoking subscription: {e}")
            return {"status": "error", "message": str(e)}
