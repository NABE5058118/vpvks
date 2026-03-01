"""
VPN Service
Handles VPN connection logic with Marzban (V2Ray/Trojan/Reality)
"""

import os
from datetime import datetime
import sys
import logging

# Add the parent directory to the path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User
from services.marzban_client import MarzbanClient

logger = logging.getLogger(__name__)


class VPNService:
    def __init__(self):
        """Initialize VPN service with Marzban client for V2Ray/Trojan"""
        # Marzban client for V2Ray/Trojan
        self.marzban = MarzbanClient()

    def connect(self, user_id):
        """Initiate VPN connection for user (V2Ray subscription)"""
        try:
            # Check if user exists
            user = User.get_by_id(user_id)
            if not user:
                return {
                    'status': 'error',
                    'message': f'User {user_id} not found'
                }

            # Check if user's subscription is active
            if not user.is_subscription_active():
                return {
                    'status': 'error',
                    'message': f'Subscription is not active. Please renew your subscription.'
                }

            # Get Marzban subscription
            result = self.get_marzban_subscription(user_id)
            
            if result.get('status') == 'success':
                return {
                    'status': 'success',
                    'message': f'VPN connection initiated for user {user_id}',
                    'user_id': user_id,
                    'connection_details': result
                }
            else:
                return result
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error connecting VPN for user {user_id}: {str(e)}'
            }

    def disconnect(self, user_id):
        """Disconnect VPN connection for user"""
        try:
            return {
                'status': 'success',
                'message': f'VPN connection terminated for user {user_id}',
                'user_id': user_id
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error disconnecting VPN for user {user_id}: {str(e)}'
            }

    def get_connection_status(self, user_id):
        """Get current VPN connection status for user"""
        try:
            user = User.get_by_id(user_id)
            if not user:
                return {
                    'user_id': user_id,
                    'connected': False,
                    'error': 'User not found'
                }

            return {
                'user_id': user_id,
                'connected': user.is_active,
                'connection_time': None,
                'data_transferred': 0
            }
        except Exception as e:
            return {
                'user_id': user_id,
                'connected': False,
                'error': str(e)
            }

    # =========================================================
    # Marzban (V2Ray/Trojan/Reality) методы
    # =========================================================

    def _enable_marzban_inbounds(self):
        """Автоматическое включение VLESS Reality и Trojan TLS через БД"""
        try:
            import subprocess

            # Запускаем скрипт включения inbound
            result = subprocess.run(
                ['python3', '/app/enable_marzban_inbounds.py'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info("✅ Marzban inbounds check completed")
                if result.stdout:
                    logger.info(result.stdout.strip())
            else:
                logger.warning(f"Inbound check failed: {result.stderr}")

        except Exception as e:
            logger.error(f"Error enabling Marzban inbounds: {e}")

    def create_marzban_user(self, user_id: int, tariff: str = "standard"):
        """Создание пользователя в Marzban (V2Ray/Trojan) - БЕСПЛАТНО И БЕСКОНЕЧНО"""
        try:
            from datetime import datetime, timedelta
            from database.models.user_model import User as UserModel

            # Check if user exists in PostgreSQL
            user = UserModel.query.filter_by(id=user_id).first()
            if not user:
                logger.info(f"User {user_id} not found in DB, creating...")
                # Создаём пользователя в БД если нет
                user_data = {
                    'id': user_id,
                    'username': f'user_{user_id}'
                }
                from models.user import User
                user = User.create(user_data)

            # 🔴 ПРОВЕРКА: Активна ли подписка
            if not user.subscription_end_date or user.subscription_end_date < datetime.utcnow():
                logger.warning(f"User {user_id} has no active subscription")
                return {
                    "status": "error",
                    "message": "Подписка не активна. Пожалуйста, оплатите тариф.",
                    "code": "no_subscription"
                }

            # Все ключи бесплатные и бессрочные
            # Тарифы (все с большим сроком - 10 лет = 3650 дней)
            tariffs = {
                "start": {"limit": 10 * 1024**3, "days": 3650},      # 10 GB, 10 лет
                "standard": {"limit": 50 * 1024**3, "days": 3650},   # 50 GB, 10 лет
                "premium": {"limit": 100 * 1024**3, "days": 3650},   # 100 GB, 10 лет
            }

            tariff_data = tariffs.get(tariff, tariffs["standard"])
            username = f"user_{user_id}"

            # Вычисляем expire дату (10 лет от сейчас) используя UTC
            expire_date = datetime.utcnow() + timedelta(days=3650)
            expire_timestamp = int(expire_date.timestamp())

            logger.info(f"Expire date: {expire_date}, timestamp: {expire_timestamp}")

            # Включаем inbound автоматически перед созданием пользователя
            self._enable_marzban_inbounds()

            # 🔴 Добавляем inbounds для пользователя
            inbounds = {
                "vless": ["VLESS Reality"],
                "trojan": ["Trojan TLS"]
            }

            # Проверка, существует ли уже пользователь
            existing_user = self.marzban.get_user(username)
            if existing_user.get("status") == "success":
                # Пользователь уже существует, получаем данные
                user_data = existing_user.get("data", {})
                expire_timestamp = user_data.get("expire")
                subscription_url = self.marzban.get_subscription_url(username)

                if subscription_url:
                    # 🆕 СИНХРОНИЗАЦИЯ С POSTGRESQL для существующего пользователя
                    from database.db_config import db
                    from database.models.user_model import User as UserModel
                    from datetime import datetime

                    user = UserModel.query.filter_by(id=user_id).first()
                    if user and expire_timestamp and expire_timestamp > 0:
                        user.subscription_end_date = datetime.fromtimestamp(expire_timestamp)
                        db.session.commit()
                        logger.info(f"✅ Синхронизировано subscription_end_date для existing user_{user_id}: {user.subscription_end_date}")

                    return {
                        "status": "success",
                        "protocol": "v2ray",
                        "subscription_url": subscription_url,
                        "username": username,
                        "message": "Existing user, retrieved subscription",
                        "expire_timestamp": expire_timestamp
                    }
                else:
                    # Пользователь есть, но ссылки нет - продлеваем на 10 лет
                    result = self.marzban.extend_user(username, 3650)
                    subscription_url = self.marzban.get_subscription_url(username)

                    # 🆕 СИНХРОНИЗАЦИЯ С POSTGRESQL после продления
                    from database.db_config import db
                    from database.models.user_model import User as UserModel
                    from datetime import datetime

                    user = UserModel.query.filter_by(id=user_id).first()
                    if user:
                        new_expire = int(datetime.utcnow().timestamp()) + (3650 * 86400)
                        user.subscription_end_date = datetime.fromtimestamp(new_expire)
                        db.session.commit()
                        logger.info(f"✅ Синхронизировано subscription_end_date для extended user_{user_id}: {user.subscription_end_date}")

                    return {
                        "status": "success",
                        "protocol": "v2ray",
                        "subscription_url": subscription_url,
                        "username": username,
                        "message": "Extended existing user"
                    }

            # Создание пользователя (бесплатно и на 10 лет)
            result = self.marzban.create_user_with_expire(
                username=username,
                data_limit=tariff_data["limit"],
                expire_timestamp=expire_timestamp,
                protocols={"vless": {}, "trojan": {}}
            )

            if result.get("status") == "success":
                # 🔴 Добавляем inbounds после создания
                self.marzban.modify_user(username, inbounds=inbounds)
                
                subscription_url = self.marzban.get_subscription_url(username)

                # 🆕 СИНХРОНИЗАЦИЯ С POSTGRESQL
                from database.db_config import db
                from database.models.user_model import User as UserModel
                from datetime import datetime

                user = UserModel.query.filter_by(id=user_id).first()
                if user:
                    user.subscription_end_date = datetime.fromtimestamp(expire_timestamp)
                    db.session.commit()
                    logger.info(f"✅ Синхронизировано subscription_end_date для user_{user_id}: {user.subscription_end_date}")

                return {
                    "status": "success",
                    "protocol": "v2ray",
                    "subscription_url": subscription_url,
                    "username": username,
                    "data_limit": tariff_data["limit"],
                    "expire_timestamp": expire_timestamp
                }
            else:
                return result

        except Exception as e:
            logger.error(f"Error creating Marzban user: {e}")
            return {"status": "error", "message": str(e)}

    def get_marzban_subscription(self, user_id: int):
        """Получение подписки пользователя из Marzban"""
        try:
            username = f"user_{user_id}"
            subscription_url = self.marzban.get_subscription_url(username)

            if subscription_url:
                return {
                    "status": "success",
                    "subscription_url": subscription_url,
                    "username": username
                }
            else:
                return {"status": "error", "message": "Subscription not found"}
        except Exception as e:
            logger.error(f"Error getting Marzban subscription: {e}")
            return {"status": "error", "message": str(e)}

    def remove_marzban_user(self, user_id: int):
        """Удаление пользователя из Marzban"""
        try:
            username = f"user_{user_id}"
            result = self.marzban.remove_user(username)
            return result
        except Exception as e:
            logger.error(f"Error removing Marzban user: {e}")
            return {"status": "error", "message": str(e)}

    def extend_marzban_user(self, user_id: int, days: int = 30):
        """Продление подписки пользователя в Marzban"""
        try:
            username = f"user_{user_id}"
            result = self.marzban.modify_user(username, expire_days=days)
            return result
        except Exception as e:
            logger.error(f"Error extending Marzban user: {e}")
            return {"status": "error", "message": str(e)}

    def create_marzban_user_with_payload(self, user_id: int, payload: dict):
        """
        Создание пользователя в Marzban с готовым payload
        """
        try:
            username = payload.get('username', f'user_{user_id}')
            
            # Проверяем существует ли уже пользователь
            existing = self.marzban.get_user(username)
            if existing.get('status') == 'success':
                logger.info(f"User {username} already exists, updating...")
                result = self.marzban.modify_user(
                    username,
                    data_limit=payload.get('data_limit'),
                    expire_days=int((payload.get('expire', 0) - int(datetime.utcnow().timestamp())) / 86400),
                    inbounds=payload.get('inbounds')
                )
                return result
            
            # Создаём нового пользователя с inbounds из payload
            result = self.marzban.create_user(
                username=username,
                data_limit=payload.get('data_limit', 10 * 1024**3),
                expire_days=int((payload.get('expire', 0) - int(datetime.utcnow().timestamp())) / 86400),
                inbounds=payload.get('inbounds')  # Передаём inbounds напрямую!
            )
            
            return result
        except Exception as e:
            logger.error(f"Error creating Marzban user with payload: {e}")
            return {"status": "error", "message": str(e)}
