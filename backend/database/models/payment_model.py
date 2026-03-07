"""Payment model for PostgreSQL database"""

from database.db_config import db
from datetime import datetime


class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.String(100), primary_key=True, unique=True, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='RUB')
    description = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    paid = db.Column(db.Boolean, default=False)
    yookassa_payment_id = db.Column(db.String(100), nullable=True)
    yookassa_status = db.Column(db.String(50), nullable=True)
    confirmation_url = db.Column(db.Text, nullable=True)
    test = db.Column(db.Boolean, default=False)
    stars_amount = db.Column(db.Integer, default=0)

    __table_args__ = (
        db.Index('idx_payments_user_id', 'user_id'),
        db.Index('idx_payments_status', 'status'),
        db.Index('idx_payments_yookassa_id', 'yookassa_payment_id'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'amount': float(self.amount),
            'currency': self.currency,
            'description': self.description,
            'user_id': self.user_id,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'paid': self.paid,
            'yookassa_payment_id': self.yookassa_payment_id,
            'yookassa_status': self.yookassa_status,
            'confirmation_url': self.confirmation_url,
            'test': self.test,
            'stars_amount': self.stars_amount
        }

    def update_status(self, new_status):
        self.status = new_status
        self.updated_at = datetime.utcnow()
        if new_status == 'succeeded':
            self.paid = True

    def set_yookassa_data(self, payment_id, status, confirmation_url=None):
        self.yookassa_payment_id = payment_id
        self.yookassa_status = status
        self.confirmation_url = confirmation_url
        self.updated_at = datetime.utcnow()

    @classmethod
    def get_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id=user_id).all()

    @classmethod
    def get_pending_payments(cls):
        return cls.query.filter_by(status='pending').all()

    @classmethod
    def get_successful_payments(cls, user_id=None, limit=10):
        query = cls.query.filter_by(paid=True)
        if user_id:
            query = query.filter_by(user_id=user_id)
        return query.order_by(cls.created_at.desc()).limit(limit).all()
