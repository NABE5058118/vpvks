"""VPN Service - Marzban (V2Ray/Trojan/Reality)"""

import os
from datetime import datetime, timedelta
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User
from services.marzban_client import MarzbanClient

logger = logging.getLogger(__name__)


class VPNService:
    def __init__(self):
        self.marzban = MarzbanClient()

    def connect(self, user_id):
        try:
            user = User.get_by_id(user_id)
            if not user:
                return {
                    'status': 'error',
                    'message': f'User {user_id} not found'
                }

            if not user.is_subscription_active():
                return {
                    'status': 'error',
                    'message': 'Subscription is not active. Please renew your subscription.'
                }

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
                'connected': user.is_subscription_active(),
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

            # Получаем лимит трафика из БД пользователя
            username = f"user_{user_id}"
            
            # Проверяем существующего пользователя в БД
            from database.db_config import db
            from database.models.user_model import User as UserModel
            
            db_user = UserModel.query.filter_by(id=user_id).first()
            data_limit_bytes = 0  # 0 = безлимитный трафик
            
            if db_user and db_user.data_limit_gb and db_user.data_limit_gb > 0:
                data_limit_bytes = int(db_user.data_limit_gb * 1024**3)
                logger.info(f"Using data limit from DB: {db_user.data_limit_gb}GB")
            else:
                # Безлимитный трафик по умолчанию
                data_limit_bytes = 0
                logger.info(f"Using unlimited traffic (data_limit = 0)")

            logger.info(f"Data limit for user {user_id}: {'Безлимитный' if data_limit_bytes == 0 else f'{data_limit_bytes} bytes'}")

            # Включаем inbound автоматически перед созданием пользователя
            self._enable_marzban_inbounds()

            # 🔴 Добавляем inbounds для пользователя
            inbounds = {
                "vless": ["VLESS Reality"],
                "trojan": ["Trojan TLS"],
                "hysteria2": ["Hysteria 2"]
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
                    # Пользователь есть, но ссылки нет - продлеваем
                    result = self.marzban.extend_user(username, 3650)
                    subscription_url = self.marzban.get_subscription_url(username)

                    # 🆕 СИНХРОНИЗАЦИЯ С POSTGRESQL после продления
                    from database.db_config import db
                    from database.models.user_model import User as UserModel

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

            # Вычисляем expire timestamp из БД
            from database.db_config import db
            from database.models.user_model import User as UserModel
            
            db_user = UserModel.query.filter_by(id=user_id).first()
            if db_user and db_user.subscription_end_date:
                expire_timestamp = int(db_user.subscription_end_date.timestamp())
            else:
                # Default: 1 год от сейчас
                import time
                expire_timestamp = int(time.time()) + (365 * 86400)

            logger.info(f"Expire timestamp: {expire_timestamp}")

            # Конвертируем timestamp в дни
            import time
            expire_days = max(1, (expire_timestamp - int(time.time())) // 86400)
            logger.info(f"Expire days: {expire_days}")

            # Создание пользователя с лимитом трафика
            result = self.marzban.create_user(
                username=username,
                data_limit=data_limit_bytes,
                expire_days=expire_days,
                protocols={"vless": {}, "trojan": {}},
                inbounds=inbounds
            )

            if result.get("status") == "success":
                subscription_url = self.marzban.get_subscription_url(username)

                # 🆕 СИНХРОНИЗАЦИЯ С POSTGRESQL
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
                    "data_limit": data_limit_bytes,
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
                
                # 🔴 ИСПРАВЛЕНИЕ: передаём expire как timestamp, а не expire_days
                # Marzban API принимает expire как Unix timestamp
                modify_data = {}
                
                if payload.get('data_limit') is not None:
                    modify_data['data_limit'] = payload.get('data_limit')
                    logger.info(f"Setting data_limit: {payload.get('data_limit')}")
                
                if payload.get('expire') and payload.get('expire') > 0:
                    # Передаем expire как timestamp (Marzban API)
                    modify_data['expire'] = payload.get('expire')
                    logger.info(f"Setting expire timestamp: {payload.get('expire')}")
                
                if payload.get('inbounds'):
                    modify_data['inbounds'] = payload.get('inbounds')
                    logger.info(f"Setting inbounds: {payload.get('inbounds')}")
                
                if payload.get('proxies'):
                    modify_data['proxies'] = payload.get('proxies')
                    logger.info(f"Setting proxies: {payload.get('proxies')}")
                
                result = self.marzban.modify_user(username, modify_data)
                logger.info(f"Marzban modify_user result: {result}")
                return result

            # Создаём нового пользователя с inbounds из payload
            create_payload = {
                "username": username,
                "data_limit": payload.get('data_limit', 10 * 1024**3),
            }
            
            if payload.get('expire'):
                create_payload['expire'] = payload.get('expire')
            
            if payload.get('inbounds'):
                create_payload['inbounds'] = payload.get('inbounds')
            
            if payload.get('proxies'):
                create_payload['proxies'] = payload.get('proxies')
            
            result = self.marzban.create_user(
                username=username,
                data_limit=create_payload.get('data_limit', 10 * 1024**3),
                expire_days=0,  # Не используем expire_days, передаём expire напрямую
                inbounds=create_payload.get('inbounds')
            )
            
            # Если create_user не поддержит expire, нужно использовать modify_user
            if result.get('status') == 'success' and payload.get('expire'):
                # Дополнительно обновляем expire через modify_user
                modify_result = self.marzban.modify_user(username, {'expire': payload.get('expire')})
                logger.info(f"Marzban modify_user after create: {modify_result}")

            return result
        except Exception as e:
            logger.error(f"Error creating Marzban user with payload: {e}")
            return {"status": "error", "message": str(e)}
