"""
Updated Payment model that uses PostgreSQL database
"""

from database.models.payment_model import Payment as PaymentModel
from database.db_config import db
from datetime import datetime
from models.user import User
import uuid


class Payment:
    @staticmethod
    def get_by_id(payment_id):
        """Get payment by ID from database"""
        return PaymentModel.query.filter_by(id=payment_id).first()

    @staticmethod
    def create(data):
        """Create a new payment in database"""
        payment_id = data.get('id')
        if not payment_id:
            payment_id = str(uuid.uuid4())

        # Verify user exists
        user = User.get_by_id(data.get('user_id'))
        if not user:
            raise ValueError(f"User with ID {data.get('user_id')} does not exist")

        # Create new payment
        payment = PaymentModel(
            id=payment_id,
            amount=data.get('amount'),
            currency=data.get('currency', 'RUB'),
            description=data.get('description'),
            user_id=data.get('user_id'),
            status=data.get('status', 'pending'),
            stars_amount=data.get('stars_amount', 0)  # Add stars amount if provided
        )

        db.session.add(payment)
        db.session.commit()

        return payment

    @staticmethod
    def get_payments_by_user(user_id):
        """Get all payments for a user from database"""
        return PaymentModel.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_recent_payments(limit=10):
        """Get recent payments from database"""
        return PaymentModel.query.order_by(PaymentModel.created_at.desc()).limit(limit).all()