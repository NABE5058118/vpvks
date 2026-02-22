"""
VPN Service
Handles VPN connection logic with WireGuard and Marzban (V2Ray/Trojan/Reality)
"""

import subprocess
import os
import uuid
from datetime import datetime
import sys
import logging

# Add the parent directory to the path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.user import User
from models.vpn_config import VPNConfig
from database.db_config import db
from database.models.vpn_config_model import VPNConfig as VPNConfigModel
from services.marzban_client import MarzbanClient

logger = logging.getLogger(__name__)

class VPNService:
    def __init__(self):
        """Initialize VPN service with WireGuard and Marzban configuration"""
        # Directory to store WireGuard configurations
        self.config_dir = os.getenv('WG_CONFIG_DIR', './wg_configs')
        os.makedirs(self.config_dir, exist_ok=True)

        # VPN server details for WireGuard
        self.server_ip = os.getenv('WG_SERVER_IP', '10.0.0.1')
        self.server_port = int(os.getenv('WG_PORT', '51820'))
        self.dns_server = os.getenv('WG_DNS', '8.8.8.8')
        self.server_public_key = os.getenv('WG_SERVER_PUBLIC_KEY', '')
        
        # Marzban client for V2Ray/Trojan
        self.marzban = MarzbanClient()

    def connect(self, user_id):
        """Initiate VPN connection for user"""
        try:
            # Check if user has active subscription
            from models.user import User
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

            # Get or create user configuration
            user_config = self._get_or_create_user_config(user_id)

            if not user_config:
                return {
                    'status': 'error',
                    'message': f'Failed to create VPN configuration for user {user_id}'
                }

            # Record the connection in the VPN config
            vpn_config = VPNConfig.get_by_user_id(user_id)
            if vpn_config:
                vpn_config.record_connection()

            # In a real implementation, we would activate the connection
            # For now, we'll simulate the connection
            return {
                'status': 'success',
                'message': f'VPN connection initiated for user {user_id}',
                'user_id': user_id,
                'connection_details': user_config
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error connecting VPN for user {user_id}: {str(e)}'
            }

    def disconnect(self, user_id):
        """Disconnect VPN connection for user"""
        try:
            # In a real implementation, we would deactivate the connection
            # For now, we'll simulate the disconnection
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
            # Check if user has active connection
            # This is a simplified version - in reality, we'd check WireGuard status
            user = User.get_by_id(user_id)
            if not user:
                return {
                    'user_id': user_id,
                    'connected': False,
                    'error': 'User not found'
                }
                
            return {
                'user_id': user_id,
                'connected': user.is_active,  # Simplified check
                'connection_time': None,
                'data_transferred': 0
            }
        except Exception as e:
            return {
                'user_id': user_id,
                'connected': False,
                'error': str(e)
            }

    def _get_or_create_user_config(self, user_id):
        """Generate or retrieve WireGuard configuration for user"""
        try:
            # Check if config already exists in database
            vpn_config = VPNConfig.get_by_user_id(user_id)

            if vpn_config:
                # Config already exists, return it
                return vpn_config.to_dict()
            else:
                # Generate new keys
                print(f"[DEBUG] Generating keys for user {user_id}")
                client_private_key = self._generate_wireguard_key(is_private=True)
                print(f"[DEBUG] Private key generated: {client_private_key[:10]}...")
                
                client_public_key = self._generate_client_public_key(client_private_key)
                print(f"[DEBUG] Public key generated: {client_public_key[:10]}...")

                # Create VPN configuration object
                config_data = {
                    'user_id': user_id,
                    'private_key': client_private_key,
                    'public_key': client_public_key,
                    'server_ip': self.server_ip,
                    'server_port': self.server_port,
                    'dns_server': self.dns_server
                }

                # Create in database
                print(f"[DEBUG] Creating VPN config in database...")
                vpn_config_model = VPNConfigModel.create(config_data)
                print(f"[DEBUG] VPN config created: {vpn_config_model.id}")

                # Also save the config file for WireGuard
                config_path = os.path.join(self.config_dir, f'user_{user_id}.conf')
                print(f"[DEBUG] Config dir: {self.config_dir}")
                print(f"[DEBUG] Config path: {config_path}")
                
                # Ensure directory exists
                os.makedirs(self.config_dir, exist_ok=True)
                
                config_content = self._create_wireguard_config(
                    client_private_key,
                    client_public_key,
                    self.server_public_key
                )

                # Save configuration to file
                with open(config_path, 'w') as f:
                    f.write(config_content)
                print(f"[DEBUG] Config file saved: {config_path}")

                # Update config file path in database
                vpn_config_model.config_file_path = config_path
                db.session.commit()
                print(f"[DEBUG] Database committed")

                # Return the config data with file path
                result = vpn_config_model.to_dict()
                result['config_file'] = config_path
                return result
        except Exception as e:
            print(f"[ERROR] Error generating user config: {str(e)}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return None

    def _generate_wireguard_key(self, is_private=True, input_key=None):
        """Generate WireGuard key (private or public)"""
        try:
            if is_private:
                # Generate private key
                result = subprocess.run(['wg', 'genkey'], capture_output=True, text=True, check=True)
                return result.stdout.strip()
            else:
                # Generate public key from private key
                if input_key:
                    result = subprocess.run(['echo', input_key], stdout=subprocess.PIPE)
                    result = subprocess.run(['wg', 'pubkey'], stdin=result.stdout, capture_output=True, text=True, check=True)
                    return result.stdout.strip()
                else:
                    # Generate random public key (for demo purposes)
                    return f"demo_public_key_{uuid.uuid4().hex[:16]}"
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback for systems without wg command
            if is_private:
                return f"demo_private_key_{uuid.uuid4().hex}"
            else:
                return f"demo_public_key_{uuid.uuid4().hex[:16]}"

    def _extract_key_from_config(self, config_content, key_type):
        """Extract a specific key from WireGuard config"""
        for line in config_content.split('\n'):
            if line.startswith(key_type + ' = '):
                return line.split(' = ')[1]
        return None

    def _generate_client_public_key(self, private_key):
        """Generate client public key from private key"""
        try:
            # Write private key to process stdin properly
            process = subprocess.Popen(['wg', 'pubkey'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(input=private_key)
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, 'wg pubkey', stderr)
            return stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback for systems without wg command
            return f"demo_public_key_{uuid.uuid4().hex[:16]}"

    def _create_wireguard_config(self, client_private_key, client_public_key, server_public_key):
        """Create WireGuard configuration file content"""
        # Generate unique IP for client based on public key hash
        client_ip_suffix = abs(hash(client_public_key)) % 250 + 2
        client_ip = f"10.10.0.{client_ip_suffix}/32"

        return f"""[Interface]
PrivateKey = {client_private_key}
Address = {client_ip}
DNS = {self.dns_server}

[Peer]
PublicKey = {server_public_key}
Endpoint = {self.server_ip}:{self.server_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

    # =========================================================
    # Marzban (V2Ray/Trojan/Reality) методы
    # =========================================================
    
    def create_marzban_user(self, user_id: int, tariff: str = "standard"):
        """Создание пользователя в Marzban (V2Ray/Trojan)"""
        try:
            # Тарифы
            tariffs = {
                "start": {"limit": 10 * 1024**3, "days": 30},      # 10 GB
                "standard": {"limit": 50 * 1024**3, "days": 30},   # 50 GB
                "premium": {"limit": 100 * 1024**3, "days": 30},   # 100 GB
            }
            
            tariff_data = tariffs.get(tariff, tariffs["standard"])
            username = f"user_{user_id}"
            
            # Проверка, существует ли уже пользователь
            existing_user = self.marzban.get_user(username)
            if existing_user.get("status") == "success":
                # Пользователь уже существует, получаем ссылку подписки
                subscription_url = self.marzban.get_subscription_url(username)
                return {
                    "status": "success",
                    "protocol": "v2ray",
                    "subscription_url": subscription_url,
                    "username": username,
                    "message": "User already exists, retrieved existing subscription"
                }
            
            # Создание пользователя
            # В новой версии Marzban proxies передаётся как словарь
            result = self.marzban.create_user(
                username=username,
                data_limit=tariff_data["limit"],
                expire_days=tariff_data["days"],
                protocols={"vless": {}, "trojan": {}}
            )
            
            if result.get("status") == "success":
                # Получение ссылки подписки
                subscription_url = self.marzban.get_subscription_url(username)
                
                return {
                    "status": "success",
                    "protocol": "v2ray",
                    "subscription_url": subscription_url,
                    "username": username,
                    "data_limit": tariff_data["limit"],
                    "expire_days": tariff_data["days"]
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