"""Marzban API client"""

import requests
import time
import os
import logging
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class MarzbanClient:
    def __init__(self):
        # URL по умолчанию — контейнер Marzban в той же Docker-сети
        self.base_url = os.getenv('MARZBAN_URL', 'http://marzban:8000')
        self.username = os.getenv('MARZBAN_ADMIN', 'admin')
        self.password = os.getenv('MARZBAN_PASSWORD')
        self.token = None
        self.token_expiry = 0

        if not self.password:
            logger.warning("MARZBAN_PASSWORD not set. Marzban integration will not work.")

    def get_token(self):
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
                    protocols: dict = None, inbounds: dict = None) -> dict:
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
                "inbounds": {
                    "vless": ["VLESS Reality"],
                    "trojan": ["Trojan TLS"]
                }
            }

            if inbounds:
                payload["inbounds"] = inbounds

            if expire_days is not None and expire_days > 0:
                import time
                expire_timestamp = int(time.time()) + (expire_days * 86400)
                payload["expire"] = expire_timestamp

            response = requests.post(
                f"{self.base_url}/api/user",
                headers=headers,
                json=payload,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            result = response.json()
            return {"status": "success", "data": result}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 409:
                return {"status": "error", "message": f"User {username} already exists"}
            logger.error(f"HTTP error creating Marzban user: {e}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Error creating Marzban user: {e}")
            return {"status": "error", "message": str(e)}

    def get_subscription_url(self, username: str) -> str:
        token = self.get_token()
        if not token:
            return ""

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{self.base_url}/api/user/{username}",
                headers=headers,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            user_data = response.json()
            subscription_url = user_data.get('subscription_url', '')

            if subscription_url:
                if subscription_url.startswith('/'):
                    public_url = os.getenv('MARZBAN_PUBLIC_URL', self.base_url)
                    return f"{public_url}{subscription_url}"
                return subscription_url
            return ""
        except Exception as e:
            logger.error(f"Error getting subscription URL: {e}")
            return ""

    def remove_user(self, username: str) -> dict:
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
            response.raise_for_status()
            return {"status": "success", "message": f"User {username} removed"}
        except Exception as e:
            logger.error(f"Error removing user: {e}")
            return {"status": "error", "message": str(e)}

    def modify_user(self, username: str, data: dict) -> dict:
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.put(
                f"{self.base_url}/api/user/{username}",
                headers=headers,
                json=data,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            logger.error(f"Error modifying user: {e}")
            return {"status": "error", "message": str(e)}

    def get_user(self, username: str) -> dict:
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
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return {"status": "error", "message": str(e)}

    def extend_user(self, username: str, days: int) -> dict:
        """Продление подписки пользователя в Marzban"""
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}

        try:
            headers = {"Authorization": f"Bearer {token}"}
            import time
            expire_timestamp = int(time.time()) + (days * 86400)

            payload = {
                "expire": expire_timestamp
            }

            response = requests.put(
                f"{self.base_url}/api/user/{username}",
                headers=headers,
                json=payload,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            return {"status": "success", "data": response.json()}
        except Exception as e:
            logger.error(f"Error extending user: {e}")
            return {"status": "error", "message": str(e)}
