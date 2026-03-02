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
            }
            
            # Добавляем inbounds если указаны
            if inbounds:
                payload["inbounds"] = inbounds
                logger.info(f"Creating user {username} with inbounds={inbounds}")

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

    def create_user_with_expire(self, username: str, data_limit: int, expire_timestamp: int,
                    protocols: dict = None) -> dict:
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}

        if protocols is None:
            # Включаем оба протокола по умолчанию
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
                "expire": expire_timestamp,
                "inbounds": {
                    "vless": ["VLESS Reality"],
                    "trojan": ["Trojan TLS"]
                }
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
            
            # Проверяем и включаем inbound после создания пользователя
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

    def get_inbounds(self):
        """Получение списка доступных inbounds из Marzban"""
        token = self.get_token()
        if not token:
            logger.error("Failed to get token for inbounds")
            return {"inbounds": {}}

        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                f"{self.base_url}/api/inbounds",
                headers=headers,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            inbounds_data = response.json()
            logger.info(f"Retrieved inbounds: {inbounds_data}")
            return {"inbounds": inbounds_data}
        except Exception as e:
            logger.error(f"Error getting inbounds: {e}")
            return {"inbounds": {}}

    def ensure_inbounds_enabled(self):
        """Проверяет и включает нужные inbound через модификацию конфига Xray"""
        token = self.get_token()
        if not token:
            logger.error("Failed to get token for inbounds check")
            return False

        try:
            headers = {"Authorization": f"Bearer {token}"}
            
            # Получаем список всех inbound через API
            response = requests.get(
                f"{self.base_url}/api/inbounds",
                headers=headers,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            inbounds_data = response.json()
            
            logger.info(f"Retrieved inbounds: {inbounds_data}")
            
            # Проверяем наличие VLESS Reality и Trojan TLS
            inbounds_to_check = ["VLESS Reality", "Trojan TLS"]
            
            for inbound_name in inbounds_to_check:
                found = False
                for group, inbounds_list in inbounds_data.items():
                    if isinstance(inbounds_list, list):
                        for inbound in inbounds_list:
                            if isinstance(inbound, dict) and inbound.get("tag") == inbound_name:
                                found = True
                                is_enabled = inbound.get("enabled", False)
                                logger.info(f"Inbound {inbound_name}: enabled={is_enabled}")
                                
                                if not is_enabled:
                                    logger.warning(f"Inbound {inbound_name} is DISABLED! Please enable it manually in Marzban Dashboard: Settings → Inbounds")
                                break
                    if found:
                        break
                
                if not found:
                    logger.error(f"Inbound {inbound_name} NOT FOUND in Marzban configuration!")
            
            # Возвращаем True если все найдено (даже если выключено)
            # Администратор должен включить inbound один раз вручную в Dashboard
            return True
            
        except Exception as e:
            logger.error(f"Error checking inbounds: {e}")
            return False

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

    def modify_user(self, username: str, data_limit: int = None, expire_days: int = None, inbounds: dict = None) -> dict:
        """Модификация пользователя (продление, изменение лимита, inbounds)"""
        token = self.get_token()
        if not token:
            return {"status": "error", "message": "Failed to get token"}

        try:
            headers = {"Authorization": f"Bearer {token}"}
            payload = {}
            
            if data_limit is not None:
                payload["data_limit"] = data_limit
                
            if expire_days is not None:
                import time
                expire_timestamp = int(time.time()) + (expire_days * 86400)
                payload["expire"] = expire_timestamp
                
            if inbounds is not None:
                payload["inbounds"] = inbounds
            
            logger.info(f"Modifying user {username} with payload: {payload}")
            
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
            logger.error(f"Error modifying user: {e}")
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
