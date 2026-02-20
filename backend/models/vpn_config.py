"""
VPN Configuration Model
Represents VPN configuration for a user
"""

import uuid
from datetime import datetime
from database.models.vpn_config_model import VPNConfig as VPNConfigModel
from database.db_config import db


class VPNConfig:
    @staticmethod
    def get_by_id(config_id):
        """Get VPN config by ID from database"""
        return VPNConfigModel.get_by_id(config_id)

    @staticmethod
    def get_by_user_id(user_id):
        """Get VPN config by user ID from database"""
        return VPNConfigModel.get_by_user_id(user_id)

    @staticmethod
    def create(data):
        """Create a new VPN configuration in database"""
        return VPNConfigModel.create(data)

    @staticmethod
    def get_all_configs():
        """Get all VPN configurations from database"""
        return VPNConfigModel.get_all_configs()