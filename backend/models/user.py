"""
Updated User model that uses PostgreSQL database
"""

from database.models.user_model import User as UserModel
from database.db_config import db
from datetime import datetime, timedelta
import uuid


class User:
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID from database"""
        return UserModel.query.filter_by(id=user_id).first()

    @staticmethod
    def create(data):
        """Create a new user in database"""
        user_id = data.get('id')
        if not user_id:
            raise ValueError("User ID is required")

        # Check if user already exists
        existing_user = UserModel.query.filter_by(id=user_id).first()
        if existing_user:
            return existing_user

        # Create new user
        user = UserModel(
            id=user_id,
            username=data.get('username'),
            email=data.get('email'),
            subscription_end_date=data.get('subscription_end_date'),
            last_charge_date=data.get('last_charge_date')
        )

        db.session.add(user)
        db.session.commit()

        return user

    @staticmethod
    def get_all_users():
        """Get all users from database"""
        return UserModel.query.all()

    @staticmethod
    def create_trial_user(user_data):
        """Create a user with a trial period"""
        # Add 7 days to current date for trial
        user_data['subscription_end_date'] = datetime.utcnow() + timedelta(days=7)
        user_data['trial_used'] = True

        return User.create(user_data)

    @staticmethod
    def get_balance(user_id):
        """Get user balance by ID"""
        user = User.get_by_id(user_id)
        if user:
            return user.balance
        return 0

    @staticmethod
    def update_balance(user_id, new_balance):
        """Update user balance"""
        user = User.get_by_id(user_id)
        if user:
            user.balance = new_balance
            db.session.commit()
            return user.balance
        return None

