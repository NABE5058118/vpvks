"""User model wrapper"""

from database.models.user_model import User as UserModel
from database.models.connection_log_model import ConnectionLog
from database.db_config import db
from datetime import datetime, timedelta


class User:
    @staticmethod
    def get_by_id(user_id):
        return UserModel.query.filter_by(id=user_id).first()

    @staticmethod
    def create(data):
        user_id = data.get('id')
        if not user_id:
            raise ValueError("User ID is required")

        existing_user = UserModel.query.filter_by(id=user_id).first()
        if existing_user:
            return existing_user

        user = UserModel(
            id=user_id,
            username=data.get('username'),
            subscription_end_date=data.get('subscription_end_date'),
            last_charge_date=data.get('last_charge_date')
        )

        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def get_all_users():
        return UserModel.query.all()

    @staticmethod
    def get_active_users():
        return UserModel.query.filter_by(deleted_at=None).all()

    @staticmethod
    def get_balance(user_id):
        user = User.get_by_id(user_id)
        return user.balance if user else 0

    @staticmethod
    def update_balance(user_id, new_balance):
        user = User.get_by_id(user_id)
        if user:
            user.balance = new_balance
            db.session.commit()
            return user.balance
        return None

    @staticmethod
    def soft_delete(user_id):
        user = User.get_by_id(user_id)
        if user:
            user.soft_delete()
            db.session.commit()
            return True
        return False

    @staticmethod
    def restore(user_id):
        user = User.get_by_id(user_id)
        if user:
            user.restore()
            db.session.commit()
            return True
        return False

    @staticmethod
    def add_connection_log(user_id, connected=True, ip_address=None, user_agent=None):
        return ConnectionLog.add_log(user_id, connected, ip_address, user_agent)

    @staticmethod
    def get_connection_logs(user_id, limit=50):
        return ConnectionLog.get_by_user_id(user_id, limit)
