"""Payment model wrapper"""

from database.models.payment_model import Payment as PaymentModel
from database.db_config import db
from datetime import datetime
from models.user import User
import uuid


class Payment:
    @staticmethod
    def get_by_id(payment_id):
        return PaymentModel.query.filter_by(id=payment_id).first()

    @staticmethod
    def create(data):
        payment_id = data.get('id')
        if not payment_id:
            payment_id = str(uuid.uuid4())

        user = User.get_by_id(data.get('user_id'))
        if not user:
            raise ValueError(f"User with ID {data.get('user_id')} does not exist")

        payment = PaymentModel(
            id=payment_id,
            amount=data.get('amount'),
            currency=data.get('currency', 'RUB'),
            description=data.get('description'),
            user_id=data.get('user_id'),
            status=data.get('status', 'pending'),
            stars_amount=data.get('stars_amount', 0)
        )

        yookassa_payment_id = data.get('yookassa_payment_id')
        yookassa_status = data.get('yookassa_status')
        confirmation_url = data.get('confirmation_url')

        if yookassa_payment_id:
            payment.set_yookassa_data(yookassa_payment_id, yookassa_status or 'pending', confirmation_url)

        db.session.add(payment)
        db.session.commit()
        return payment

    @staticmethod
    def get_payments_by_user(user_id):
        return PaymentModel.query.filter_by(user_id=user_id).all()

    @staticmethod
    def get_recent_payments(limit=10):
        return PaymentModel.query.order_by(PaymentModel.created_at.desc()).limit(limit).all()

    @staticmethod
    def update_yookassa_data(payment_id, yookassa_payment_id, status, confirmation_url=None):
        payment = Payment.get_by_id(payment_id)
        if payment:
            payment.set_yookassa_data(yookassa_payment_id, status, confirmation_url)
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_successful_payments(user_id=None, limit=10):
        return PaymentModel.get_successful_payments(user_id, limit)

    @staticmethod
    def get_pending_payments():
        return PaymentModel.get_pending_payments()
